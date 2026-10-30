"""
Поток Билайна.

Главное, что здесь проверяется, — та самая ошибка, из-за которой в базе
оказалось 49 симок из 1312: поле perpage и обход всех элементов страницы,
а не только items[0].
"""

from __future__ import annotations

import pytest

from api_client import ApiError


@pytest.fixture
def api(beeline_config):
    import config
    from data_collector.beeline_collector import BilineApi

    state, url = beeline_config
    client = BilineApi(
        config.BILINE_BASE_URL,
        config.BILINE_CLIENT_ID,
        config.BILINE_CLIENT_SECRET,
        config.BILINE_USERNAME,
        config.BILINE_PASSWORD,
        config.BILINE_DASHBORD,
    )
    yield client, state
    client.close()


# --------------------------------------------------------------------------- #
#  Разбор элемента списка
# --------------------------------------------------------------------------- #


ZHIVOY_ELEMENT = {
    "id": 4021634,
    "name": "",
    "status": "activated",
    "type": "regular",
    "contract_id": 100221902,
    "activated_at": "2022-08-04 05:27:12",
    "attached_at": "2022-08-04 05:27:12",
    "rate_plan_ends": "",
    "created_at": "2022-08-04 05:27:12",
    "rate_plan_id": 6255,
    "rate_plan_name": "M2M 30 MB%_SANTEHL",
    "blockings": ["blocking_platform"],
    "processings": [],
    "esia_state": True,
    "sim": {
        "id": 4021634,
        "imsi": "250990283419219",
        "iccid": "8970199170730066634",
        "apn": "m2m.beeline.ru",
        "imei": "867793036184895",
        "msisdn": "70899366645",
        "device_name": "SIMCOM SIM800",
        "device_type": 3,
        "last_ip": "10.219.211.53",
        "last_activity_dt": "2024-11-02 11:51:35",
        "stationarity_class": 0,
    },
    "cell_location": {"latitude": "56.146108", "longitude": "44.331631", "range": 225},
}


def test_razbor_elementa_spiska():
    """Структура взята с живого ответа: всё нужное лежит во вложенном sim."""
    from beeline_entry import _sim_to_dict

    data = _sim_to_dict(ZHIVOY_ELEMENT)

    assert data["iccid"] == "8970199170730066634"
    assert len(data["iccid"]) == 19, "ICCID Билайна уже 19-значный, обрезать не нужно"
    assert data["tel_num"] == "70899366645"
    assert data["operator"] == 3
    assert data["status"] == 1
    assert data["source"] == "beeline"
    assert data["operator_blockings"] == "blocking_platform"
    assert data["operator_rate_plan"] == "M2M 30 MB%_SANTEHL"


def test_imei_i_model_berutsya_iz_spiska():
    """Главная экономия: detect_device на каждую симку не нужен."""
    from beeline_entry import _sim_to_dict

    data = _sim_to_dict(ZHIVOY_ELEMENT)

    assert data["operator_imei"] == "867793036184895"
    assert data["operator_device_name"] == "SIMCOM SIM800"
    assert data["operator_last_activity"] == "2024-11-02 11:51:35"
    assert data["operator_apn"] == "m2m.beeline.ru"
    assert data["operator_last_ip"] == "10.219.211.53"
    assert data["sim_imsi"] == "250990283419219"


def test_koordinaty_iz_cell_location():
    from beeline_entry import _sim_to_dict

    data = _sim_to_dict(ZHIVOY_ELEMENT)

    assert data["operator_lat"] == "56.146108"
    assert data["operator_lon"] == "44.331631"
    assert data["operator_loc_range"] == 225


def test_nulevye_koordinaty_eto_neizvestno():
    """У части симок cell_location нулевой — это «не знаем», а не точка на экваторе."""
    from beeline_entry import _sim_to_dict

    item = dict(ZHIVOY_ELEMENT)
    item["cell_location"] = {"latitude": 0, "longitude": 0, "range": 0}

    data = _sim_to_dict(item)
    assert data["operator_lat"] is None
    assert data["operator_lon"] is None


