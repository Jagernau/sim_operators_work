import pytest

import clear_mts_entry as mts
from api_client import ApiError
from database import crud
from logging_setup import Stat, get_logger


@pytest.mark.parametrize("reply, expected", [
    ([{"externalID": "PE22816", "status": "PROMO"}], 1),
    ([{"name": "Телематика. Пакет 100 МБ"}], 1),
    ([{"name": "Телематика. Пакет 60 МБ 112022"}], 0),
    ([], 0),
])
def test_package_list(reply, expected):
    assert mts._telematics_flag(reply) == expected


def test_package_update(db, models, mts_config, monkeypatch):
    from data_collector.mts_collector import MtsApi

    state, _ = mts_config
    state.sims_total = 1
    known = crud.load_known_iccids(db)
    stat = Stat("МТС", get_logger("test_mts"))
    for reply, expected in [
        ({"error": "unavailable"}, None),
        ([{"name": "Телематика. Пакет 100 МБ"}], 1),
        (ApiError("failed"), 1),
        ([{}], 1),
        ([], 0),
    ]:
        def get_services(self, number, *, include_prices):
            assert include_prices is False
            if isinstance(reply, Exception):
                raise reply
            return reply

        monkeypatch.setattr(MtsApi, "get_detail_service_from_tel_number", get_services)
        mts.get_mts_pages("123", db, known, stat)
        db.expire_all()
        assert db.query(models.SimCard).one().mts_telematics_100mb == expected


def test_service_request_preserves_price_option(monkeypatch):
    from data_collector.mts_collector import MtsApi
    from urllib.parse import parse_qs, urlsplit

    client = MtsApi("http://localhost", "", "", "123")
    monkeypatch.setattr(client, "_get", lambda url, **kw: parse_qs(urlsplit(url).query))
    try:
        plain = client.get_detail_service_from_tel_number("70000000000", include_prices=False)
        priced = client.get_detail_service_from_tel_number("70000000000")
    finally:
        client.close()

    assert plain["marketSegment.characteristic.value"] == ["70000000000"]
    assert plain["productOffering.productSpecification.productSpecificationType.name"] == ["service"]
    assert plain["productOffering.actionAllowed"] == ["none"]
    assert plain["applyTimeZone"] == ["true"]
    assert "fields" not in plain
    assert priced["fields"] == ["CalculatePrices"]
