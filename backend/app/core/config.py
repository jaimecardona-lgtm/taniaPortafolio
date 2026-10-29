import os

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Vacío = se resuelve en model_post_init (RENDER_EXTERNAL_URL o localhost)
    openrouter_site_url: str = ""
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

    # CORS (en producción el frontend es same-origin; esto solo afecta desarrollo separado)
    allowed_origins: str = "http://localhost:5173,http://localhost:10000"

    def model_post_init(self, __context) -> None:
        # Referer de OpenRouter: OPENROUTER_SITE_URL > URL pública de Render > local
        if not self.openrouter_site_url:
            self.openrouter_site_url = os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:10000"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
