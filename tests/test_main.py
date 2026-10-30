"""Точка входа: какие операторы запускаются и как переживаются падения."""

from __future__ import annotations

import pytest

import main


@pytest.fixture
def main_log(log_dir, monkeypatch):
    """
    main.log создаётся при импорте модуля, то есть до подмены папки логов.
    Пересоздаём его под временную папку теста.
    """
    import logging_setup

    monkeypatch.setattr(main, "log", logging_setup.get_logger("main"))
    return log_dir


def test_tele2_vyklyuchen():
    """
    Теле2 собирается парсером отдельно и по расписанию подниматься не должен.
    Если эту строку когда-нибудь раскомментируют, тест об этом напомнит.
    """
    assert "tele2" not in main.WORKERS
    assert set(main.WORKERS) == {"mts", "beeline"}


def test_raspisanie_vnutri_programmy():
    """Планировщик живёт в самой программе, а не в systemd timer."""
    assert main.RUN_AT == "10:30"


def test_run_vyzyvaet_funkciyu(monkeypatch, log_dir):
    called = []
    monkeypatch.setattr(main, "reset_pool", lambda: called.append("reset"))

    main._run("mts", "МТС", lambda: called.append("job"))

    assert called == ["reset", "job"], "пул соединений надо сбрасывать до работы"


def test_run_sbrasyvaet_pul_posle_fork(monkeypatch, log_dir):
    """Унаследованные после fork соединения нельзя делить между процессами."""
    calls = []
    monkeypatch.setattr(main, "reset_pool", lambda: calls.append(1))

    main._run("beeline", "Билайн", lambda: None)

    assert calls == [1]


def test_run_ne_probrasyvaet_isklyuchenie(monkeypatch, log_dir):
    """Падение одного оператора не должно ронять весь процесс."""
    monkeypatch.setattr(main, "reset_pool", lambda: None)

    def boom():
        raise RuntimeError("связь пропала")

    main._run("mts", "МТС", boom)   # не должно бросить наружу

    text = (log_dir / "mts.log").read_text(encoding="utf-8")
    assert "прервано" in text
    assert "связь пропала" in text


def test_job_s_neizvestnym_operatorom(monkeypatch, main_log):
    started = []
    monkeypatch.setattr(main, "WORKERS", {"mts": lambda: started.append("mts")})

    main.job("несуществующий")

    assert started == []
    assert "Неизвестный оператор" in (main_log / "main.log").read_text(encoding="utf-8")


def test_job_zapuskaet_tolko_ukazannogo(monkeypatch, main_log):
    class FakeProcess:
        started = []

        def __init__(self, target=None, name=None):
            self.name = name
            self.exitcode = 0

        def start(self):
            FakeProcess.started.append(self.name)

        def join(self):
            pass

    FakeProcess.started = []
    monkeypatch.setattr(main.multiprocessing, "Process", FakeProcess)

    main.job("beeline")

    assert FakeProcess.started == ["beeline"]


def test_job_bez_argumenta_zapuskaet_vseh(monkeypatch, main_log):
    class FakeProcess:
        started = []

        def __init__(self, target=None, name=None):
            self.name = name
            self.exitcode = 0

        def start(self):
            FakeProcess.started.append(self.name)

        def join(self):
            pass

    FakeProcess.started = []
    monkeypatch.setattr(main.multiprocessing, "Process", FakeProcess)

    main.job()

    assert set(FakeProcess.started) == {"mts", "beeline"}


def test_nenulevoy_kod_vyhoda_v_log(monkeypatch, main_log):
    class FakeProcess:
        def __init__(self, target=None, name=None):
            self.name = name
            self.exitcode = 1

        def start(self):
            pass

        def join(self):
            pass

    monkeypatch.setattr(main.multiprocessing, "Process", FakeProcess)

    main.job("mts")

    assert "завершился с кодом 1" in (main_log / "main.log").read_text(encoding="utf-8")
