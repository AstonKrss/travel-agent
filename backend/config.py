from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM Configuration
    llm_provider: str = Field("openai", description="LLM provider: openai, volcano")
    llm_temperature: float = Field(0.7, description="LLM temperature")

    # OpenAI
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_base_url: str = Field(
        "https://api.openai.com/v1", description="OpenAI base URL"
    )
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model")
    openai_reasoning_model: str = Field(
        "gpt-4o", description="OpenAI reasoning model for complex tasks"
    )

    # Volcano Engine
    volcano_api_key: Optional[str] = Field(None, description="Volcano API key")
    volcano_base_url: str = Field(
        "https://ark.cn-beijing.volces.com/api/v3", description="Volcano base URL"
    )
    volcano_model: str = Field("ep-m-20260326112043-hrs4j", description="Volcano model")
    volcano_reasoning_model: str = Field(
        "ep-m-20260326112043-hrs4j", description="Volcano reasoning model"
    )

    # Server
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    allowed_origin: str = Field("*", description="CORS origin")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
