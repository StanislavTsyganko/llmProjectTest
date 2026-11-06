import json
import os
import time
from openai import OpenAI

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import LLMCardDraft


def generate_card(payload: dict) -> LLMCardDraft:
    if os.getenv("USE_MOCK") == "1":
        return _mock(payload)

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not set in .env")

    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=api_key,
    )
    model = os.getenv("LLM_MODEL", "llama3")

    retry_reason = ""

    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(payload, retry_reason)}
                ],
                response_format={"type": "json_object"},
                temperature=0.0, # 0.2 дает баланс: модель не фантазирует, но пишет текст развернуто.
                max_tokens=3000, # Убедитесь, что модель не обрезает ответ на полуслове (для Ollama это полезно)
            )

            content = resp.choices[0].message.content

            # Очистка от markdown-тегов
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            draft = LLMCardDraft(**data)

            desc_len = len(draft.seo_description)
            if 800 <= desc_len <= 1200:
                return draft
            elif desc_len < 800:
                retry_reason = f"Описание слишком короткое ({desc_len} символов). Напиши минимум 800 символов."
            else:
                retry_reason = f"Описание слишком длинное ({desc_len} символов). Напиши максимум 1200 символов."

            if attempt == 1:
                return draft

        except json.JSONDecodeError as e:
            if attempt == 1:
                raise RuntimeError(f"LLM вернула невалидный JSON: {e}")
            retry_reason = "Предыдущий ответ не был валидным JSON."
        except Exception as e:
            raise RuntimeError(f"Ошибка API LLM: {e}") from e

    return draft


def _mock(payload: dict) -> LLMCardDraft:
    """Заглушка на случай, если проверяющий запустит проект с USE_MOCK=1."""
    name = payload.get("name") or "товар"
    return LLMCardDraft(
        seo_title=f"{name} — купить в B2B-магазине",
        seo_description=(
            f"{name} от производителя {payload.get('manufacturer') or 'данных нет'}. "
            "Данный блок сформирован в mock-режиме для проверки работы сервиса без API-ключа. "
            * 6
        )[:1000],
        keywords=[f"купить {name}", f"{name} цена", f"{name} характеристики"],
        commercial_block=f"{name} подходит для задач промышленного контроля. Детали — данных нет.",
    )
