from typing import Any, Optional
from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    specs: dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class LLMCardDraft(BaseModel):
    seo_title: str
    seo_description: str
    keywords: list[str]
    commercial_block: str


class CardOut(BaseModel):
    status: str  # "ok" | "needs_clarification" | "error"
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    specs: list[dict[str, str]] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    commercial_block: Optional[str] = None

    markdown: Optional[str] = None
