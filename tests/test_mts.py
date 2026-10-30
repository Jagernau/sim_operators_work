"""
Поток МТС.

Главное здесь — проверка, что обход не уходит в вечный цикл при устойчивой
ошибке и что при неполном обходе списание не выполняется: иначе живые симки
пометятся исчезнувшими у оператора.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import clear_mts_entry
from api_client import ApiError


# --------------------------------------------------------------------------- #
#  Разбор блокировок
# --------------------------------------------------------------------------- #


def blok(code=None, name=None, start="2026-09-15T12:43:44+03:00", end="0001-01-01T00:00:00+03:00"):
    """Блокировка в том виде, в каком её отдаёт живой МТС."""
    block = {"status": "ACTIVE", "validFor": {}}
    if code:
        block["externalID"] = code
    if name:
        block["name"] = name
    if start:
        block["validFor"]["startDateTime"] = start
    if end:
        block["validFor"]["endDateTime"] = end
    return block


def test_net_dannyh_status_neizvesten():
    """None означает «не смогли узнать» — это статус 4, а не «активна»."""
    assert clear_mts_entry._blocks_to_status(None) == (4, None, None, None)


def test_pustoy_spisok_znachit_aktivna():
    assert clear_mts_entry._blocks_to_status([]) == (1, None, None, None)


def test_dobrovolnaya_blokirovka_po_kodu():
    status, start, end, code = clear_mts_entry._blocks_to_status(
        [blok("BL0005", "Добровольная блокировка")]
    )
    assert status == 2
    assert code == "BL0005"
    assert start == "2026-09-15 12:43:44", "время блокировки должно сохраняться целиком"
    assert end is None, "0001-01-01 — заглушка «бессрочно», её храним как NULL"


def test_pervonachalnaya_blokirovka_po_kodu():
    status, start, end, code = clear_mts_entry._blocks_to_status(
        [blok("BL0008", "Первоначальная блокировка", start="2026-10-07T10:34:01+03:00")]
    )
    assert status == 3
    assert code == "BL0008"
    assert start == "2026-10-07 10:34:01"


def test_kod_vazhnee_nazvaniya():
    """Если МТС переименует блокировку, код всё равно даст правильный статус."""
    status, _, _, code = clear_mts_entry._blocks_to_status(
        [blok("BL0005", "Блокировка по инициативе абонента")]
    )
    assert status == 2
    assert code == "BL0005"


def test_neizvestnyy_kod_otkatyvaetsya_na_nazvanie():
    """Новый код, но знакомое название — статус всё ещё распознаётся."""
    status, _, _, code = clear_mts_entry._blocks_to_status(
        [blok("BL9999", "Добровольная блокировка")]
    )
    assert status == 2
    assert code == "BL9999"


def test_sovsem_neizvestnaya_blokirovka():
    """Ни код, ни название не знакомы — статус «неизвестен», но код сохраняем."""
    status, start, end, code = clear_mts_entry._blocks_to_status(
        [blok("BL7777", "Сезонная блокировка")]
    )
    assert status == 4
    assert code == "BL7777"


def test_blokirovka_bez_daty_ne_padaet():
    status, start, end, code = clear_mts_entry._blocks_to_status([blok("BL0005", start=None)])
    assert status == 2
    assert start is None


def test_realnyy_konec_blokirovki_sohranyaetsya():
    _, _, end, _ = clear_mts_entry._blocks_to_status(
        [blok("BL0005", end="2026-12-31T23:59:59+03:00")]
    )
    assert end == "2026-12-31 23:59:59"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-05-12T12:43:44+03:00", "2026-05-12 12:43:44"),
        ("2026-05-12T12:43:44Z", "2026-05-12 12:43:44"),
        ("0001-01-01T00:00:00+03:00", None),
        ("", None),
        (None, None),
    ],
)
def test_razbor_daty_mts(raw, expected):
    assert clear_mts_entry._mts_dt(raw) == expected


# --------------------------------------------------------------------------- #
#  Коллектор
# --------------------------------------------------------------------------- #


@pytest.fixture
def api(mts_config):
    import config
    from data_collector.mts_collector import MtsApi

    state, url = mts_config
    client = MtsApi(config.MTS_BASE_URL, config.MTS_USERNAME, config.MTS_PASSWORD, "252303159685")
    yield client, state
    client.close()


def test_token_odin_na_mnogo_zaprosov(api):
    """Прежний код брал токен на каждой странице."""
    client, state = api
    state.sims_total = 50

    for page in range(5):
        client.get_structure_abonents(page, pageSize=10)

    assert state.get("token") == 1
    assert state.get("structure") == 5


def test_pagesize_peredayotsya(api):
    client, state = api
    client.get_structure_abonents(1, pageSize=100)
    assert state.perpage_seen[-1] == 100


def test_obhod_nachinaetsya_s_pervoy_stranicy(db, models, mts_config):
    """
    pageNum=0 и pageNum=1 у МТС отдают одну и ту же страницу. Обход должен
    стартовать с единицы, иначе первая сотня симок обрабатывается дважды.
    """
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 25

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    iccids, polnyy = clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    assert polnyy is True
    assert len(iccids) == len(set(iccids)), "дубликатов быть не должно"
    assert len(iccids) == 25
    assert 0 not in [p for p in state.perpage_seen], "pageSize не должен быть нулевым"


def test_imsi_popadaet_v_bazu(db, models, mts_config):
    """IMSI лежит в productCharacteristic рядом с SIM и тоже забирается."""
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 5

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    sims = db.query(models.SimCard).all()
    assert len(sims) == 5
    assert all(s.sim_imsi and len(s.sim_imsi) == 15 for s in sims)


def test_poisk_po_iccid(api):
    client, state = api
    client.get_by_iccid("8970101168709000000")
    assert state.get("structure") == 1


def test_oshibka_servera_daet_apierror(api):
    client, state = api
    state.mode = "500"

    with pytest.raises(ApiError):
        client.get_structure_abonents(0)


# --------------------------------------------------------------------------- #
#  Обход страниц
# --------------------------------------------------------------------------- #


def test_obhod_vseh_stranic(db, models, mts_config):
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 30

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    iccids, polnyy = clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    assert polnyy is True
    assert len(iccids) == 30
    assert db.query(models.SimCard).count() == 30


def test_ustoychivaya_oshibka_ne_zaciklivaetsya(db, models, mts_config):
    """
    Прежний код при ошибке делал continue, не увеличив номер страницы,
    и крутился вечно. Теперь — три попытки и выход.
    """
    import logging_setup
    from database import crud

    state, url = mts_config
    state.mode = "404"                     # 404 не ретраится, тест быстрый

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    iccids, polnyy = clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    assert polnyy is False
    assert iccids == []
    assert state.get("structure") == clear_mts_entry.MAX_FAILS_PODRYAD


def test_oshibka_v_seredine_preryvaet_obhod(db, models, mts_config):
    """Если страница 2 из 5 не прочиталась, обход считается неполным."""
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 50

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    known = crud.load_known_iccids(db)

    original = clear_mts_entry._process_page
    calls = {"n": 0}

    def break_after_first(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            state.mode = "404"
        return original(*args, **kwargs)

    clear_mts_entry._process_page = break_after_first
    try:
        iccids, polnyy = clear_mts_entry.get_mts_pages("252303159685", db, known, stat)
    finally:
        clear_mts_entry._process_page = original

    assert polnyy is False
    assert 0 < len(iccids) < 50


def test_blokirovki_pishutsya_v_bazu(db, models, mts_config):
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 10

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    # в моке BL0005 у номеров на 2, 5, 8 и BL0008 у номеров на 3, 6
    dobrovolnye = db.query(models.SimCard).filter(models.SimCard.status == 2).all()
    pervichnye = db.query(models.SimCard).filter(models.SimCard.status == 3).all()

    assert len(dobrovolnye) == 3
    assert len(pervichnye) == 2
    assert all(s.operator_block_code == "BL0005" for s in dobrovolnye)
    assert all(s.operator_block_code == "BL0008" for s in pervichnye)
    assert all(
        s.block_start == datetime(2026, 9, 15, 12, 43, 44) for s in dobrovolnye
    ), "время блокировки должно сохраняться, а не обнуляться до полуночи"
    assert all(s.block_end is None for s in dobrovolnye)


# --------------------------------------------------------------------------- #
#  Полный прогон и списание
# --------------------------------------------------------------------------- #


def test_polnyy_progon_spisyvaet_ischeznuvshie(db, models, mts_config):
    state, url = mts_config
    state.sims_total = 5

    staraya = models.SimCard(
        sim_cell_operator=1, sim_owner=1, status=1,
        sim_iccid="99999999999999999999", sim_tel_number="79109999999",
    )
    db.add(staraya)
    db.commit()

    clear_mts_entry.mts_merge_data()

    db.expire_all()
    assert db.query(models.SimCard).filter(
        models.SimCard.sim_iccid == "99999999999999999999"
    ).first().status == 0


def test_nepolnyy_obhod_ne_spisyvaet(db, models, mts_config):
    """Самое опасное место: неполные данные не должны обнулять базу."""
    state, url = mts_config
    state.mode = "404"

    for i in range(5):
        db.add(models.SimCard(
            sim_cell_operator=1, sim_owner=1, status=1,
            sim_iccid=f"8970101168709000000{i}", sim_tel_number=f"791000000{i:02d}",
        ))
    db.commit()

    clear_mts_entry.mts_merge_data()

    db.expire_all()
    spisano = db.query(models.SimCard).filter(models.SimCard.status == 0).count()
    assert spisano == 0, "при неполном обходе списание выполняться не должно"


def test_progon_oboih_schetov(db, models, mts_config):
    state, url = mts_config
    state.sims_total = 4

    clear_mts_entry.mts_merge_data()

    # два лицевых счёта, мок отдаёт один и тот же набор — записей должно быть 4
    assert db.query(models.SimCard).count() == 4
    assert state.get("structure") >= 2


def test_iccid_obrezaetsya_do_19_znakov(db, models, mts_config):
    """
    МТС отдаёт ICCID двадцатизначным, последний символ — контрольная цифра.
    В базе ICCID хранится без неё, поэтому обрезка в _process_page сделана
    намеренно. Тест стоит здесь, чтобы её не приняли за опечатку.

    У Билайна ICCID приходит уже 19-значным и не обрезается — см. test_beeline.
    """
    import logging_setup
    from database import crud

    state, url = mts_config
    state.sims_total = 3

    stat = logging_setup.Stat("тест", logging_setup.get_logger("test_mts"))
    iccids, _ = clear_mts_entry.get_mts_pages("252303159685", db, crud.load_known_iccids(db), stat)

    assert all(len(i) == 19 for i in iccids), f"ожидали 19 знаков, получили {[len(i) for i in iccids]}"
    for sim in db.query(models.SimCard).all():
        assert len(sim.sim_iccid) == 19
