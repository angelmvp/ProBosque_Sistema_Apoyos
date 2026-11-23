# Cómo contribuir

- Ramas: `main` estable; trabajo en `feature/hu-XX-descripcion`; cambios por pull request revisado por otra persona.
- Todo en español (código, commits, documentación).
- Antes de subir: `docker compose exec backend pytest -q` y, si tocaste el frontend, `docker compose exec frontend npm run tipos`.
- Respeta las capas: un módulo **no** importa a otro (la prueba de arquitectura falla).
- Cambios en la base: migración Alembic, nunca editar tablas a mano.
- Cada criterio de aceptación nuevo (`HU-XX-CA-N`) lleva su prueba con ese nombre en el docstring.
- Regenera la matriz de roles con `python scripts/generar_matriz_roles.py` desde la raíz; requiere `openpyxl` y genera `docs/matriz-de-roles.xlsx`.
