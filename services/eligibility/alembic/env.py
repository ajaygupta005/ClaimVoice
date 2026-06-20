"""Alembic migration environment for the eligibility service.

The schema is defined imperatively in versions/ (no ORM models), so
``target_metadata`` is ``None`` — we only run the explicit upgrade/downgrade
scripts, never autogenerate.

The database URL comes from the ``DATABASE_URL`` environment variable and is
normalized to the psycopg (v3) driver, which is the only Postgres driver the
project installs (psycopg2 is absent).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object (reads alembic.ini).
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM metadata — migrations are explicit.
target_metadata = None

_DEFAULT_URL = "postgresql://localhost/claimvoice"


def _database_url() -> str:
    """Resolve DATABASE_URL and force the psycopg (v3) SQLAlchemy driver."""
    url = os.environ.get("DATABASE_URL", _DEFAULT_URL)
    # SQLAlchemy defaults bare ``postgresql://`` to psycopg2; pin to psycopg v3.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def run_migrations_offline() -> None:
    """Run migrations without a DB-API connection (emit SQL)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
