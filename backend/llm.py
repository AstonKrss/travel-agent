from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from .config import settings


def get_llm() -> BaseChatModel:
    """
    Factory method to get LLM based on configuration.
    Supports: OpenAI, Volcano Engine (ByteDance) Qwen, etc.
    """
    # Check for Volcano Engine configuration
    if settings.llm_provider == "volcano":
        # Volcano Engine uses OpenAI-compatible API
        return ChatOpenAI(
            api_key=SecretStr(settings.volcano_api_key or ""),
            base_url=settings.volcano_base_url,
            model=settings.volcano_model or "qwen3-72b-instruct",
            temperature=settings.llm_temperature,
        )
    elif settings.llm_provider == "openai":
        # Standard OpenAI
        return ChatOpenAI(
            api_key=SecretStr(settings.openai_api_key or ""),
            base_url=settings.openai_base_url,
            model=settings.openai_model or "gpt-4o-mini",
            temperature=settings.llm_temperature,
        )
    else:
        # Default to OpenAI compatible interface
        if settings.openai_api_key:
            return ChatOpenAI(
                api_key=SecretStr(settings.openai_api_key),
                base_url=settings.openai_base_url,
                model=settings.openai_model or "gpt-4o-mini",
                temperature=settings.llm_temperature,
            )
        # If no API key, our current workflow doesn't need LLM because all steps are predefined
        # The mock decision flow works without LLM
        raise ValueError(
            f"LLM provider {settings.llm_provider} not configured properly. "
            "Please check your .env file. For mock usage, keep USE_MOCK=true."
        )
