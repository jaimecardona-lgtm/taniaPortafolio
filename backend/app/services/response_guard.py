"""Validación y limpieza de la respuesta del modelo antes de enviarla al frontend"""

import re

# Fragmentos típicos de razonamiento interno que nunca deben llegar al usuario
LEAK_PHRASES = [
    "Analyze the Request",
    "Identify Relevant Information",
    "Determine the Person's Response Style",
    "Draft the Response",
    "Refine the Response",
    "Self-Correction",
    "Chain of Thought",
]

_LEAK_PATTERN = re.compile(
    "|".join(
        [re.escape(phrase) for phrase in LEAK_PHRASES]
        + [r"\bAnalyze\b", r"\bDraft\b"]
    ),
    re.IGNORECASE,
)

# Respuesta segura si la limpieza local no deja una respuesta válida
SAFE_FALLBACK_TEXT = (
    "Claro 😊 Cuéntame un poco más sobre lo que buscas y con gusto te ayudo "
    "con mi experiencia, mis proyectos o mi contacto."
)


def has_reasoning_leak(text: str) -> bool:
    """Indica si el texto contiene marcadores de razonamiento interno"""
    return bool(_LEAK_PATTERN.search(text))


def sanitize_assistant_text(text: str) -> str:
    """
    Quita Markdown visual innecesario y deja texto plano para el chat.
    No modifica símbolos matemáticos (+, -, =, ×, ÷, ≤, %, etc.).
    """
    cleaned = text.replace("\r\n", "\n")

    # Cercas de bloque de código (```) se quitan; el contenido se conserva
    cleaned = re.sub(r"^[ \t]*```[\w-]*[ \t]*$", "", cleaned, flags=re.MULTILINE)

    # `texto` -> texto
    cleaned = re.sub(r"`([^`\n]+)`", r"\1", cleaned)

    # ### texto -> texto
    cleaned = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]+", "", cleaned, flags=re.MULTILINE)

    # **texto** -> texto
    cleaned = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"\1", cleaned)

    # __texto__ -> texto
    cleaned = re.sub(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", r"\1", cleaned)

    # *texto* -> texto (no toca multiplicaciones como 2 * 3)
    cleaned = re.sub(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])", r"\1", cleaned)

    # Restos de ** en una línea propia
    cleaned = re.sub(r"^[ \t]*\*\*[ \t]*$", "", cleaned, flags=re.MULTILINE)

    # Bullets Markdown (-, *, +) -> •
    cleaned = re.sub(r"^[ \t]*[-*+][ \t]+", "• ", cleaned, flags=re.MULTILINE)

    # Espacios al final de línea y saltos de línea excesivos
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
