"""
Подключение к MySQL — один движок на процесс.

Было: MysqlDatabase() в каждой функции crud.py создавал новый create_engine,
то есть новый пул соединений. session.close() закрывает сессию, но не движок —
пулы копились в памяти до конца прогона вместе с открытыми соединениями к базе.

Стало: движок создаётся лениво, один раз на процесс. Сессии берутся из
session_scope(), который сам коммитит при успехе и откатывает при ошибке.

Про multiprocessing: main.py разводит операторов по процессам. Соединения,
открытые до fork, в дочернем процессе ломаются (два процесса пишут в один сокет),
поэтому в начале каждого дочернего процесса надо вызвать reset_pool().
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config

BASE = declarative_base()

_engine = None
_SessionFactory = None


def get_engine():
    """Движок на процесс. Создаётся при первом обращении."""
    global _engine, _SessionFactory
    if _engine is None:
        _engine = create_engine(
            str(config.connection_mysql),
            connect_args={"ssl_ca": "certs/root.crt"},
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,   # прогон идёт часами, MySQL рвёт простаивающие
            pool_recycle=1800,    # соединения по wait_timeout — переподключаемся сами
            future=False,
        )
        _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session():
    """Новая сессия. Закрывать обязан вызывающий — проще брать session_scope()."""
    get_engine()
    return _SessionFactory()


@contextmanager
def session_scope():
    """
    Сессия на блок работы: коммит при успехе, откат при исключении, закрытие всегда.

        with session_scope() as session:
            ...
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_pool() -> None:
    """
    Сбросить унаследованные после fork соединения.
    Вызывать первой строкой в теле дочернего процесса.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()


class MysqlDatabase:
    """
    Оставлено для совместимости со старым кодом, который делает MysqlDatabase().session.
    Движок больше не создаётся заново — отдаётся общий.
    """

    BASE = BASE

    def __init__(self):
        get_engine()
        self.__session = _SessionFactory()

    @property
    def session(self):
        return self.__session

    @property
    def engine(self):
        return get_engine()
