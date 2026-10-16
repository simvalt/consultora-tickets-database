# Modelo de datos

PostgreSQL 16. Fechas en `timestamptz` (UTC). Esquema definido únicamente en `alembic/versions/`.

```
roles 1──* role_permissions (role_id, module, level 0..4)
roles 1──* users 1──* refresh_tokens
users ─┬─< tickets (created_by, assignee_id, deleted_by)
clients 1──* tickets *──1 ticket_categories
tickets 1──* ticket_comments (author_id → users)
tickets 1──* ticket_events  (actor_id → users)
```

| Tabla | Notas |
|---|---|
| `roles` | Dinámicos. Nombre único (insensible a mayúsculas). `is_active` para desactivar sin perder referencias. |
| `role_permissions` | PK `(role_id, module)`. `module` ∈ tickets, users, roles, clients, dashboard. `level` 0 nada, 1 leer, 2 insertar, 3 editar, 4 eliminar (acumulativo). |
| `users` | Email único insensible a mayúsculas, `password_hash` argon2id, un rol por usuario, `is_active`. Nunca se borran. |
| `refresh_tokens` | Solo se guarda el SHA-256 del token opaco; `revoked_at` para logout/rotación. |
| `clients` | Nombre único; se desactivan (no se borran). |
| `ticket_categories` | Catálogo fijo sembrado por el seed base (6 categorías). |
| `tickets` | Folio `TCK-000001` generado por la secuencia `ticket_folio_seq` (columna `folio` UNIQUE con DEFAULT). Eliminación lógica con `deleted_at/deleted_by`. |
| `ticket_comments` | Comentarios internos; no vacíos. |
| `ticket_events` | Historial: `created`, `status_change`, `assignment`, `reopen`, `deleted`, con estatus/responsable anterior y nuevo, actor y motivo. |

## Restricciones relevantes

- `ck_tickets_status`, `ck_tickets_priority`: valores permitidos.
- `ck_tickets_assignee_required`: estatus iniciado, en_proceso, pendiente y cerrado exigen responsable.
- `ck_tickets_closed_at`: `closed_at` existe si y solo si el estatus es `cerrado` (la reapertura lo limpia; el evento histórico se conserva en `ticket_events`).
- `ck_tickets_deleted`: `deleted_at` y `deleted_by` van juntos.
- Claves foráneas sin `ON DELETE CASCADE` hacia tablas de negocio (preserva histórico); solo `role_permissions` y `refresh_tokens` se borran en cascada.

## Índices

- Parciales (`WHERE deleted_at IS NULL`) sobre `status`, `priority`, `client_id`, `category_id`, `assignee_id`, `created_at`; `due_at` parcial para vencidos.
- GIN trigram (`pg_trgm`) en `title` y `description` para búsqueda `ILIKE`; el folio usa el índice único.
- `ticket_events (ticket_id, created_at)` para el historial y un índice parcial de eventos de cierre para la serie "cerrados por día".

## "Administrador"

No hay bandera especial: un administrador es un usuario activo con rol activo que tiene nivel 4 en **todos** los módulos. El seed base crea el rol "Administrador" y un usuario inicial (ADMIN_EMAIL / ADMIN_PASSWORD). El backend impide dejar el sistema sin ninguno.
