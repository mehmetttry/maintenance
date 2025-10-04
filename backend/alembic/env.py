# backend/alembic/env.py
from logging.config import fileConfig
import os, sys
from alembic import context

# --- Proje kökünü PYTHONPATH'e ekle (.. = backend) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Uygulamanın engine & metadata'sını kullan
from app.core.db import engine as app_engine, Base  # <-- kritik
# (Modeller import edilince metadata dolu olur)
from app import models  # noqa: F401

# Alembic config & logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = str(app_engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=False,
        render_as_batch=(app_engine.dialect.name == "sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = app_engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=False,
            render_as_batch=(app_engine.dialect.name == "sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
