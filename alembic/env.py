import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from api.models.base import Base
from api.models.event import Event  # noqa: F401
from api.models.job import Job  # noqa: F401
from api.models.sourcetype_config import SourcetypeConfigModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_LOCAL_FALLBACK = (
    "postgresql+asyncpg://logsentinel:logsentinel@localhost:5432/logsentinel"
)
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # Surfaces loudly in Railway / Docker deploy logs where falling back to
    # localhost produces a cryptic psycopg2 "connection refused" instead of
    # the real cause (missing env var). Still falls through for local dev so
    # `make migrate` works out of the box against docker-compose postgres.
    print(
        "WARNING: DATABASE_URL is not set — falling back to localhost default. "
        "On a deployed environment this means the Postgres plugin's URL was "
        "not wired into this service.",
        file=sys.stderr,
    )
    db_url = _LOCAL_FALLBACK

# Railway / Heroku-style plugins hand out `postgresql://...` or `postgres://...`.
# Alembic runs sync, so strip `+asyncpg` and normalize the legacy `postgres://`
# scheme that SQLAlchemy 2 no longer accepts.
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
sync_url = db_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
