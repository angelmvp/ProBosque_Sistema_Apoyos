"""Fecha de hoy en la zona horaria del Estado de México (las pruebas pueden sustituirla)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Mexico_City")


def fecha_hoy() -> date:
    return datetime.now(ZONA).date()