def test_pustye_stroki_prevrashchayutsya_v_none():
    """Билайн отдаёт "" вместо null — в базу должно уйти NULL."""
    from beeline_entry import _sim_to_dict

    item = dict(ZHIVOY_ELEMENT)
    item["sim"] = dict(item["sim"], imei="", device_name="", last_activity_dt="", apn="")
    item["rate_plan_name"] = ""

    data = _sim_to_dict(item)
    assert data["operator_imei"] is None
    assert data["operator_device_name"] is None
    assert data["operator_last_activity"] is None
    assert data["operator_rate_plan"] is None


def test_element_bez_iccid_otbrasyvaetsya():
    from beeline_entry import _sim_to_dict

    assert _sim_to_dict({"id": 1, "status": "activated", "sim": {}}) is None
    assert _sim_to_dict({"id": 1, "status": "activated"}) is None


def test_pustye_blokirovki_dayut_none():
    from beeline_entry import _sim_to_dict

    item = dict(ZHIVOY_ELEMENT, blockings=[])
    assert _sim_to_dict(item)["operator_blockings"] is None


# --------------------------------------------------------------------------- #
#  Обход страниц
# --------------------------------------------------------------------------- #


def test_perpage_nazyvaetsya_bez_podchyorkivaniya(api):
    """
    В payload поле называется perpage. Прежний per_page API не понимал вовсе.
    Живой Билайн всё равно отдаёт по 30 записей, но поле передаём по документации.
    """
    client, state = api
    client.get_all_sims_pag(page=1, perpage=200)

    assert state.payloads[-1]["perpage"] == 200
    assert "per_page" not in state.payloads[-1]


def test_sortirovka_po_vozrastaniyu(api):
    """При desc симки, добавленные во время обхода, сдвигают страницы."""
    client, state = api
    client.get_all_sims_pag(page=1)
    assert state.payloads[-1]["order"] == {"id": "asc"}


def test_obhod_otdayot_vse_simki(api):
    """Было: одна симка со страницы. Стало: все, сколько бы страниц ни было."""
    client, state = api
    state.sims_total = 250

    sims = list(client.iter_all_sims())

    assert len(sims) == 250
    assert state.get("list_all_sim") == 9, "250 симок по 30 на странице — девять страниц"
    iccids = {s["sim"]["iccid"] for s in sims}
    assert len(iccids) == 250, "дубликатов быть не должно"


def test_obhod_odnoy_nepolnoy_stranicy(api):
    client, state = api
    state.sims_total = 7

    sims = list(client.iter_all_sims())
    assert len(sims) == 7
    assert state.get("list_all_sim") == 1


def test_obhod_pustogo_spiska(api):
    client, state = api
    state.sims_total = 0

    assert list(client.iter_all_sims()) == []


def test_token_odin_na_ves_obhod(api):
    """Раньше токен запрашивался на каждой странице."""
    client, state = api
    state.sims_total = 500

    list(client.iter_all_sims())

    assert state.get("token") == 1
    assert state.get("list_all_sim") == 17, "500 симок по 30 — семнадцать страниц"


# --------------------------------------------------------------------------- #
#  Методы по одной симке
# --------------------------------------------------------------------------- #


def test_detect_device(api):
    client, state = api
    device = client.detect_device(1000)

    assert device["imei"] == "990018947099424"
    assert device["device_name"] == "XIAOMI Redmi 10A"


def test_last_activity(api):
    client, state = api
    activity = client.last_activity(1000)

    assert activity["dt"] == "2026-10-29T12:00:00Z"
    assert activity["mobile_network"] == "25099"
    assert activity["other_party"] == "m2m.beeline.ru"


def test_get_balance(api):
    client, state = api
    assert client.get_balance(1000) == 123.45


def test_update_location(api):
    client, state = api
    location = client.update_location(1000)

    assert location["latitude"] == "56.3269"
    assert location["precision"] == "385"


def test_esim_404_daet_apierror(api):
    client, state = api
    with pytest.raises(ApiError):
        client.esim_info = client._call("GET", client._dash("/sim_cards/1000/esim"))


def test_401_perepoluchaet_token(api):
    """Если токен протух раньше срока, запрос повторяется с новым."""
    client, state = api
    state.mode = "needs_auth"

    data = client.get_all_sims_pag(page=1)

    assert data["status"] == "ok"
    assert state.get("token") == 2, "после 401 токен должен быть запрошен заново"


# --------------------------------------------------------------------------- #
#  Полный прогон
# --------------------------------------------------------------------------- #


