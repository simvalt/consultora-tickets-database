"""Carga de datos iniciales y de demostración.

Uso:
    python seed/seed.py base   # catálogo, rol Administrador y admin inicial (idempotente)
    python seed/seed.py demo   # datos de demostración (SOLO local; idempotente)

Variables: DATABASE_URL, APP_ENV, ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME, DEMO_PASSWORD.
Las contraseñas se almacenan con argon2id (mismos parámetros por defecto que el backend).
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import psycopg
from argon2 import PasswordHasher

MODULES = ["tickets", "users", "roles", "clients", "dashboard"]

CATEGORIES = [
    (1, "incidente", "Incidente"),
    (2, "requerimiento", "Requerimiento"),
    (3, "consulta", "Consulta"),
    (4, "cambio", "Cambio"),
    (5, "soporte", "Soporte técnico"),
    (6, "otro", "Otro"),
]

# nombre, descripción, niveles (tickets, users, roles, clients, dashboard)
DEMO_ROLES = [
    ("Supervisor", "Gestiona tickets y clientes; consulta usuarios", (4, 1, 0, 3, 1)),
    ("Agente", "Atiende tickets y consulta clientes", (3, 0, 0, 1, 1)),
    ("Capturista", "Registra tickets sin modificarlos", (2, 0, 0, 1, 0)),
    ("Consulta", "Solo lectura", (1, 0, 0, 1, 1)),
]

DEMO_USERS = [
    ("supervisor@consultora.local", "Sofía Ramírez", "Supervisor"),
    ("agente1@consultora.local", "Carlos Méndez", "Agente"),
    ("agente2@consultora.local", "Lucía Fernández", "Agente"),
    ("agente3@consultora.local", "Miguel Torres", "Agente"),
    ("capturista@consultora.local", "Elena Ortiz", "Capturista"),
    ("consulta@consultora.local", "Pablo Herrera", "Consulta"),
]

DEMO_CLIENTS = [
    ("Acme Industrial", "Ana Beltrán", "ana@acme.example"),
    ("Banco Horizonte", "Luis Quintero", "luis@horizonte.example"),
    ("Clínica San Rafael", "Marta Salas", "marta@sanrafael.example"),
    ("Distribuidora Norte", "Jorge Paz", "jorge@dnorte.example"),
    ("Educa Futuro", "Rosa Vidal", "rosa@educafuturo.example"),
    ("Finanzas Delta", "Iván Cruz", "ivan@delta.example"),
    ("Logística Rápida", "Nora Lima", "nora@lograpida.example"),
    ("Retail Centro", "Hugo Mora", "hugo@retailcentro.example"),
]

TITLES = [
    "No funciona el acceso a la VPN", "Solicitud de alta de usuario", "Error al generar reporte mensual",
    "Lentitud en el sistema de facturación", "Cambio de configuración del firewall",
    "Consulta sobre licencias de software", "Fallo en respaldo nocturno", "Instalación de certificado SSL",
    "Impresora de recepción sin conexión", "Migración de buzón de correo", "Actualización de servidor de aplicaciones",
    "Caída del portal de clientes", "Solicitud de nuevo módulo de reportes", "Restablecer acceso a base de datos",
    "Revisión de permisos en carpeta compartida", "Alerta de disco lleno en servidor",
]

PATHS = {
    "sin_inicio": [[]],
    "iniciado": [["iniciado"]],
    "en_proceso": [["iniciado", "en_proceso"]],
    "pendiente": [["iniciado", "en_proceso", "pendiente"]],
    "cerrado": [["iniciado", "en_proceso", "cerrado"], ["iniciado", "en_proceso", "pendiente", "en_proceso", "cerrado"]],
    "cancelado": [["cancelado"], ["iniciado", "cancelado"]],
    "rechazado": [["rechazado"]],
}
REASONS = {
    "pendiente": "En espera de información del cliente",
    "cancelado": "El cliente retiró la solicitud",
    "rechazado": "Fuera del alcance del contrato",
    "cerrado": "Se aplicó la solución y el cliente confirmó el resultado",
}

hasher = PasswordHasher()

# Contraseñas publicadas en la documentación (.env.example). Sólo se aceptan en APP_ENV=local.
EXAMPLE_PASSWORDS = {"Admin#Local1234", "Demo#Local1234"}


def check_not_example(password: str, variable: str) -> None:
    env = os.environ.get("APP_ENV", "local").lower()
    if env != "local" and password in EXAMPLE_PASSWORDS:
        sys.exit(f"{variable} es la contraseña de ejemplo publicada en la documentación; con APP_ENV={env} "
                 "define una propia.")


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Define DATABASE_URL")
    return psycopg.connect(url)


def seed_base(cur: psycopg.Cursor) -> None:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        sys.exit("Define ADMIN_EMAIL y ADMIN_PASSWORD para crear el administrador inicial.")
    if len(password) < 12:
        sys.exit("ADMIN_PASSWORD debe tener al menos 12 caracteres.")
    check_not_example(password, "ADMIN_PASSWORD")
    name = os.environ.get("ADMIN_NAME") or "Administrador"

    for cid, code, cname in CATEGORIES:
        cur.execute(
            "INSERT INTO ticket_categories (id, code, name) VALUES (%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (cid, code, cname),
        )
    cur.execute(
        "INSERT INTO roles (name, description) VALUES ('Administrador','Acceso completo al sistema') "
        "ON CONFLICT DO NOTHING"
    )
    cur.execute("SELECT id FROM roles WHERE lower(name)='administrador'")
    role_id = cur.fetchone()[0]
    for module in MODULES:
        cur.execute(
            "INSERT INTO role_permissions (role_id, module, level) VALUES (%s,%s,4) "
            "ON CONFLICT (role_id, module) DO NOTHING",
            (role_id, module),
        )
    cur.execute("SELECT 1 FROM users WHERE lower(email)=lower(%s)", (email,))
    if cur.fetchone():
        print(f"Administrador {email} ya existe; sin cambios.")
    else:
        cur.execute(
            "INSERT INTO users (email, full_name, password_hash, role_id) VALUES (%s,%s,%s,%s)",
            (email, name, hasher.hash(password), role_id),
        )
        print(f"Administrador inicial creado: {email}")


def ts(base: datetime, **kw) -> datetime:
    return base + timedelta(**kw)


def seed_demo(cur: psycopg.Cursor) -> None:
    if os.environ.get("APP_ENV", "local").lower() == "production":
        sys.exit("El seed demo está deshabilitado con APP_ENV=production.")
    password = os.environ.get("DEMO_PASSWORD")
    if not password or len(password) < 12:
        sys.exit("Define DEMO_PASSWORD (mínimo 12 caracteres).")
    check_not_example(password, "DEMO_PASSWORD")
    cur.execute("SELECT count(*) FROM tickets")
    if cur.fetchone()[0] > 0:
        print("Ya existen tickets; el seed demo no se vuelve a aplicar.")
        return

    cur.execute("SELECT id FROM users ORDER BY id LIMIT 1")
    row = cur.fetchone()
    if not row:
        sys.exit("Ejecuta primero `seed.py base`.")
    admin_id = row[0]

    role_ids = {}
    for rname, desc, levels in DEMO_ROLES:
        cur.execute(
            "INSERT INTO roles (name, description) VALUES (%s,%s) "
            "ON CONFLICT (lower(name)) DO UPDATE SET description=EXCLUDED.description RETURNING id",
            (rname, desc),
        )
        rid = cur.fetchone()[0]
        role_ids[rname] = rid
        for module, level in zip(MODULES, levels):
            cur.execute(
                "INSERT INTO role_permissions (role_id, module, level) VALUES (%s,%s,%s) "
                "ON CONFLICT (role_id, module) DO UPDATE SET level=EXCLUDED.level",
                (rid, module, level),
            )

    pw_hash = hasher.hash(password)
    user_ids = {}
    for email, fname, rname in DEMO_USERS:
        cur.execute(
            "INSERT INTO users (email, full_name, password_hash, role_id) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (lower(email)) DO UPDATE SET full_name=EXCLUDED.full_name RETURNING id",
            (email, fname, pw_hash, role_ids[rname]),
        )
        user_ids[email] = cur.fetchone()[0]
    # Un usuario inactivo para probar el bloqueo de acceso.
    cur.execute(
        "INSERT INTO users (email, full_name, password_hash, role_id, is_active) "
        "VALUES ('inactivo@consultora.local','Usuario Inactivo',%s,%s,false) ON CONFLICT (lower(email)) DO NOTHING",
        (pw_hash, role_ids["Agente"]),
    )

    client_ids = []
    for cname, contact, email in DEMO_CLIENTS:
        cur.execute(
            "INSERT INTO clients (name, contact_name, email) VALUES (%s,%s,%s) "
            "ON CONFLICT (lower(name)) DO UPDATE SET contact_name=EXCLUDED.contact_name RETURNING id",
            (cname, contact, email),
        )
        client_ids.append(cur.fetchone()[0])
    cur.execute(
        "INSERT INTO clients (name, contact_name, is_active) VALUES ('Cliente Histórico','Contacto',false) "
        "ON CONFLICT (lower(name)) DO NOTHING"
    )

    agents = [user_ids[e] for e, _, r in DEMO_USERS if r == "Agente"]
    authors = agents + [user_ids["supervisor@consultora.local"], user_ids["capturista@consultora.local"], admin_id]
    rnd = random.Random(42)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    statuses = (["sin_inicio"] * 10 + ["iniciado"] * 8 + ["en_proceso"] * 14 + ["pendiente"] * 8
                + ["cerrado"] * 26 + ["cancelado"] * 6 + ["rechazado"] * 4)
    priorities = ["baja"] * 3 + ["media"] * 5 + ["alta"] * 3 + ["critica"] * 1
    open_states = {"sin_inicio", "iniciado", "en_proceso", "pendiente"}

    for i in range(76):
        final = statuses[i % len(statuses)] if i < len(statuses) else rnd.choice(statuses)
        created = now - timedelta(days=rnd.uniform(0.2, 60))
        creator = rnd.choice(authors)
        assignee = rnd.choice(agents) if final != "sin_inicio" else None
        # Algunos sin_inicio ya tienen responsable; los rechazados/cancelados directos no.
        path = rnd.choice(PATHS[final])
        if final == "sin_inicio" and rnd.random() < 0.25:
            assignee = rnd.choice(agents)
        if final in {"rechazado"} or path == ["cancelado"]:
            assignee = None
        reopened = final == "cerrado" and rnd.random() < 0.2
        if reopened:
            path = ["iniciado", "en_proceso", "cerrado", "en_proceso"]
            final = "en_proceso"

        priority = rnd.choice(priorities)
        title = f"{rnd.choice(TITLES)}"
        due = None
        if rnd.random() < 0.7:
            due = created + timedelta(days=rnd.choice([2, 5, 7, 14, 21]))
        # Garantiza algunos vencidos: abiertos con vencimiento pasado.
        if final in open_states and i % 5 == 0:
            due = now - timedelta(days=rnd.uniform(0.5, 6))

        events = [("created", None, "sin_inicio", None, None, creator, None, created)]
        if assignee and "iniciado" not in path and final == "sin_inicio":
            events.append(("assignment", None, None, None, assignee, creator, None, ts(created, minutes=5)))

        cursor_t = created
        started = closed = None
        status = "sin_inicio"
        cur_assignee = assignee if (final == "sin_inicio" and assignee) else None
        resolution = None
        for step in path:
            cursor_t = min(cursor_t + timedelta(hours=rnd.uniform(1, 30)), now - timedelta(minutes=1))
            if step == "iniciado":
                events.append(("assignment", None, None, cur_assignee, assignee, creator, None, cursor_t))
                cur_assignee = assignee
                started = started or cursor_t
            reason = REASONS.get(step)
            if status == "cerrado" and step == "en_proceso":
                events.append(("reopen", "cerrado", "en_proceso", None, None, creator, "Se detectó que persistía el fallo", cursor_t))
                closed = None
                resolution = None
            else:
                events.append(("status_change", status, step, None, None, creator, reason, cursor_t))
            if step == "cerrado":
                closed = cursor_t
                resolution = REASONS["cerrado"]
            status = step

        cur.execute(
            "INSERT INTO tickets (title, description, client_id, category_id, priority, status, created_by, "
            "assignee_id, resolution, created_at, updated_at, started_at, closed_at, due_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (title, f"{title}. Detalle reportado por el cliente; ver comentarios para seguimiento.",
             rnd.choice(client_ids), rnd.randint(1, 6), priority, status, creator, cur_assignee,
             resolution, created, cursor_t, started, closed, due),
        )
        ticket_id = cur.fetchone()[0]
        for et, fs, tos, fa, ta, actor, reason, at in events:
            cur.execute(
                "INSERT INTO ticket_events (ticket_id, event_type, from_status, to_status, from_assignee_id, "
                "to_assignee_id, actor_id, reason, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (ticket_id, et, fs, tos, fa, ta, actor, reason, at),
            )
        for _ in range(rnd.randint(0, 3)):
            at = created + (cursor_t - created) * rnd.random()
            cur.execute(
                "INSERT INTO ticket_comments (ticket_id, author_id, body, created_at) VALUES (%s,%s,%s,%s)",
                (ticket_id, rnd.choice(authors),
                 rnd.choice(["Se contactó al cliente.", "Pendiente de validar con el equipo de infraestructura.",
                             "Se realizaron pruebas sin éxito, se escala.", "Confirmado el síntoma en producción."]), at),
            )
    print(f"Datos de demostración cargados (APP_ENV={os.environ.get('APP_ENV', 'local')}).")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"base", "demo"}:
        sys.exit(__doc__)
    with connect() as conn:
        with conn.cursor() as cur:
            (seed_base if sys.argv[1] == "base" else seed_demo)(cur)
        conn.commit()


if __name__ == "__main__":
    main()
