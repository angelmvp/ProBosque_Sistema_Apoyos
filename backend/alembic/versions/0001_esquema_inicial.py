"""esquema inicial

Revision ID: 0001
Revises: 
Create Date: 2026-11-17 20:58:32.447696
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('archivos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre_original', sa.String(length=255), nullable=False),
    sa.Column('ruta_relativa', sa.String(length=400), nullable=False),
    sa.Column('tipo_mime', sa.String(length=100), nullable=False),
    sa.Column('tamano_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('permisos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clave', sa.String(length=80), nullable=False),
    sa.Column('descripcion', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clave')
    )
    op.create_table('programas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clave', sa.String(length=60), nullable=False),
    sa.Column('nombre', sa.String(length=160), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clave')
    )
    op.create_table('regiones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clave', sa.String(length=10), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.String(length=400), nullable=False),
    sa.Column('domicilio', sa.String(length=255), nullable=True),
    sa.Column('telefono', sa.String(length=60), nullable=True),
    sa.Column('horario', sa.String(length=120), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clave')
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('clave', sa.String(length=60), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clave')
    )
    op.create_table('expedientes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('folio', sa.String(length=40), nullable=False),
    sa.Column('programa_id', sa.Integer(), nullable=False),
    sa.Column('region_id', sa.Integer(), nullable=False),
    sa.Column('tramite', sa.String(length=160), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['programa_id'], ['programas.id'], ),
    sa.ForeignKeyConstraint(['region_id'], ['regiones.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('folio')
    )
    op.create_table('municipios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('region_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['region_id'], ['regiones.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('roles_permisos',
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('permiso_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['permiso_id'], ['permisos.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('rol_id', 'permiso_id')
    )
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('correo', sa.String(length=255), nullable=False),
    sa.Column('nombre', sa.String(length=160), nullable=False),
    sa.Column('hash_contrasena', sa.String(length=255), nullable=False),
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('region_id', sa.Integer(), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['region_id'], ['regiones.id'], ),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('correo')
    )
    op.create_table('bitacora',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('recurso', sa.String(length=255), nullable=False),
    sa.Column('resultado', sa.String(length=30), nullable=False),
    sa.Column('detalle', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('publicaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('programa_id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('vigencia_inicio', sa.Date(), nullable=False),
    sa.Column('vigencia_fin', sa.Date(), nullable=False),
    sa.Column('archivo_id', sa.Integer(), nullable=True),
    sa.Column('publicada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('publicada_por_id', sa.Integer(), nullable=True),
    sa.Column('creada_por_id', sa.Integer(), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['archivo_id'], ['archivos.id'], ),
    sa.ForeignKeyConstraint(['creada_por_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['programa_id'], ['programas.id'], ),
    sa.ForeignKeyConstraint(['publicada_por_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('publicaciones')
    op.drop_table('bitacora')
    op.drop_table('usuarios')
    op.drop_table('roles_permisos')
    op.drop_table('municipios')
    op.drop_table('expedientes')
    op.drop_table('roles')
    op.drop_table('regiones')
    op.drop_table('programas')
    op.drop_table('permisos')
    op.drop_table('archivos')
    # ### end Alembic commands ###
