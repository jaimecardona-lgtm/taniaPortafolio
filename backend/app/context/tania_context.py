"""Contexto personal dinámico de Tania para el modelo (edad y cumpleaños).

La fecha biográfica es la misma que usa el frontend en
portafolio-react/src/features/assistant/birthDateUtils.js.
La edad se calcula en cada request; nunca se hardcodea.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

TANIA_BIRTH_DATE = date(2003, 2, 24)
TANIA_TIMEZONE = ZoneInfo("America/Bogota")

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def _today_in_bogota() -> date:
    return datetime.now(TANIA_TIMEZONE).date()


def _format_date(value: date) -> str:
    return f"{value.day} de {_MESES[value.month - 1]} de {value.year}"


def get_tania_age(today: date | None = None) -> int:
    """Edad cumplida a la fecha dada (por defecto, hoy en America/Bogota)"""
    if today is None:
        today = _today_in_bogota()

    age = today.year - TANIA_BIRTH_DATE.year
    if (today.month, today.day) < (TANIA_BIRTH_DATE.month, TANIA_BIRTH_DATE.day):
        age -= 1
    return age


def get_next_birthday(today: date) -> date:
    """Próximo cumpleaños estrictamente posterior a hoy"""
    this_year = date(today.year, TANIA_BIRTH_DATE.month, TANIA_BIRTH_DATE.day)
    if this_year > today:
        return this_year
    return date(today.year + 1, TANIA_BIRTH_DATE.month, TANIA_BIRTH_DATE.day)


def build_tania_dynamic_context(today: date | None = None) -> str:
    """Datos verificables para el modelo, calculados con la fecha actual"""
    if today is None:
        today = _today_in_bogota()

    age = get_tania_age(today)
    is_birthday = (today.month, today.day) == (
        TANIA_BIRTH_DATE.month,
        TANIA_BIRTH_DATE.day,
    )

    lines = [
        "Datos personales verificables:",
        f"Tania nació el {_format_date(TANIA_BIRTH_DATE)}.",
    ]

    if is_birthday:
        lines.append(f"Hoy es el cumpleaños de Tania. Cumple {age} años hoy.")
    else:
        lines.append(f"Actualmente tiene {age} años.")
        next_birthday = get_next_birthday(today)
        lines.append(f"Su próximo cumpleaños es el {_format_date(next_birthday)}.")

    lines.append(f"La fecha actual en Colombia es {_format_date(today)}.")
    return "\n".join(lines)
