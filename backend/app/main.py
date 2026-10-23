"""FastAPI application para el asistente de Tania"""

import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.chat import ChatRequest, ChatResponse, ChatMessage
from app.services.openrouter import openrouter
from app.services.response_guard import (
    CLEANUP_INSTRUCTION,
    SAFE_FALLBACK_TEXT,
    has_reasoning_leak,
    sanitize_assistant_text,
)
from app.prompts.tania import TANIA_SYSTEM_PROMPT

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tania Portfolio API",
    description="Asistente conversacional del portafolio de Tania Peláez Valverde",
    version="1.0.0",
)

# CORS
allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "tania-portfolio-api",
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest):
    """
    Endpoint de chat.

    Recibe un historial de mensajes y devuelve una respuesta del asistente.
    """
    try:
        # Validar request
        request.validate_messages()

        # Llamar a OpenRouter con fallback
        response_text = await openrouter.chat(
            system_prompt=TANIA_SYSTEM_PROMPT,
            messages=request.messages,
        )

        # Si el modelo filtró razonamiento, un único reintento de limpieza
        if has_reasoning_leak(response_text):
            logger.warning("Reasoning leak detected; requesting one cleanup retry")
            response_text = await openrouter.chat(
                system_prompt=f"{TANIA_SYSTEM_PROMPT}\n\n{CLEANUP_INSTRUCTION}",
                messages=request.messages,
            )

            if has_reasoning_leak(response_text):
                logger.error("Cleanup retry still leaked reasoning; using safe fallback")
                response_text = SAFE_FALLBACK_TEXT

        return ChatResponse(content=sanitize_assistant_text(response_text))

    except TimeoutError:
        logger.warning("Chat request timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="El servidor tardó demasiado. Por favor, intenta de nuevo.",
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except ConnectionError as e:
        logger.error(f"OpenRouter connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo procesar tu solicitud. Intenta más tarde.",
        )

    except Exception as e:
        logger.error(f"Unexpected error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
