"""perfil de usuario

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("apellido_paterno", sa.String(length=80), nullable=True))
    op.add_column("usuarios", sa.Column("apellido_materno", sa.String(length=80), nullable=True))
    op.execute("UPDATE usuarios SET apellido_paterno = '', apellido_materno = ''")
    op.execute("ALTER TABLE usuarios ALTER COLUMN apellido_paterno SET NOT NULL")
    op.execute("ALTER TABLE usuarios ALTER COLUMN apellido_materno SET NOT NULL")
    op.execute("ALTER TABLE usuarios ALTER COLUMN nombre TYPE VARCHAR(80)")


def downgrade() -> None:
    op.execute("UPDATE usuarios SET nombre = nombre")
    op.drop_column("usuarios", "apellido_materno")
    op.drop_column("usuarios", "apellido_paterno")
    op.execute("ALTER TABLE usuarios ALTER COLUMN nombre TYPE VARCHAR(160)")
