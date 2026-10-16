"""Índice para el orden por defecto del listado de tickets (más recientes primero, desempate por id).

Con 200 000 tickets la primera página pasaba de ordenar todo el conjunto (~37 ms) a leer 20 entradas del índice.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_tickets_created_desc_id ON tickets (created_at DESC NULLS LAST, id) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tickets_created_desc_id")
