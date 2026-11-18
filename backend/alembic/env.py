from alembic import context
from sqlalchemy import create_engine

from app.modelos import Base
from app.nucleo.configuracion import obtener_configuracion

target_metadata = Base.metadata


def correr_migraciones() -> None:
    motor = create_engine(obtener_configuracion().url_base_datos)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


correr_migraciones()
