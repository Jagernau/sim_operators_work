"""Логирование: маскировка секретов, схлопывание повторов, ротация, счётчики."""

from __future__ import annotations

import logging

import pytest


def read_log(log_dir, name="t"):
    path = log_dir / f"{name}.log"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# --------------------------------------------------------------------------- #
#  Маскировка
# --------------------------------------------------------------------------- #


def test_jwt_ne_popadaet_v_log(log_dir):
    """Токен Билайна — больше тысячи символов, и он не должен лежать в файле."""
    import logging_setup

    log = logging_setup.get_logger("t")
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9." + "A" * 400
    log.info(f"Получен токен доступа от Билайн: {token}")

    text = read_log(log_dir)
    assert "A" * 400 not in text
    assert "скрыто" in text
    assert len(text) < 200


@pytest.mark.parametrize(
    "line, secret",
    [
        ("access_token=abcdef1234567890", "abcdef1234567890"),
        ('"refresh_token": "def502004ff8bc7ffb23b7"', "def502004ff8bc7ffb23b7"),
        ("client_secret=ePovviEW6A13mqxxLbA3Q8YQtDiG9hdC", "ePovviEW6A13mqxxLbA3Q8YQtDiG9hdC"),
        ("password: qwerty123456789", "qwerty123456789"),
        ("Authorization: Bearer zzzzzzzzzzzzzzzzzzzz", "zzzzzzzzzzzzzzzzzzzz"),
    ],
)
def test_sekrety_maskiruyutsya(log_dir, line, secret):
    import logging_setup

    log = logging_setup.get_logger("t")
    log.info(line)
    assert secret not in read_log(log_dir)


