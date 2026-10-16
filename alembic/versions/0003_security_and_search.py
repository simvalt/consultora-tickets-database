"""Fecha de cambio de contraseña (invalida tokens anteriores) e índice trigram del folio.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users ADD COLUMN password_changed_at timestamptz NOT NULL DEFAULT now();
        -- La búsqueda usa ILIKE '%texto%' sobre el folio: el índice único (btree) no sirve para eso.
        CREATE INDEX ix_tickets_folio_trgm ON tickets USING gin (folio gin_trgm_ops);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_tickets_folio_trgm;
        ALTER TABLE users DROP COLUMN IF EXISTS password_changed_at;
        """
    )
