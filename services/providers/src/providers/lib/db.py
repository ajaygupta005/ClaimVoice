"""SQLAlchemy session factory for the providers service."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal = None


def _normalise_url(url: str) -> str:
    if url.startswith("postgresql"):
        scheme, rest = url.split("://", 1)
        base = scheme.split("+")[0]
        url = f"{base}+psycopg://{rest}"
    return url


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        raw = os.environ.get("DATABASE_URL", "")
        if not raw:
            raise RuntimeError("DATABASE_URL is not set")
        url = _normalise_url(raw)
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session() -> Session:
    _get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
