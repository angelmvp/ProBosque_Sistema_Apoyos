"""Asistente de solicitudes, checklist documental, superficies y folios."""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("requisitos", sa.Column("numero", sa.Integer(), nullable=True))
    op.add_column("requisitos", sa.Column("grupo", sa.String(40), nullable=False,
                                          server_default="identidad_representacion"))
    op.add_column("requisitos", sa.Column("programas", sa.JSON(), nullable=False,
                                          server_default=sa.text("'[]'")))
    op.add_column("requisitos", sa.Column("tipos_persona", sa.JSON(), nullable=False,
                                          server_default=sa.text("'[]'")))
    op.add_column("recepciones", sa.Column("solicitud_completa", sa.Boolean(), nullable=False,
                                           server_default=sa.false()))
    op.add_column("recepciones", sa.Column("documentos_legibles", sa.Boolean(), nullable=False,
                                           server_default=sa.false()))
    op.add_column("recepciones", sa.Column("corresponden_al_programa", sa.Boolean(), nullable=False,
                                           server_default=sa.false()))
    op.create_table(
        "conceptos_superficie",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clave", sa.String(80), nullable=False, unique=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("programa_clave", sa.String(80), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "superficies_solicitud",
        sa.Column("solicitud_id", sa.Integer(),
                  sa.ForeignKey("solicitudes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("concepto_id", sa.Integer(),
                  sa.ForeignKey("conceptos_superficie.id"), primary_key=True),
        sa.Column("hectareas", sa.Numeric(12, 3), nullable=False),
    )
    op.create_table(
        "contadores_folio",
        sa.Column("anio", sa.Integer(), primary_key=True),
        sa.Column("consecutivo", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        INSERT INTO contadores_folio (anio, consecutivo)
        SELECT anio, MAX(consecutivo) FROM folios GROUP BY anio
        """
    )


def downgrade() -> None:
    op.drop_table("contadores_folio")
    op.drop_table("superficies_solicitud")
    op.drop_table("conceptos_superficie")
    op.drop_column("recepciones", "corresponden_al_programa")
    op.drop_column("recepciones", "documentos_legibles")
    op.drop_column("recepciones", "solicitud_completa")
    op.drop_column("requisitos", "tipos_persona")
    op.drop_column("requisitos", "programas")
    op.drop_column("requisitos", "grupo")
    op.drop_column("requisitos", "numero")
