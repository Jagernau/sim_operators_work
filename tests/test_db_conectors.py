"""Подключение к базе: один движок на процесс, сессии, сброс пула после fork."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.db_conectors as dbc


def test_dvizhok_sozdayotsya_odin_raz(monkeypatch):
    """
    Раньше MysqlDatabase() в каждой функции crud поднимал новый create_engine,
    то есть новый пул соединений, и они копились до конца прогона.
    """
    created = []

    def fake_create_engine(*args, **kwargs):
        created.append(1)
        return create_engine("sqlite:///:memory:")

    monkeypatch.setattr(dbc, "create_engine", fake_create_engine)
    monkeypatch.setattr(dbc, "_engine", None)
    monkeypatch.setattr(dbc, "_SessionFactory", None)

    for _ in range(50):
        dbc.get_engine()

    assert len(created) == 1


def test_get_session_otdayot_rabochuyu_sessiyu(db, models):
    session = dbc.get_session()
    try:
        assert session.query(models.SimCard).count() == 0
    finally:
        session.close()


def test_session_scope_kommitit(db, models):
    with dbc.session_scope() as session:
        session.add(
            models.SimCard(
                sim_cell_operator=1, sim_owner=1, status=1,
                sim_iccid="89701011687090000777", sim_tel_number="79100000777",
            )
        )

    assert db.query(models.SimCard).filter(
        models.SimCard.sim_iccid == "89701011687090000777"
    ).count() == 1


def test_session_scope_otkatyvaet_pri_oshibke(db, models):
    with pytest.raises(RuntimeError):
        with dbc.session_scope() as session:
            session.add(
                models.SimCard(
                    sim_cell_operator=1, sim_owner=1, status=1,
                    sim_iccid="89701011687090000888", sim_tel_number="79100000888",
                )
            )
            raise RuntimeError("что-то пошло не так")

    assert db.query(models.SimCard).filter(
        models.SimCard.sim_iccid == "89701011687090000888"
    ).count() == 0


def test_reset_pool_ne_padaet_bez_dvizhka(monkeypatch):
    monkeypatch.setattr(dbc, "_engine", None)
    dbc.reset_pool()      # не должно бросить


def test_reset_pool_zakryvaet_soedineniya(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    disposed = []
    monkeypatch.setattr(engine, "dispose", lambda: disposed.append(1))
    monkeypatch.setattr(dbc, "_engine", engine)

    dbc.reset_pool()

    assert disposed == [1]


def test_staryy_klass_rabotaet_cherez_obshchiy_dvizhok(db, models):
    """MysqlDatabase оставлен для совместимости и новый движок не поднимает."""
    legacy = dbc.MysqlDatabase()
    try:
        assert legacy.session.query(models.SimCard).count() == 0
        assert legacy.engine is dbc.get_engine()
    finally:
        legacy.session.close()
