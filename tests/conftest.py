"""Pytest setup for an isolated PostgreSQL database."""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
config = dotenv_values(PROJECT_ROOT / ".env")
base_database_url = config.get("DATABASE_URL")
if not base_database_url:
    raise RuntimeError("DATABASE_URL must be configured in .env to run tests")

base_url = make_url(base_database_url)
test_database_name = f"{base_url.database}_test"
test_url = base_url.set(database=test_database_name)

# Create the test database on the same local PostgreSQL instance when needed.
maintenance_url = base_url.set(database="postgres")
maintenance_engine = create_engine(maintenance_url)
with maintenance_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
    exists = connection.scalar(
        text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
        {"database_name": test_database_name},
    )
    if not exists:
        quoted_name = test_database_name.replace('"', '""')
        connection.exec_driver_sql(f'CREATE DATABASE "{quoted_name}"')
maintenance_engine.dispose()

os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
# Tests must never use the real network, even when the developer's .env
# contains production-compatible provider settings.
os.environ["EMBEDDING_PROVIDER"] = "fake"
for _name in (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_TIMEOUT_SECONDS",
):
    os.environ[_name] = ""

from backend.app.database import Base, engine  # noqa: E402
from backend.app import models  # noqa: E402,F401

with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(bind=engine)

# The isolated test database may still contain the old vector(8) column from
# earlier runs. Reset only this test database column to the current dimension.
from backend.app.embedding import EMBEDDING_DIMENSION  # noqa: E402

with engine.begin() as connection:
    connection.execute(
        text(
            "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding"
        )
    )
    connection.execute(
        text(
            "ALTER TABLE document_chunks "
            f"ADD COLUMN embedding vector({EMBEDDING_DIMENSION})"
        )
    )
