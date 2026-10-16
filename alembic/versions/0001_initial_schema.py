"""Esquema inicial del sistema de tickets.

Revision ID: 0001
Revises:
Create Date: 2026-10-16
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

UP = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------- roles
CREATE TABLE roles (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        varchar(80)  NOT NULL,
    description varchar(255) NOT NULL DEFAULT '',
    is_active   boolean      NOT NULL DEFAULT true,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_roles_name_lower ON roles (lower(name));

-- Niveles acumulativos: 0 nada, 1 leer, 2 insertar, 3 editar, 4 eliminar.
CREATE TABLE role_permissions (
    role_id integer  NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    module  varchar(30) NOT NULL,
    level   smallint NOT NULL DEFAULT 0,
    PRIMARY KEY (role_id, module),
    CONSTRAINT ck_role_permissions_module
        CHECK (module IN ('tickets', 'users', 'roles', 'clients', 'dashboard')),
    CONSTRAINT ck_role_permissions_level CHECK (level BETWEEN 0 AND 4)
);

-- ---------------------------------------------------------------- users
CREATE TABLE users (
    id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         varchar(255) NOT NULL,
    full_name     varchar(150) NOT NULL,
    password_hash varchar(255) NOT NULL,
    role_id       integer      NOT NULL REFERENCES roles(id),
    is_active     boolean      NOT NULL DEFAULT true,
    last_login_at timestamptz,
    created_at    timestamptz  NOT NULL DEFAULT now(),
    updated_at    timestamptz  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));
CREATE INDEX ix_users_role_id ON users (role_id);

CREATE TABLE refresh_tokens (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     integer      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  char(64)     NOT NULL UNIQUE,
    expires_at  timestamptz  NOT NULL,
    revoked_at  timestamptz,
    created_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

-- -------------------------------------------------------------- clients
CREATE TABLE clients (
    id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         varchar(150) NOT NULL,
    contact_name varchar(150) NOT NULL DEFAULT '',
    email        varchar(255) NOT NULL DEFAULT '',
    phone        varchar(40)  NOT NULL DEFAULT '',
    is_active    boolean      NOT NULL DEFAULT true,
    created_at   timestamptz  NOT NULL DEFAULT now(),
    updated_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_clients_name_lower ON clients (lower(name));

-- ----------------------------------------------------------- categorias
CREATE TABLE ticket_categories (
    id   smallint PRIMARY KEY,
    code varchar(30) NOT NULL UNIQUE,
    name varchar(80) NOT NULL
);

-- -------------------------------------------------------------- tickets
CREATE SEQUENCE ticket_folio_seq START 1;

CREATE TABLE tickets (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    folio       varchar(20) NOT NULL UNIQUE
                DEFAULT ('TCK-' || lpad(nextval('ticket_folio_seq')::text, 6, '0')),
    title       varchar(200) NOT NULL,
    description text         NOT NULL DEFAULT '',
    client_id   integer  NOT NULL REFERENCES clients(id),
    category_id smallint NOT NULL REFERENCES ticket_categories(id),
    priority    varchar(10) NOT NULL DEFAULT 'media',
    status      varchar(15) NOT NULL DEFAULT 'sin_inicio',
    created_by  integer  NOT NULL REFERENCES users(id),
    assignee_id integer  REFERENCES users(id),
    resolution  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    started_at  timestamptz,
    closed_at   timestamptz,
    due_at      timestamptz,
    deleted_at  timestamptz,
    deleted_by  integer REFERENCES users(id),
    CONSTRAINT ck_tickets_priority CHECK (priority IN ('baja', 'media', 'alta', 'critica')),
    CONSTRAINT ck_tickets_status CHECK (status IN
        ('sin_inicio', 'iniciado', 'en_proceso', 'pendiente', 'cancelado', 'cerrado', 'rechazado')),
    CONSTRAINT ck_tickets_assignee_required CHECK (
        status IN ('sin_inicio', 'cancelado', 'rechazado') OR assignee_id IS NOT NULL),
    CONSTRAINT ck_tickets_closed_at CHECK ((status = 'cerrado') = (closed_at IS NOT NULL)),
    CONSTRAINT ck_tickets_deleted CHECK ((deleted_at IS NULL) = (deleted_by IS NULL))
);
CREATE INDEX ix_tickets_status      ON tickets (status)      WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_priority    ON tickets (priority)    WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_client_id   ON tickets (client_id)   WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_category_id ON tickets (category_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_assignee_id ON tickets (assignee_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_created_at  ON tickets (created_at)  WHERE deleted_at IS NULL;
CREATE INDEX ix_tickets_due_at      ON tickets (due_at)
    WHERE deleted_at IS NULL AND due_at IS NOT NULL;
CREATE INDEX ix_tickets_created_by  ON tickets (created_by);
CREATE INDEX ix_tickets_title_trgm  ON tickets USING gin (title gin_trgm_ops);
CREATE INDEX ix_tickets_desc_trgm   ON tickets USING gin (description gin_trgm_ops);

CREATE TABLE ticket_comments (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id  bigint  NOT NULL REFERENCES tickets(id),
    author_id  integer NOT NULL REFERENCES users(id),
    body       text    NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_ticket_comments_body CHECK (length(btrim(body)) > 0)
);
CREATE INDEX ix_ticket_comments_ticket ON ticket_comments (ticket_id, created_at);

CREATE TABLE ticket_events (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id        bigint  NOT NULL REFERENCES tickets(id),
    event_type       varchar(20) NOT NULL,
    from_status      varchar(15),
    to_status        varchar(15),
    from_assignee_id integer REFERENCES users(id),
    to_assignee_id   integer REFERENCES users(id),
    actor_id         integer NOT NULL REFERENCES users(id),
    reason           text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_ticket_events_type CHECK (event_type IN
        ('created', 'status_change', 'assignment', 'reopen', 'deleted'))
);
CREATE INDEX ix_ticket_events_ticket ON ticket_events (ticket_id, created_at);
CREATE INDEX ix_ticket_events_closed ON ticket_events (created_at)
    WHERE event_type = 'status_change' AND to_status = 'cerrado';
"""

DOWN = """
DROP TABLE IF EXISTS ticket_events, ticket_comments, tickets, ticket_categories,
    clients, refresh_tokens, users, role_permissions, roles CASCADE;
DROP SEQUENCE IF EXISTS ticket_folio_seq;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
