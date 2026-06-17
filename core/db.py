from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        # SQLite needs this flag when used across the test session; it is
        # harmless for Postgres because the branch only applies to sqlite URLs.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, future=True, connect_args=connect_args)
    return _engine


def get_session_factory():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), future=True, expire_on_commit=False)
    return _Session


@contextmanager
def session_scope():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_for_tests(url):
    """Point the engine at a throwaway database. Test-only helper."""
    global _engine, _Session
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, future=True, connect_args=connect_args)
    _Session = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine
