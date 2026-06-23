"""Lightweight SQLite migrations run on startup."""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from backend.db.base import engine

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    _migrate_users_name_hand_unique()
    _migrate_account_role()
    _ensure_admin_role()
    _migrate_auth_session_columns()
    _ensure_phase1_tables()
    _ensure_phase3_columns()
    _ensure_phase3_tables()
    _ensure_google_sub_column()
    _ensure_customer_auth_columns()
    _ensure_email_verification_table()
    _ensure_training_tables()
    _ensure_password_reset_table()


def _ensure_training_tables() -> None:
    from backend.db.base import Base
    from backend.db import models  # noqa: F401

    insp = inspect(engine)
    existing = set(insp.get_table_names())
    needed = {"training_ingest_log", "training_runs"}
    missing = needed - existing
    if not missing:
        return
    logger.info("Creating training tables: %s", missing)
    Base.metadata.create_all(
        bind=engine,
        tables=[models.TrainingIngestLog.__table__, models.TrainingRun.__table__],
    )


def _ensure_password_reset_table() -> None:
    from backend.db.base import Base
    from backend.db import models  # noqa: F401

    insp = inspect(engine)
    if "password_reset_codes" in insp.get_table_names():
        return
    logger.info("Creating password_reset_codes table")
    Base.metadata.create_all(bind=engine, tables=[models.PasswordResetCode.__table__])


def _migrate_account_role() -> None:
    insp = inspect(engine)
    if "accounts" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("accounts")}
    if "role" in cols:
        return
    logger.info("Adding accounts.role column")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE accounts ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'employee'"))
        conn.commit()


def _ensure_admin_role() -> None:
    """First registered account becomes admin."""
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM accounts ORDER BY id LIMIT 1")).fetchone()
        if row:
            conn.execute(
                text("UPDATE accounts SET role = 'admin' WHERE id = :id"),
                {"id": row[0]},
            )
            conn.commit()


def _migrate_users_name_hand_unique() -> None:
    """Allow the same dataset name for Left and Right (unique on name+hand)."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    if "users" not in tables:
        return

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        ).fetchone()
        if not row or not row[0]:
            return
        create_sql = row[0]
        if "UNIQUE (name, hand)" in create_sql or "UNIQUE(name, hand)" in create_sql:
            return

        logger.info("Migrating users table: unique(name) -> unique(name, hand)")
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(
            text(
                "CREATE TABLE users_new ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "name VARCHAR(128) NOT NULL, "
                "hand VARCHAR(8) NOT NULL, "
                "template_embedding BLOB NOT NULL, "
                "created_at DATETIME NOT NULL, "
                "CONSTRAINT uq_users_name_hand UNIQUE (name, hand))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users_new (id, name, hand, template_embedding, created_at) "
                "SELECT id, name, hand, template_embedding, created_at FROM users"
            )
        )
        conn.execute(text("DROP TABLE users"))
        conn.execute(text("ALTER TABLE users_new RENAME TO users"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_name ON users (name)"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
        logger.info("users table migration complete")


def _migrate_auth_session_columns() -> None:
    insp = inspect(engine)
    if "auth_sessions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("auth_sessions")}
    with engine.connect() as conn:
        if "logout_method" not in cols:
            logger.info("Adding auth_sessions.logout_method")
            conn.execute(text("ALTER TABLE auth_sessions ADD COLUMN logout_method VARCHAR(16)"))
        if "attendance_record_id" not in cols:
            logger.info("Adding auth_sessions.attendance_record_id")
            conn.execute(text("ALTER TABLE auth_sessions ADD COLUMN attendance_record_id INTEGER"))
        conn.commit()


def _ensure_phase1_tables() -> None:
    """Create attendance, invites, settings tables via SQLAlchemy metadata if missing."""
    from backend.db.base import Base
    from backend.db import models  # noqa: F401

    insp = inspect(engine)
    existing = set(insp.get_table_names())
    needed = {"attendance_records", "employee_invites", "company_settings"}
    if needed.issubset(existing):
        return
    logger.info("Creating phase-1 tables: %s", needed - existing)
    Base.metadata.create_all(bind=engine, tables=[
        models.AttendanceRecord.__table__,
        models.EmployeeInvite.__table__,
        models.CompanySettings.__table__,
    ])
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM company_settings WHERE id = 1")).fetchone()
        if not row:
            conn.execute(
                text(
                    "INSERT INTO company_settings (id, work_day_start, grace_minutes, timezone, require_palm_logout) "
                    "VALUES (1, '09:00', 30, 'UTC', 1)"
                )
            )
            conn.commit()
            logger.info("Seeded default company_settings (grace=30min)")


def _ensure_phase3_columns() -> None:
    insp = inspect(engine)
    if "company_settings" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("company_settings")}
    additions = [
        ("exclude_weekends", "BOOLEAN NOT NULL DEFAULT 1"),
        ("half_day_hours", "FLOAT NOT NULL DEFAULT 4.0"),
        ("notify_absent", "BOOLEAN NOT NULL DEFAULT 0"),
        ("notify_weekly_summary", "BOOLEAN NOT NULL DEFAULT 0"),
        ("admin_notify_email", "VARCHAR(256)"),
    ]
    with engine.connect() as conn:
        for name, sql_type in additions:
            if name not in cols:
                logger.info("Adding company_settings.%s", name)
                conn.execute(text(f"ALTER TABLE company_settings ADD COLUMN {name} {sql_type}"))
        conn.commit()


def _ensure_phase3_tables() -> None:
    from backend.db.base import Base
    from backend.db import models  # noqa: F401

    insp = inspect(engine)
    if "company_holidays" in insp.get_table_names():
        return
    logger.info("Creating company_holidays table")
    Base.metadata.create_all(bind=engine, tables=[models.CompanyHoliday.__table__])


def _ensure_google_sub_column() -> None:
    insp = inspect(engine)
    if "accounts" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("accounts")}
    if "google_sub" in cols:
        return
    logger.info("Adding accounts.google_sub column")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE accounts ADD COLUMN google_sub VARCHAR(128)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_google_sub ON accounts (google_sub)"))
        conn.commit()


def _ensure_customer_auth_columns() -> None:
    insp = inspect(engine)
    if "accounts" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("accounts")}
    with engine.connect() as conn:
        if "username" not in cols:
            logger.info("Adding accounts.username column")
            conn.execute(text("ALTER TABLE accounts ADD COLUMN username VARCHAR(64)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_username ON accounts (username)"))
        if "email_verified" not in cols:
            logger.info("Adding accounts.email_verified column")
            conn.execute(text("ALTER TABLE accounts ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
            conn.execute(text("UPDATE accounts SET email_verified = 1 WHERE role != 'customer'"))
        conn.commit()


def _ensure_email_verification_table() -> None:
    from backend.db.base import Base
    from backend.db import models  # noqa: F401

    insp = inspect(engine)
    if "email_verification_codes" in insp.get_table_names():
        return
    logger.info("Creating email_verification_codes table")
    Base.metadata.create_all(bind=engine, tables=[models.EmailVerificationCode.__table__])
