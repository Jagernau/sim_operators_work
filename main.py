"""
sim_operators_work — сбор данных по SIM-картам от МТС, Билайна и Теле2.

Расписание внутри программы (schedule), процессы по операторам.
Служба systemd называется по имени папки: sim_operators_work.

Запуск разового прогона без ожидания расписания:
    python main.py --now            все операторы
    python main.py --now mts        только МТС
    python main.py --now beeline    только Билайн
"""

from __future__ import annotations

import multiprocessing
import sys
import time

import schedule

from database.db_conectors import reset_pool
from logging_setup import get_logger

log = get_logger("main")

RUN_AT = "10:30"


def _run(name: str, title: str, func) -> None:
    """
    Тело дочернего процесса. reset_pool() обязателен: соединения с MySQL,
    унаследованные после fork, нельзя делить между процессами.
    """
    reset_pool()
    worker_log = get_logger(name)
    worker_log.info(f"{title}: старт")
    try:
        func()
    except Exception as e:
        worker_log.error(f"{title}: прервано — {e}", exc_info=True)


def process_mts() -> None:
    import clear_mts_entry
    _run("mts", "МТС", clear_mts_entry.mts_merge_data)


def process_beeline() -> None:
    import beeline_entry
    _run("beeline", "Билайн", beeline_entry.beeline_merge_data)


def process_tele2() -> None:
    import tele2_entry
    _run("tele2", "Теле2", tele2_entry.tele2_merge_data)


WORKERS = {
    "mts": process_mts,
    "beeline": process_beeline,
    # "tele2": process_tele2,   # парсер через selenium, включать осознанно
}


def job(only: str | None = None) -> None:
    started = time.monotonic()
    names = [only] if only else list(WORKERS)
    log.info(f"Прогон начат: {', '.join(names)}")

    processes = []
    for name in names:
        worker = WORKERS.get(name)
        if worker is None:
            log.error(f"Неизвестный оператор: {name}")
            continue
        p = multiprocessing.Process(target=worker, name=name)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
        if p.exitcode != 0:
            log.error(f"Процесс {p.name} завершился с кодом {p.exitcode}")

    log.info(f"Прогон закончен за {int(time.monotonic() - started) // 60} мин")


if __name__ == "__main__":
    if "--now" in sys.argv:
        index = sys.argv.index("--now")
        only = sys.argv[index + 1] if len(sys.argv) > index + 1 else None
        job(only)
        sys.exit(0)

    schedule.every().day.at(RUN_AT).do(job)
    log.info(f"Запущен, прогон каждый день в {RUN_AT}")

    while True:
        schedule.run_pending()
        time.sleep(30)
