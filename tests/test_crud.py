"""Запись в базу: upsert, история IMEI, журнал изменений, списание."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from database import crud


@pytest.fixture
def stat():
    import logging_setup

    return logging_setup.Stat("тест", logging_setup.get_logger("test_crud"))


def add_sim(session, models, **fields):
    defaults = dict(
        sim_cell_operator=1,
        sim_owner=1,
        sim_tel_number="79100000000",
        sim_iccid="89701011687090000000",
        status=1,
    )
    defaults.update(fields)
    sim = models.SimCard(**defaults)
    session.add(sim)
    session.commit()
    return sim


# --------------------------------------------------------------------------- #
#  Чтение
# --------------------------------------------------------------------------- #


def test_known_iccids_odin_zapros(db, models):
    """Раньше это был полный SELECT дважды на каждую симку."""
    for i in range(5):
        add_sim(db, models, sim_iccid=f"8970101168709000000{i}")

    known = crud.load_known_iccids(db)
    assert len(known) == 5
    assert "89701011687090000003" in known
    assert isinstance(known["89701011687090000003"], int)


def test_known_iccids_na_pustoy_baze(db, models):
    assert crud.load_known_iccids(db) == {}


# --------------------------------------------------------------------------- #
#  Вставка
# --------------------------------------------------------------------------- #


def test_novaya_simka_zapisyvaetsya(db, models, sim_data, stat):
    known = {}
    sim_id = crud.upsert_sim(db, known, sim_data(), stat)

    assert sim_id is not None
    sim = db.query(models.SimCard).filter(models.SimCard.sim_id == sim_id).first()
    assert sim.sim_iccid == "89701011687090000001"
    assert sim.sim_tel_number == "79800000001"
    assert sim.status == 1
    assert stat.get("добавлено") == 1


def test_vstavka_popadaet_v_global_logging(db, models, sim_data, stat):
    sim_id = crud.upsert_sim(db, {}, sim_data(), stat)

    rows = db.query(models.GlobalLogging).filter(models.GlobalLogging.edit_id == sim_id).all()
    assert len(rows) == 1
    assert rows[0].action == "add"
    assert rows[0].field == "iccid"
    assert rows[0].section_type == "sim_card"


def test_vstavka_popolnyaet_known(db, models, sim_data, stat):
    known = {}
    crud.upsert_sim(db, known, sim_data(), stat)
    assert "89701011687090000001" in known


def test_bez_iccid_ne_pishetsya(db, models, sim_data, stat):
    assert crud.upsert_sim(db, {}, sim_data(iccid=None), stat) is None
    assert crud.upsert_sim(db, {}, sim_data(iccid=""), stat) is None
    assert stat.get("пропущено без ICCID") == 2
    assert db.query(models.SimCard).count() == 0


def test_polya_operatora_pri_vstavke(db, models, sim_data, stat):
    sim_id = crud.upsert_sim(
        db,
        {},
        sim_data(
            operator_imei="990018947099424",
            operator_device_name="XIAOMI Redmi 10A",
            operator_last_activity="2026-10-29T12:00:00Z",
            operator_apn="m2m.beeline.ru",
            operator_mcc_mnc="25099",
            operator_blockings="blocking_platform",
            operator_rate_plan="M2M 3Gb_UniSim",
        ),
        stat,
    )

    sim = db.query(models.SimCard).filter(models.SimCard.sim_id == sim_id).first()
    assert sim.operator_imei == "990018947099424"
    assert sim.operator_device_name == "XIAOMI Redmi 10A"
    assert sim.operator_last_activity == datetime(2026, 10, 29, 12, 0, 0)
    assert sim.operator_apn == "m2m.beeline.ru"
    assert sim.operator_mcc_mnc == "25099"
    assert sim.operator_sync_at is not None


# --------------------------------------------------------------------------- #
#  Обновление
# --------------------------------------------------------------------------- #


def test_povtor_bez_izmeneniy_nichego_ne_pishet(db, models, sim_data, stat):
    known = {}
    crud.upsert_sim(db, known, sim_data(), stat)
    logs_posle_vstavki = db.query(models.GlobalLogging).count()

    for _ in range(5):
        crud.upsert_sim(db, known, sim_data(), stat)

    assert db.query(models.GlobalLogging).count() == logs_posle_vstavki
    assert stat.get("без изменений") == 5
    assert stat.get("обновлено") == 0


def test_smena_telefona(db, models, sim_data, stat):
    known = {}
    sim_id = crud.upsert_sim(db, known, sim_data(), stat)
    crud.upsert_sim(db, known, sim_data(tel_num="79800009999"), stat)

    sim = db.query(models.SimCard).filter(models.SimCard.sim_id == sim_id).first()
    assert sim.sim_tel_number == "79800009999"

    row = db.query(models.GlobalLogging).filter(models.GlobalLogging.field == "sim_tel_number").first()
    assert row.old_value == "79800000001"
    assert row.new_value == "79800009999"
    assert row.action == "update"


def test_smena_statusa(db, models, sim_data, stat):
    known = {}
    sim_id = crud.upsert_sim(db, known, sim_data(), stat)
    crud.upsert_sim(db, known, sim_data(status=2, block_start="2026-10-30 00:00:00"), stat)

    sim = db.query(models.SimCard).filter(models.SimCard.sim_id == sim_id).first()
    assert sim.status == 2
    assert sim.block_start == datetime(2026, 10, 30, 0, 0, 0)

    fields = {r.field for r in db.query(models.GlobalLogging).all()}
    assert "status" in fields
    assert "block_start" in fields


def test_snyatie_blokirovki(db, models, sim_data, stat):
    known = {}
    sim_id = crud.upsert_sim(db, known, sim_data(status=2, block_start="2026-09-01 00:00:00"), stat)
    crud.upsert_sim(db, known, sim_data(status=1, block_start=None), stat)

    sim = db.query(models.SimCard).filter(models.SimCard.sim_id == sim_id).first()
    assert sim.status == 1
    assert sim.block_start is None


def test_odin_commit_na_simku(db, models, sim_data, stat):
    """
    Раньше update_one_sim делал до пяти commit и столько же лишних SELECT.
    Теперь на изменение двух полей — одна порция записей.
    """
    known = {}
    crud.upsert_sim(db, known, sim_data(), stat)
    db.query(models.GlobalLogging).delete()
    db.commit()

    crud.upsert_sim(db, known, sim_data(tel_num="79800007777", status=3), stat)
    assert db.query(models.GlobalLogging).count() == 2
    assert stat.get("обновлено") == 1


# --------------------------------------------------------------------------- #
#  История IMEI
# --------------------------------------------------------------------------- #


def test_pervyy_imei_ne_sozdayot_istoriyu(db, models, sim_data, stat):
    """Первое получение IMEI — не перестановка терминала, а просто новые данные."""
    known = {}
    crud.upsert_sim(db, known, sim_data(), stat)
    crud.upsert_sim(db, known, sim_data(operator_imei="990018947099424"), stat)

    assert db.query(models.SimImeiHistory).count() == 0
    sim = db.query(models.SimCard).first()
    assert sim.operator_imei == "990018947099424"


def test_smena_imei_pishetsya_v_istoriyu(db, models, sim_data, stat):
    """Вот это и есть контроль: симку переставили в другой терминал."""
    known = {}
    sim_id = crud.upsert_sim(db, known, sim_data(operator_imei="990018947099424"), stat)
    crud.upsert_sim(
        db,
        known,
        sim_data(operator_imei="860000000000777", operator_device_name="Teltonika FMB920"),
        stat,
    )

    rows = db.query(models.SimImeiHistory).all()
    assert len(rows) == 1
    assert rows[0].sim_id == sim_id
    assert rows[0].old_imei == "990018947099424"
    assert rows[0].new_imei == "860000000000777"
    assert rows[0].device_name == "Teltonika FMB920"
    assert rows[0].source == "beeline"
    assert stat.get("смен IMEI у оператора") == 1


def test_tot_zhe_imei_istoriyu_ne_plodit(db, models, sim_data, stat):
    known = {}
    crud.upsert_sim(db, known, sim_data(operator_imei="990018947099424"), stat)
    for _ in range(3):
        crud.upsert_sim(db, known, sim_data(operator_imei="990018947099424"), stat)

    assert db.query(models.SimImeiHistory).count() == 0


# --------------------------------------------------------------------------- #
#  Разбор дат
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-10-29T12:00:00Z", datetime(2026, 10, 29, 12, 0, 0)),
        ("2026-10-30T07:09:22.889Z", datetime(2026, 10, 30, 7, 9, 22)),
        ("2026-10-30 00:00:00", datetime(2026, 10, 30, 0, 0, 0)),
        ("2026-10-30", datetime(2026, 10, 30, 0, 0, 0)),
        (None, None),
        ("", None),
        ("совсем не дата", None),
    ],
)
def test_razbor_dat(raw, expected):
    assert crud._parse_dt(raw) == expected


def test_datetime_prohodit_naskvoz():
    now = datetime(2026, 1, 1, 10, 30)
    assert crud._parse_dt(now) is now


# --------------------------------------------------------------------------- #
#  Списание
# --------------------------------------------------------------------------- #


def test_spisanie_ischeznuvshih(db, models, stat):
    for i in range(3):
        add_sim(db, models, sim_iccid=f"8970101168709000000{i}", status=1)

    crud.write_off_mts_sim(["89701011687090000000", "89701011687090000001"], stat)

    statuses = {s.sim_iccid: s.status for s in db.query(models.SimCard).all()}
    assert statuses["89701011687090000000"] == 1
    assert statuses["89701011687090000001"] == 1
    assert statuses["89701011687090000002"] == 0, "симка, которой нет у оператора, должна списаться"


def test_spisanie_pishet_v_global_logging(db, models, stat):
    add_sim(db, models, sim_iccid="89701011687090000009", status=1)
    crud.write_off_mts_sim(["другой-iccid"], stat)

    rows = db.query(models.GlobalLogging).filter(models.GlobalLogging.field == "status").all()
    assert len(rows) == 1
    assert rows[0].new_value == "0"


def test_pustoy_spisok_nichego_ne_spisyvaet(db, models, stat):
    """Защита: если обход сорвался, живые симки не должны уйти в списанные."""
    add_sim(db, models, sim_iccid="89701011687090000009", status=1)

    crud.write_off_mts_sim([], stat)

    assert db.query(models.SimCard).first().status == 1
    assert db.query(models.GlobalLogging).count() == 0


def test_uzhe_spisannye_ne_trogayutsya(db, models, stat):
    add_sim(db, models, sim_iccid="89701011687090000009", status=0)
    crud.write_off_mts_sim(["другой"], stat)

    assert db.query(models.GlobalLogging).count() == 0


def test_spisanie_snimaet_block_start(db, models, stat):
    add_sim(
        db,
        models,
        sim_iccid="89701011687090000009",
        status=2,
        block_start=datetime(2026, 9, 1),
    )
    crud.write_off_mts_sim(["другой"], stat)

    sim = db.query(models.SimCard).first()
    assert sim.status == 0
    assert sim.block_start is None


def test_spisanie_tolko_dlya_mts(db, models, stat):
    """Оператор 3 — Билайн, его списание МТС трогать не должно."""
    add_sim(db, models, sim_iccid="89701011687090000009", sim_cell_operator=3, status=1)
    crud.write_off_mts_sim(["другой"], stat)

    assert db.query(models.SimCard).first().status == 1
