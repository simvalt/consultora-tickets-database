"""Permisos propios por usuario (override por módulo sobre los del rol).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_permissions (
            user_id integer  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module  varchar(30) NOT NULL,
            level   smallint NOT NULL,
            PRIMARY KEY (user_id, module),
            CONSTRAINT ck_user_permissions_module
                CHECK (module IN ('tickets', 'users', 'roles', 'clients', 'dashboard')),
            CONSTRAINT ck_user_permissions_level CHECK (level BETWEEN 0 AND 4)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_permissions;")
