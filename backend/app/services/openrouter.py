"""Servicio para comunicación con OpenRouter"""

import httpx
import logging

from app.core.config import settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

# Razonamiento desactivado y, por seguridad, excluido de la respuesta.
# Solo se lee message.content; el campo reasoning nunca se retorna.
REASONING_CONFIG = {"effort": "none", "exclude": True}

# Fallos reales del proveedor: sí justifican una request al fallback.
# 429 NO está aquí: ambos modelos gratuitos comparten la cuenta y su límite.
RECOVERABLE_STATUSES = (500, 502, 503, 504)


class RateLimitError(Exception):
    """OpenRouter devolvió 429. No se hace fallback ni reintento."""


class ProviderError(Exception):
    """Error que no debe reintentarse ni derivar a fallback (400, 401, 402, 403, etc.)."""


class OpenRouterService:
    """Cliente asíncrono para OpenRouter API"""

    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.primary_model = settings.chat_primary_llm
        self.fallback_model = settings.chat_fallback_llm
        self.use_fallback = settings.chat_use_fallback
        self.timeout = settings.chat_timeout_ms / 1000  # Convertir a segundos

    def _get_headers(self) -> dict:
        """Construye headers para OpenRouter"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.openrouter_site_url,
            "X-OpenRouter-Title": settings.openrouter_site_name,
            "Content-Type": "application/json",
        }

    async def call_model(
        self,
        model: str,
        system_prompt: str,
        messages: list[ChatMessage],
    ) -> str:
        """Llama a OpenRouter con el modelo especificado y devuelve message.content"""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *[{"role": msg.role.value, "content": msg.content} for msg in messages],
            ],
            "temperature": settings.chat_temperature,
            "top_p": settings.chat_top_p,
            "max_tokens": settings.chat_max_tokens,
            "reasoning": REASONING_CONFIG,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )

                if not response.is_success:
                    self._handle_error(response, model)

                data = response.json()
                return self._extract_content(data, model)

            except httpx.TimeoutException:
                logger.warning(f"Timeout calling {model}")
                raise TimeoutError(f"Timeout after {self.timeout}s")
            except httpx.RequestError as e:
                logger.error(f"Request error calling {model}: {e}")
                raise ConnectionError(str(e))

    def _extract_content(self, data: dict, model: str) -> str:
        """Extrae únicamente message.content; respuesta vacía se trata como fallo real"""
        choices = data.get("choices") or []
        if not choices:
            logger.error(f"No choices in OpenRouter response for {model}")
            raise ConnectionError(f"Respuesta sin choices de {model}")

        content = (choices[0].get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            logger.error(f"Empty message.content from {model}")
            raise ConnectionError(f"Respuesta vacía de {model}")

        return content

    def _handle_error(self, response: httpx.Response, model: str) -> None:
        """
        Clasifica un error HTTP:
        - 429: RateLimitError (sin fallback)
        - 500/502/503/504: ConnectionError (fallback permitido)
        - cualquier otro (400, 401, 402, 403, ...): ProviderError (sin fallback)
        """
        status = response.status_code

        if status == 429:
            logger.warning(f"OpenRouter 429 from {model}; rate limit, no fallback")
            raise RateLimitError("Límite de solicitudes de OpenRouter alcanzado")

        if status in RECOVERABLE_STATUSES:
            logger.warning(f"OpenRouter {status} from {model}")
            raise ConnectionError(f"OpenRouter error {status}")

        logger.error(f"OpenRouter {status} from {model}: {response.text[:300]}")
        raise ProviderError(f"OpenRouter error {status}")

    async def chat(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
    ) -> str:
        """
        Como máximo 2 requests por mensaje: 1 primary y, solo ante fallo real
        (timeout, conexión o 5xx), 1 fallback. 429 y errores de cliente no hacen fallback.
        """
        try:
            return await self.call_model(self.primary_model, system_prompt, messages)
        except (TimeoutError, ConnectionError) as e:
            can_fallback = (
                self.use_fallback
                and self.fallback_model
                and self.fallback_model != self.primary_model
            )
            if not can_fallback:
                raise

            logger.info(f"Primary model failed ({e}); attempting fallback: {self.fallback_model}")
            try:
                return await self.call_model(
                    self.fallback_model, system_prompt, messages
                )
            except (RateLimitError, ProviderError):
                raise
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                raise ConnectionError(
                    "No se pudo procesar tu solicitud. Intenta más tarde."
                )


openrouter = OpenRouterService()
