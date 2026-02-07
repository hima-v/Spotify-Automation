"""Alembic env; reads DATABASE_URL from environment."""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.session import Base
# Import models so Base.metadata is populated when you add them
# from app.db import models  # noqa: F401

target_metadata = Base.metadata


def get_url():
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/spotify_playlist")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
