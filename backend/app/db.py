"""Motor y sesión de BD para la API."""

import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock"
)
# El pipeline (PIPELINE_DATA=auto) decide RepoDB vs RepoCSV mirando la env var;
# si la API corre con el default local, publicarlo para que use la MISMA BD.
os.environ.setdefault("DATABASE_URL", DATABASE_URL)
engine = create_engine(DATABASE_URL)


def get_db():
    with Session(engine) as s:
        yield s


Db = Annotated[Session, Depends(get_db)]
