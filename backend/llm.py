from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from .config import settings


def get_llm(timeout: int = 30) -> BaseChatModel:
    """Factory method to get LLM based on configuration."""
    if settings.llm_provider == "volcano":
        return ChatOpenAI(
            api_key=SecretStr(settings.volcano_api_key or ""),
            base_url=settings.volcano_base_url,
            model=settings.volcano_model or "ep-m-20260326112043-hrs4j",
            temperature=settings.llm_temperature,
            timeout=timeout,
            max_retries=2,
        )
    elif settings.llm_provider == "openai":
        return ChatOpenAI(
            api_key=SecretStr(settings.openai_api_key or ""),
            base_url=settings.openai_base_url,
            model=settings.openai_model or "gpt-4o-mini",
            temperature=settings.llm_temperature,
            timeout=timeout,
            max_retries=2,
        )
    else:
        raise ValueError(
            f"LLM provider {settings.llm_provider} not configured properly."
        )
