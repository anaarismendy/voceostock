import os

from sqlalchemy import create_engine

from alembic import context
from app.models import Base

target_metadata = Base.metadata

url = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock"
)

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
