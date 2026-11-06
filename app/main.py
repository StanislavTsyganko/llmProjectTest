import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .llm import generate_card
from .schemas import CardOut, ProductIn

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="AI Card Draft Service")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


REQUIRED_FIELDS = ["name", "manufacturer"]


def collect_specs_block(specs: dict) -> list[dict[str, str]]:
    if not specs:
        return [{"name": "характеристики", "value": "данных нет"}]
    return [{"name": str(k), "value": str(v) if v not in (None, "") else "данных нет"}
            for k, v in specs.items()]


def build_markdown(data: dict) -> str:
    """Собирает результат в готовый для копирования текст."""
    lines = []

    lines.append(f"## {data.get('seo_title', 'Заголовок отсутствует')}\n")
    lines.append(f"{data.get('seo_description', 'Описание отсутствует')}\n")

    lines.append("### Ключевые характеристики")
    for spec in data.get("specs", []):
        lines.append(f"- **{spec['name']}**: {spec['value']}")
    lines.append("")

    lines.append("### Поисковые запросы")
    for kw in data.get("keywords", []):
        lines.append(f"- {kw}")
    lines.append("")

    lines.append("### Для менеджера (коммерческий блок)")
    lines.append(f"{data.get('commercial_block', 'данных нет')}\n")

    return "\n".join(lines)


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"message": "Frontend not found. POST to /generate."})
    return FileResponse(index_file)


@app.post("/generate", response_model=CardOut)
def generate(product: ProductIn):
    payload = product.model_dump()

    missing = [f for f in REQUIRED_FIELDS if not (payload.get(f) or "").strip()]
    if missing:
        return CardOut(
            status="needs_clarification",
            missing_fields=missing,
            specs=collect_specs_block(payload.get("specs") or {}),
        )

    warnings = []
    if not payload.get("specs"):
        warnings.append("Характеристики не переданы — в блоке характеристик указано «данных нет».")
    if not payload.get("description"):
        warnings.append("Описание не передано — SEO-блок построен только по названию.")

    try:
        draft = generate_card(payload)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    specs_block = collect_specs_block(payload.get("specs") or {})

    if len(draft.seo_title) > 70:
        warnings.append(f"SEO-заголовок длиннее 70 символов ({len(draft.seo_title)}).")
    if not (800 <= len(draft.seo_description) <= 1200):
        warnings.append(f"SEO-описание вне диапазона 800–1200 символов ({len(draft.seo_description)}).")

    result_data = {
        "seo_title": draft.seo_title,
        "seo_description": draft.seo_description,
        "specs": specs_block,
        "keywords": draft.keywords,
        "commercial_block": draft.commercial_block,
    }

    return CardOut(
        status="ok",
        warnings=warnings,
        markdown=build_markdown(result_data),
        **result_data
    )
