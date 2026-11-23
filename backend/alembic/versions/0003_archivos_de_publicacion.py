"""archivos multiples por publicacion

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publicacion_archivos",
        sa.Column("publicacion_id", sa.Integer(), nullable=False),
        sa.Column("archivo_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("etiqueta", sa.String(length=200), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["archivo_id"], ["archivos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["publicacion_id"], ["publicaciones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("publicacion_id", "archivo_id"),
    )
    op.execute(
        """
        INSERT INTO publicacion_archivos (publicacion_id, archivo_id, tipo, etiqueta, orden)
        SELECT id, archivo_id, 'convocatoria', 'Convocatoria', 0
        FROM publicaciones
        WHERE archivo_id IS NOT NULL
        """
    )
    op.drop_constraint("publicaciones_archivo_id_fkey", "publicaciones", type_="foreignkey")
    op.drop_column("publicaciones", "archivo_id")


def downgrade() -> None:
    op.add_column("publicaciones", sa.Column("archivo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "publicaciones_archivo_id_fkey", "publicaciones", "archivos",
        ["archivo_id"], ["id"]
    )
    op.execute(
        """
        UPDATE publicaciones p
        SET archivo_id = pa.archivo_id
        FROM publicacion_archivos pa
        WHERE pa.publicacion_id = p.id
          AND pa.tipo = 'convocatoria'
        """
    )
    op.drop_table("publicacion_archivos")
