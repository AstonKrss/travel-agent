"""LLM Router - Select model based on task complexity"""

from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from backend.config import settings


def get_llm(task: str = "default", timeout: int = 30) -> Optional[BaseChatModel]:
    """Get LLM instance based on task type.

    Tasks:
    - intent: Fast classification (lower temperature)
    - reasoning: Complex reasoning (higher quality)
    - extraction: Structured data extraction
    - chat: General conversation
    - default: Default model
    """
    if settings.llm_provider == "volcano":
        return _get_volcano_llm(task, timeout)

    # Fallback to OpenAI-compatible
    return _get_openai_llm(task, timeout)


def _get_volcano_llm(task: str, timeout: int) -> Optional[BaseChatModel]:
    """Get Volcano Engine LLM."""
    if not settings.volcano_api_key:
        return None

    if task in ("intent", "extraction"):
        temp = 0.1
    elif task == "reasoning":
        temp = 0.3
    else:
        temp = settings.llm_temperature

    return ChatOpenAI(
        api_key=SecretStr(settings.volcano_api_key),
        base_url=settings.volcano_base_url,
        model=settings.volcano_model,
        temperature=temp,
        timeout=timeout,
        max_retries=2,
    )


def _get_openai_llm(task: str, timeout: int) -> Optional[BaseChatModel]:
    """Get OpenAI-compatible LLM."""
    if not settings.openai_api_key:
        return None

    if task in ("intent", "extraction"):
        model = settings.openai_model
        temp = 0.1
    elif task == "reasoning":
        model = settings.openai_reasoning_model
        temp = 0.3
    else:
        model = settings.openai_model
        temp = settings.llm_temperature

    return ChatOpenAI(
        api_key=SecretStr(settings.openai_api_key),
        base_url=settings.openai_base_url,
        model=model,
        temperature=temp,
        timeout=timeout,
        max_retries=2,
    )
