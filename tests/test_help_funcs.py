"""Преобразование статусов операторов в наши коды."""

from __future__ import annotations

import pytest

import help_funcs


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Добровольная блокировка", 2),
        ("Первоначальная блокировка", 3),
    ],
)
def test_mts_statusy(text, expected):
    assert help_funcs.mts_status_convert(text) == expected


def test_mts_neizvestnyy_status_daet_none():
    """
    Зафиксировано как есть: новые типы блокировок МТС вернут None.
    В clear_mts_entry это превращается в статус 4 («неизвестен»),
    так что симка не теряется и не помечается активной по ошибке.
    """
    assert help_funcs.mts_status_convert("Сезонная блокировка") is None
    assert help_funcs.mts_status_convert("") is None
    assert help_funcs.mts_status_convert(None) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("purged", 0),
        ("activated", 1),
        ("deactivated", 2),
        ("activation_ready", 3),
    ],
)
def test_beeline_statusy(text, expected):
    assert help_funcs.beeline_status_convert(text) == expected


def test_beeline_neizvestnyy_status_daet_none():
    """
    Если Билайн заведёт новый статус, сюда прилетит None и в базу запишется
    NULL. Это видно по счётчику и в v_sim_imei_check — заметить можно,
    но лучше расширить список, когда такой статус впервые встретится.
    """
    assert help_funcs.beeline_status_convert("suspended") is None
    assert help_funcs.beeline_status_convert("blocked") is None
    assert help_funcs.beeline_status_convert("None") is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Заблокирован", 0),
        ("Активен", 1),
        ("Приостановлен", 2),
        ("Не активирован", 3),
        ("что-то новое", None),
    ],
)
def test_tele2_statusy(text, expected):
    assert help_funcs.tele2_status_convert(text) == expected


def test_stranicy_paginacii():
    data = {
        "a": {"class": "", "text": "1"},
        "b": {"class": "current", "text": "2"},
        "c": {"class": "", "text": "3"},
        "d": {"class": "", "text": "Вперёд"},
    }
    assert help_funcs.get_current_page(data) == 2
    assert help_funcs.get_max_page(data) == 3


def test_max_page_bez_chisel():
    data = {"a": {"class": "", "text": "Вперёд"}}
    assert help_funcs.get_max_page(data) == 0
