"""Servicio para comunicación con OpenRouter"""

import httpx
import logging

from app.core.config import settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

# Razonamiento mínimo y excluido de la respuesta visible.
# Solo se lee message.content; el campo reasoning nunca se retorna.
REASONING_CONFIG = {"effort": "minimal", "exclude": True}

# Errores que justifican intentar el modelo fallback
RECOVERABLE_STATUSES = (429, 500, 502, 503, 504)

# Errores que no se reintentan: la solicitud en sí es inválida o no autorizada
NON_RECOVERABLE_STATUSES = (400, 401, 403)


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
        """Extrae únicamente message.content; cualquier otra cosa es recuperable"""
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
        Convierte un error HTTP en excepción.
        - 400/401/403: ValueError (no se reintenta ni se usa fallback).
        - Cualquier otro: ConnectionError, que chat() usa para activar el fallback.
        """
        status = response.status_code

        if status in NON_RECOVERABLE_STATUSES:
            logger.error(f"OpenRouter {status}: {response.text}")
            raise ValueError(f"OpenRouter error: {response.text[:200]}")

        if status in RECOVERABLE_STATUSES:
            logger.warning(f"OpenRouter {status} from {model}")
        else:
            logger.error(f"OpenRouter {status} from {model}: {response.text[:300]}")

        raise ConnectionError(f"OpenRouter error {status}")

    async def chat(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
    ) -> str:
        """
        Chat con fallback automático.
        Intenta modelo primario; si falla recuperablemente y está habilitado,
        intenta modelo fallback.
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
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                raise ConnectionError(
                    "No se pudo procesar tu solicitud. Intenta más tarde."
                )


openrouter = OpenRouterService()
