"""solicitudes, requisitos y recepción

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("programas", sa.Column("solicitud_en_linea", sa.Boolean(), nullable=False,
                                         server_default=sa.false()))
    op.execute(
        """
        UPDATE programas
        SET solicitud_en_linea = TRUE
        WHERE clave IN ('capturando_carbono', 'plantaciones_sustentables',
                        'restauracion_hidrologico_forestal')
        """
    )
    op.create_table(
        "solicitudes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitante_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("programa_id", sa.Integer(), sa.ForeignKey("programas.id"), nullable=False),
        sa.Column("municipio_id", sa.Integer(), sa.ForeignKey("municipios.id"), nullable=False),
        sa.Column("region_id", sa.Integer(), sa.ForeignKey("regiones.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="borrador"),
        sa.Column("datos_501", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("datos_502", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("aviso_privacidad", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creada_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actualizada_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("enviada_en", sa.DateTime(timezone=True)),
        sa.Column("recibida_en", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "requisitos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clave", sa.String(60), nullable=False, unique=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False, server_default=""),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "documentos_solicitud",
        sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("requisito_id", sa.Integer(), sa.ForeignKey("requisitos.id"), primary_key=True),
        sa.Column("archivo_id", sa.Integer(), sa.ForeignKey("archivos.id")),
        sa.Column("entregado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("observacion", sa.String(500), nullable=False, server_default=""),
    )
    op.create_table(
        "recepciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("receptor_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=False, server_default=""),
        sa.Column("recibida_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "folios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("consecutivo", sa.Integer(), nullable=False),
        sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes.id"), nullable=False, unique=True),
        sa.Column("valor", sa.String(40), nullable=False, unique=True),
        sa.UniqueConstraint("anio", "consecutivo", name="uq_folio_anio_consecutivo"),
    )
    op.create_table(
        "acuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes.id"), nullable=False, unique=True),
        sa.Column("archivo_id", sa.Integer(), sa.ForeignKey("archivos.id"), nullable=False),
        sa.Column("generado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("acuses")
    op.drop_table("folios")
    op.drop_table("recepciones")
    op.drop_table("documentos_solicitud")
    op.drop_table("requisitos")
    op.drop_table("solicitudes")
    op.drop_column("programas", "solicitud_en_linea")
