"""Conexão com o PostgreSQL."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import obter_config


class Base(DeclarativeBase):
    pass


@lru_cache
def obter_engine() -> Engine:
    # Datas sempre em UTC na API; as telas mostram no horário de Brasília.
    return create_engine(
        obter_config().database_url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
    )


@lru_cache
def _fabrica() -> sessionmaker[Session]:
    return sessionmaker(bind=obter_engine(), expire_on_commit=False)


def nova_sessao() -> Session:
    return _fabrica()()


def obter_db() -> Iterator[Session]:
    db = nova_sessao()
    try:
        yield db
    finally:
        db.close()
