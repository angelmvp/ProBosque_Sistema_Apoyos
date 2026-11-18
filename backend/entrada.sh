#!/bin/sh
# Arranque del backend: espera la base, migra, carga datos iniciales y levanta la API.
set -e
python - <<'PY'
import time
from sqlalchemy import create_engine, text
from app.nucleo.configuracion import obtener_configuracion
motor = create_engine(obtener_configuracion().url_base_datos)
for intento in range(60):
    try:
        with motor.connect() as c:
            c.execute(text("SELECT 1"))
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("No se pudo conectar a la base de datos.")
PY
alembic upgrade head
python -m app.semillas
exec uvicorn app.main:crear_app --factory --host 0.0.0.0 --port 8000 --reload