def test_obychnyy_tekst_ne_portitsya(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    log.info("SIM 89701011687090000001 обновлена, IMEI 990018947099424")

    text = read_log(log_dir)
    assert "89701011687090000001" in text
    assert "990018947099424" in text


def test_argumenty_formatiruyutsya_i_maskiruyutsya(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    log.info("токен %s получен", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9zzzz")

    text = read_log(log_dir)
    assert "zzzz" not in text
    assert "получен" in text


# --------------------------------------------------------------------------- #
#  Схлопывание повторов
# --------------------------------------------------------------------------- #


def test_povtory_shlopyvayutsya(log_dir):
    """Зациклившаяся ошибка не должна наливать гигабайты."""
    import logging_setup

    log = logging_setup.get_logger("t")
    for _ in range(500):
        log.error("Не удаётся получить данные с МТС в итерации цикла: timeout")

    lines = [ln for ln in read_log(log_dir).splitlines() if ln.strip()]
    assert 3 <= len(lines) <= 10, f"ожидали единицы строк, получили {len(lines)}"
    assert any("повтор" in ln for ln in lines)


def test_raznye_soobshcheniya_ne_shlopyvayutsya(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    for i in range(20):
        log.info(f"страница {i} обработана")

    lines = [ln for ln in read_log(log_dir).splitlines() if ln.strip()]
    assert len(lines) == 20


def test_posle_drugogo_soobshcheniya_schetchik_sbrasyvaetsya(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    for _ in range(10):
        log.error("одна и та же ошибка")
    log.info("что-то другое")
    for _ in range(10):
        log.error("одна и та же ошибка")

    text = read_log(log_dir)
    assert text.count("одна и та же ошибка") >= 6


# --------------------------------------------------------------------------- #
#  Ротация и устройство логгера
# --------------------------------------------------------------------------- #


def test_fayl_rotiruetsya_po_razmeru(tmp_path, monkeypatch):
    import importlib

    import logging_setup
    from tests.conftest import _drop_our_loggers

    _drop_our_loggers()
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_MAX_BYTES", "2000")
    monkeypatch.setenv("LOG_BACKUPS", "2")
    importlib.reload(logging_setup)

    log = logging_setup.get_logger("rot")
    for i in range(300):
        log.info(f"строка номер {i} с каким-то текстом подлиннее для объёма")

    _drop_our_loggers()
    files = sorted(p.name for p in tmp_path.glob("rot.log*"))
    assert "rot.log" in files
    assert len(files) <= 3, "backupCount не соблюдается"
    for path in tmp_path.glob("rot.log*"):
        assert path.stat().st_size < 10_000

    importlib.reload(logging_setup)


def test_propagate_otklyuchen(log_dir):
    """Иначе каждая строка уходит ещё и в корневой логгер, то есть в journald."""
    import logging_setup

    log = logging_setup.get_logger("t")
    assert log.propagate is False


def test_povtornyy_vyzov_otdayot_tot_zhe_logger(log_dir):
    import logging_setup

    first = logging_setup.get_logger("t")
    second = logging_setup.get_logger("t")
    assert first is second

    nashi = [h for h in first.handlers if getattr(h, logging_setup._MARKER, False)]
    assert len(nashi) == 1, "второй вызов не должен добавлять ещё один обработчик"


def test_raznye_imena_raznye_fayly(log_dir):
    import logging_setup

    logging_setup.get_logger("mts").info("из МТС")
    logging_setup.get_logger("beeline").info("из Билайна")

    assert "из МТС" in read_log(log_dir, "mts")
    assert "из Билайна" in read_log(log_dir, "beeline")
    assert "из Билайна" not in read_log(log_dir, "mts")


# --------------------------------------------------------------------------- #
#  Stat
# --------------------------------------------------------------------------- #


def test_stat_schitaet_i_pishet_odnu_stroku(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    stat = logging_setup.Stat("МТС", log)

    for _ in range(4812):
        stat.inc("обработано")
    stat.inc("обновлено", 117)
    stat.inc("ошибок API", 4)
    stat.done()

    text = read_log(log_dir)
    итог = [ln for ln in text.splitlines() if "готово за" in ln]
    assert len(итог) == 1
    assert "обработано 4812" in итог[0]
    assert "обновлено 117" in итог[0]
    assert "ошибок API 4" in итог[0]


def test_stat_get_i_inc(log_dir):
    import logging_setup

    stat = logging_setup.Stat("тест", logging_setup.get_logger("t"))
    assert stat.get("нет такого") == 0
    stat.inc("есть")
    stat.inc("есть", 5)
    assert stat.get("есть") == 6


def test_stat_heartbeat_tolko_na_kratnyh(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    stat = logging_setup.Stat("Билайн", log)
    for _ in range(1200):
        stat.inc("обработано")
        stat.heartbeat(every=500)

    beats = [ln for ln in read_log(log_dir).splitlines() if "Билайн: обработано" in ln]
    assert len(beats) == 2


def test_stat_failed_pishet_prichinu(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    stat = logging_setup.Stat("Билайн", log)
    stat.inc("обработано", 10)
    stat.failed(RuntimeError("связь пропала"))

    text = read_log(log_dir)
    assert "прервано" in text
    assert "связь пропала" in text
    assert "обработано 10" in text


def test_stat_note_v_log(log_dir):
    import logging_setup

    log = logging_setup.get_logger("t")
    stat = logging_setup.Stat("МТС", log)
    stat.note("счёт 252303 прочитан не полностью")

    assert "прочитан не полностью" in read_log(log_dir)


def test_uroven_logirovaniya_iz_okruzheniya(tmp_path, monkeypatch):
    import importlib

    import logging_setup
    from tests.conftest import _drop_our_loggers

    _drop_our_loggers()
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    importlib.reload(logging_setup)

    log = logging_setup.get_logger("lvl")
    log.info("это не должно попасть")
    log.warning("а это должно")

    _drop_our_loggers()
    text = (tmp_path / "lvl.log").read_text(encoding="utf-8")
    assert "не должно попасть" not in text
    assert "а это должно" in text

    importlib.reload(logging_setup)
