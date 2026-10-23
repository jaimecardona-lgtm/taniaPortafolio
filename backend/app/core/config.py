from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://taniaportafolio.onrender.com"
    openrouter_site_name: str = "Tania Peláez Valverde Portfolio"

    # Chat LLM
    chat_primary_llm: str = "nvidia/nemotron-3.5-lightning:free"
    chat_fallback_llm: str = "openrouter/free"
    chat_use_fallback: bool = True

    # Chat parameters
    chat_temperature: float = 0.2
    chat_top_p: float = 0.8
    chat_max_tokens: int = 450
    chat_timeout_ms: int = 45000

    # CORS
    allowed_origins: str = "http://localhost:5173,https://taniaportafolio.onrender.com"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