def test_polnyy_progon_pishet_vse_simki(db, models, beeline_config, monkeypatch):
    import beeline_entry

    state, url = beeline_config
    state.sims_total = 120
    monkeypatch.setattr(beeline_entry, "DETECT_DEVICE", False)

    beeline_entry.beeline_merge_data()

    assert db.query(models.SimCard).count() == 120
    assert state.get("token") == 1
    assert state.get("list_all_sim") == 4, "120 симок по 30 — четыре страницы"


def test_progon_sohranyaet_vse_polya_operatora(db, models, beeline_config, monkeypatch):
    import beeline_entry

    state, url = beeline_config
    state.sims_total = 10
    monkeypatch.setattr(beeline_entry, "DETECT_DEVICE", False)

    beeline_entry.beeline_merge_data()

    sims = db.query(models.SimCard).all()
    assert len(sims) == 10

    # у всех есть IMSI, он приходит даже для списанных
    assert all(s.sim_imsi for s in sims)

    # в моке каждая пятая симка списана и без устройства
    s_imei = [s for s in sims if s.operator_imei]
    assert len(s_imei) == 8
    assert all(s.operator_device_name == "SIMCOM SIM800" for s in s_imei)
    assert all(s.operator_apn == "m2m.beeline.ru" for s in s_imei)
    assert all(s.operator_last_ip == "10.219.211.53" for s in s_imei)
    assert all(s.operator_lat is not None for s in s_imei)
    assert all(s.operator_rate_plan == "M2M 30 MB%_SANTEHL" for s in s_imei)


def test_imei_berutsya_bez_edinogo_detect_device(db, models, beeline_config, monkeypatch):
    """
    Главная экономия после разбора живого API: список уже несёт IMEI,
    поэтому отдельных запросов на симку быть не должно вовсе.
    """
    import beeline_entry

    state, url = beeline_config
    state.sims_total = 30
    monkeypatch.setattr(beeline_entry, "DETECT_DEVICE", False)

    beeline_entry.beeline_merge_data()

    assert state.get("detect_device") == 0
    assert db.query(models.SimCard).filter(models.SimCard.operator_imei.isnot(None)).count() == 24


def test_detect_device_ne_dyorgaetsya_kogda_model_uzhe_est(db, models, beeline_config, monkeypatch):
    """Даже при включённой настройке уточнять нечего, если модель пришла в списке."""
    import beeline_entry

    state, url = beeline_config
    state.sims_total = 20
    monkeypatch.setattr(beeline_entry, "DETECT_DEVICE", True)
    monkeypatch.setattr(beeline_entry, "DETECT_LIMIT", 5)

    beeline_entry.beeline_merge_data()

    assert state.get("detect_device") == 0


def test_nado_utochnit_model():
    """Уточняем модель только когда IMEI есть, а названия устройства нет."""
    from datetime import datetime, timedelta

    from beeline_entry import _nado_utochnit_model

    class Row:
        def __init__(self, imei, name, sync):
            self.operator_imei = imei
            self.operator_device_name = name
            self.operator_sync_at = sync

        
    svezhiy = datetime.now()
    staryy = datetime.now() - timedelta(days=30)

    assert _nado_utochnit_model(None) is False
    assert _nado_utochnit_model(Row(None, None, svezhiy)) is False, "нет IMEI — уточнять нечего"
    assert _nado_utochnit_model(Row("867793036184895", None, svezhiy)) is True
    assert _nado_utochnit_model(Row("867793036184895", "SIMCOM SIM800", svezhiy)) is False
    assert _nado_utochnit_model(Row("867793036184895", "SIMCOM SIM800", staryy)) is True


def test_povtornyy_progon_ne_plodit_dubley(db, models, beeline_config, monkeypatch):
    import beeline_entry

    state, url = beeline_config
    state.sims_total = 45
    monkeypatch.setattr(beeline_entry, "DETECT_DEVICE", False)

    beeline_entry.beeline_merge_data()
    beeline_entry.beeline_merge_data()

    assert db.query(models.SimCard).count() == 45


def test_progon_s_nedostupnym_api_ne_vesnet(db, models, beeline_config, monkeypatch):
    import beeline_entry

    state, url = beeline_config
    state.mode = "token_fail"

    with pytest.raises(Exception):
        beeline_entry.beeline_merge_data()

    assert db.query(models.SimCard).count() == 0
