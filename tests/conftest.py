"""
Общие фикстуры.

База для тестов — SQLite в памяти. Модели описаны под MySQL, поэтому типы
диалекта (TINYINT, VARCHAR с collation и прочие) переводятся в понятные SQLite
прямо здесь. MySQL для прогона тестов не нужен: pytest запускается где угодно.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Логи тестов — во временную папку, до импорта logging_setup.
os.environ.setdefault("LOG_DIR", tempfile.mkdtemp(prefix="sim_tests_log_"))
os.environ.setdefault("LOG_LEVEL", "DEBUG")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.dialects.mysql import (  # noqa: E402
    DATETIME,
    LONGTEXT,
    SMALLINT,
    TEXT,
    TINYINT,
    VARCHAR,
)
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


# --------------------------------------------------------------------------- #
#  Типы MySQL в SQLite
# --------------------------------------------------------------------------- #

def _register_sqlite_types() -> None:
    for mysql_type, sqlite_sql in (
        (TINYINT, "INTEGER"),
        (SMALLINT, "INTEGER"),
        (LONGTEXT, "TEXT"),
        (TEXT, "TEXT"),
        (DATETIME, "DATETIME"),
    ):
        compiles(mysql_type, "sqlite")(
            lambda element, compiler, _sql=sqlite_sql, **kw: _sql
        )

    compiles(VARCHAR, "sqlite")(
        lambda element, compiler, **kw: f"VARCHAR({element.length or 255})"
    )


_register_sqlite_types()


@pytest.fixture(scope="session", autouse=True)
def _strip_collations():
    """SQLite не знает utf8mb3_unicode_ci — убираем collation из всех колонок."""
    import database.mysql_models as models

    for table in models.Base.metadata.tables.values():
        for column in table.columns:
            if getattr(column.type, "collation", None):
                column.type.collation = None
    return True


# --------------------------------------------------------------------------- #
#  База
# --------------------------------------------------------------------------- #


@pytest.fixture
def db(_strip_collations):
    """
    Чистая база на каждый тест: sim_cards, global_logging, sim_imei_history.
    Подменяет движок в database.db_conectors, поэтому код программы (который
    вызывает get_session()) работает с этой же базой.
    """
    import database.db_conectors as dbc
    import database.mysql_models as models

    engine = create_engine("sqlite:///:memory:")
    for cls in (models.SimCard, models.GlobalLogging, models.SimImeiHistory):
        cls.__table__.create(engine, checkfirst=True)

    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    saved_engine, saved_factory = dbc._engine, dbc._SessionFactory
    dbc._engine, dbc._SessionFactory = engine, factory

    session = factory()
    try:
        yield session
    finally:
        session.close()
        dbc._engine, dbc._SessionFactory = saved_engine, saved_factory
        engine.dispose()


@pytest.fixture
def models():
    import database.mysql_models as m

    return m


# --------------------------------------------------------------------------- #
#  Логи
# --------------------------------------------------------------------------- #


def _drop_our_loggers() -> None:
    """
    Снимает обработчики с логгеров, созданных через logging_setup.
    Без этого логгер из прошлого теста продолжает писать в старую папку:
    reload модуля не трогает глобальный реестр logging.
    """
    import logging

    import logging_setup

    for name in list(logging.Logger.manager.loggerDict):
        logger = logging.getLogger(name)
        for handler in list(getattr(logger, "handlers", [])):
            if getattr(handler, logging_setup._MARKER, False):
                handler.close()
                logger.removeHandler(handler)


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Свежая папка логов и перезагруженный logging_setup под неё."""
    import importlib

    import logging_setup

    _drop_our_loggers()
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    importlib.reload(logging_setup)
    yield tmp_path
    _drop_our_loggers()
    importlib.reload(logging_setup)


# --------------------------------------------------------------------------- #
#  Мок-серверы операторов
# --------------------------------------------------------------------------- #


@pytest.fixture
def mts_mock():
    from tests.mocks import MockState, MtsHandler, start_mock

    state = MockState()
    server, url = start_mock(MtsHandler, state)
    try:
        yield state, url
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def beeline_mock():
    from tests.mocks import BeelineHandler, MockState, start_mock

    state = MockState()
    server, url = start_mock(BeelineHandler, state)
    try:
        yield state, url
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def mts_config(monkeypatch, mts_mock):
    """config и модуль коллектора настроены на мок МТС, без пауз лимитера."""
    import config
    import data_collector.mts_collector as mc

    state, url = mts_mock
    monkeypatch.setattr(config, "MTS_BASE_URL", url, raising=False)
    monkeypatch.setattr(config, "MTS_USERNAME", "user", raising=False)
    monkeypatch.setattr(config, "MTS_PASSWORD", "pass", raising=False)
    monkeypatch.setattr(config, "MTS_ACCOUNT_NUMBER", "252303159685", raising=False)
    monkeypatch.setattr(config, "MTS_ACCOUNT_NUMBER_SCOUT", "252303159686", raising=False)
    monkeypatch.setattr(mc, "RATE_PER_MIN", 100000)
    monkeypatch.setattr(mc, "PAGE_SIZE", 10)
    return state, url


@pytest.fixture
def beeline_config(monkeypatch, beeline_mock):
    """config и модуль коллектора настроены на мок Билайна, без пауз лимитера."""
    import config
    import data_collector.beeline_collector as bc

    state, url = beeline_mock
    monkeypatch.setattr(config, "BILINE_BASE_URL", url, raising=False)
    monkeypatch.setattr(config, "BILINE_DASHBORD", "2", raising=False)
    monkeypatch.setattr(config, "BILINE_CLIENT_ID", "3", raising=False)
    monkeypatch.setattr(config, "BILINE_CLIENT_SECRET", "secret", raising=False)
    monkeypatch.setattr(config, "BILINE_USERNAME", "user", raising=False)
    monkeypatch.setattr(config, "BILINE_PASSWORD", "pass", raising=False)
    monkeypatch.setattr(bc, "RATE_PER_MIN", 100000)
    monkeypatch.setattr(bc, "PAGE_SIZE", 200)
    return state, url


# --------------------------------------------------------------------------- #
#  Вспомогательное
# --------------------------------------------------------------------------- #


@pytest.fixture
def sim_data():
    """Заготовка словаря для crud.upsert_sim."""

    def make(**overrides):
        base = {
            "operator": 3,
            "owner": 1,
            "source": "beeline",
            "tel_num": "79800000001",
            "iccid": "89701011687090000001",
            "status": 1,
            "block_start": None,
        }
        base.update(overrides)
        return base

    return make
