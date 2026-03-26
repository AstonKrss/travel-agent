from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM Configuration
    llm_provider: str = Field(
        "openai",
        description="LLM provider: openai, volcano (Volcano Engine/Qwen), etc.",
    )
    llm_temperature: float = Field(0.7, description="LLM temperature")

    # OpenAI
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_base_url: str = Field(
        "https://api.openai.com/v1", description="OpenAI API base URL"
    )
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model name")

    # Volcano Engine (ByteDance) - Doubao / Qwen
    volcano_api_key: Optional[str] = Field(None, description="Volcano Engine API key")
    volcano_base_url: str = Field(
        "https://ark.cn-beijing.volces.com/api/v3",
        description="Volcano Engine base URL",
    )
    volcano_model: str = Field(
        "qwen3-72b-instruct",
        description="Volcano Engine model ID (e.g. qwen3-72b-instruct, doubao-4)",
    )

    # ASR Speech Recognition Configuration (optional)
    # Alibaba Cloud Dashscope (also supports Qwen ASR)
    dashscope_api_key: Optional[str] = Field(
        None, description="Alibaba Cloud Dashscope API key for ASR"
    )
    # iFlytek
    iflytek_appid: Optional[str] = Field(None, description="iFlytek App ID for ASR")
    iflytek_api_key: Optional[str] = Field(None, description="iFlytek API key")
    iflytek_api_secret: Optional[str] = Field(None, description="iFlytek API secret")

    # TMC (Travel Management Company) API Configuration
    tmc_api_base_url: Optional[str] = Field(None, description="TMC API base URL")
    tmc_api_key: Optional[str] = Field(
        None, description="TMC API key for authentication"
    )
    tmc_company_account_id: Optional[str] = Field(
        None, description="Company account ID for corporate payment"
    )

    # OA/Finance System API Configuration
    oa_api_base_url: Optional[str] = Field(None, description="OA system API base URL")
    oa_api_key: Optional[str] = Field(None, description="OA API key")

    # CORS Configuration
    allowed_origin: str = Field("*", description="Allowed CORS origin")

    # Server Configuration
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")

    # Use mock implementations when API keys are not provided
    use_mock: bool = Field(
        True, description="Use mock implementations when API keys not configured"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
