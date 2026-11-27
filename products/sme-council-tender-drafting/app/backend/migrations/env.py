"""Alembic environment. Uses DATABASE_URL (or a URL passed in by tests) and the app's models."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (registers every table on Base.metadata)
from app.config import Settings
from app.db import Base
from app.dbauth import attach_entra_token, build_token_provider, validate_entra_url

config = context.config
if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", Settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # DB_AUTH=entra: the same token-as-password sign-in as the app. Tests pass db_auth/token_provider as attributes.
    db_auth = config.attributes.get("db_auth") or Settings().db_auth
    engine = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
                                poolclass=pool.NullPool)
    if db_auth == "entra":
        validate_entra_url(config.get_main_option("sqlalchemy.url").replace("%%", "%"))
        attach_entra_token(engine, config.attributes.get("token_provider")
                           or build_token_provider(Settings().azure_client_id))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
