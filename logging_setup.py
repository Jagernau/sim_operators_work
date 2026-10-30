"""
Единая настройка логирования для sim_operators_work.

Заменяет logger.py, mts_logger.py, beeline_logger.py, tele2_logger.py.

Что делает иначе, чем старые логгеры:
  * ротация средствами самого Python (RotatingFileHandler), а не только внешним
    logrotate — файл физически не может вырасти больше LOG_MAX_BYTES * (LOG_BACKUPS + 1);
  * маскирует токены и пароли, чтобы они не попадали в файл;
  * схлопывает одинаковые сообщения, идущие подряд (защита от зацикливания);
  * propagate = False — строка не дублируется в корневой логгер и journald;
  * класс Stat — копит счётчики по ходу прогона и пишет ОДНУ итоговую строку
    вместо сотен «начало…/конец…».

Использование:

    from logging_setup import get_logger, Stat

    log = get_logger("mts")          # пишет в mts.log
    stat = Stat("МТС", log)

    stat.inc("обработано")
    stat.inc("ошибок API")
    stat.done()                      # одна строка с итогами и временем

Настройки через .env (все необязательные):
    LOG_DIR         — куда класть файлы (по умолчанию — папка программы)
    LOG_LEVEL       — INFO (по умолчанию) или DEBUG для подробного режима
    LOG_MAX_BYTES   — размер файла до ротации, по умолчанию 10 МБ
    LOG_BACKUPS     — сколько старых файлов хранить, по умолчанию 3
    LOG_STDOUT      — 1, чтобы дополнительно писать в stdout (для promtail/journald)
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
import time
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR") or Path(__file__).resolve().parent)
LOG_LEVEL = (os.getenv("LOG_LEVEL") or "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES") or 10 * 1024 * 1024)
LOG_BACKUPS = int(os.getenv("LOG_BACKUPS") or 3)
LOG_STDOUT = (os.getenv("LOG_STDOUT") or "0") == "1"


# --------------------------------------------------------------------------- #
#  Маскировка секретов
# --------------------------------------------------------------------------- #

# Ловим «ключ: значение» и «Bearer xxx». Значение режем до первых 6 символов.
_SECRET_RE = re.compile(
    r"(?i)\b(bearer\s+|access[_-]?token|refresh[_-]?token|client[_-]?secret"
    r"|password|passwd|api[_-]?key|authorization)\b([\"'\s:=]*)([A-Za-z0-9._~+/\-]{10,})"
)

# Отдельно — длинные JWT, попавшие в текст сами по себе.
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9._~+/\-]{20,}")


def _mask(text: str) -> str:
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)[:6]}…скрыто", text)
    text = _JWT_RE.sub(lambda m: f"{m.group(0)[:10]}…скрыто", text)
    return text


class SecretFilter(logging.Filter):
    """Вырезает токены и пароли из текста сообщения."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                record.msg = record.getMessage()
            except Exception:
                record.msg = str(record.msg)
            record.args = ()
        record.msg = _mask(str(record.msg))
        return True


# --------------------------------------------------------------------------- #
#  Схлопывание повторов
# --------------------------------------------------------------------------- #


class RepeatFilter(logging.Filter):
    """
    Пропускает первые `head` одинаковых подряд сообщений, дальше — каждое `step`-е,
    дописывая «(повтор N)». Если программа зациклилась на одной ошибке, в файл
    попадёт десяток строк вместо десятков тысяч.
    """

    def __init__(self, head: int = 3, step: int = 100):
        super().__init__()
        self.head = head
        self.step = step
        self._key = None
        self._count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        key = (record.name, record.levelno, str(record.msg)[:300])
        if key != self._key:
            self._key = key
            self._count = 1
            return True

        self._count += 1
        if self._count <= self.head:
            return True
        if self._count % self.step == 0:
            record.msg = f"{record.msg}  (повтор {self._count})"
            return True
        return False


# --------------------------------------------------------------------------- #
#  Логгеры
# --------------------------------------------------------------------------- #

_FORMAT = "%(asctime)s %(levelname)-5s %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


_MARKER = "_sim_operators_handler"


def _already_configured(logger: logging.Logger) -> bool:
    """
    Настроен ли логгер нами. Проверяем свою метку, а не просто наличие
    обработчиков: сторонние библиотеки (pytest, например) вешают свои
    обработчики на тот же логгер, и тогда файл молча перестаёт писаться.
    """
    return any(getattr(h, _MARKER, False) for h in logger.handlers)


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер, пишущий в <LOG_DIR>/<name>.log.
    Повторный вызов с тем же именем отдаёт уже настроенный логгер.
    """
    logger = logging.getLogger(name)
    if _already_configured(logger):
        return logger

    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    formatter = logging.Formatter(_FORMAT, _DATEFMT)
    secret_filter = SecretFilter()
    repeat_filter = RepeatFilter()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUPS,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    file_handler.addFilter(repeat_filter)
    setattr(file_handler, _MARKER, True)
    logger.addHandler(file_handler)

    if LOG_STDOUT:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(secret_filter)
        stream_handler.addFilter(repeat_filter)
        setattr(stream_handler, _MARKER, True)
        logger.addHandler(stream_handler)

    return logger


# --------------------------------------------------------------------------- #
#  Счётчики вместо построчного спама
# --------------------------------------------------------------------------- #


class Stat:
    """
    Копит счётчики за прогон и выводит их одной строкой.

        stat = Stat("МТС", log)
        stat.inc("обработано")
        stat.inc("ошибок API")
        stat.note("страница 7 пустая")   # редкое событие — в лог сразу
        stat.heartbeat(every=500)        # промежуточная строка раз в 500 шагов
        stat.done()

    Итог выглядит так:
        2026-10-30 10:41:02 INFO  МТС: готово за 7 мин 12 с — обработано 4812,
        добавлено 3, обновлено 117, ошибок API 4
    """

    def __init__(self, title: str, logger: logging.Logger):
        self.title = title
        self.log = logger
        self.counters: dict[str, int] = {}
        self.started = time.monotonic()
        self._last_beat = 0

    def inc(self, key: str, by: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + by

    def get(self, key: str) -> int:
        return self.counters.get(key, 0)

    def note(self, message: str, level: int = logging.WARNING) -> None:
        """Разовое событие, которое стоит увидеть в логе отдельной строкой."""
        self.log.log(level, f"{self.title}: {message}")

    def heartbeat(self, key: str = "обработано", every: int = 500) -> None:
        """Промежуточный прогресс — чтобы в долгом прогоне было видно, что он жив."""
        value = self.get(key)
        if value and value != self._last_beat and value % every == 0:
            self._last_beat = value
            self.log.info(f"{self.title}: {self._summary()}")

    def _elapsed(self) -> str:
        seconds = int(time.monotonic() - self.started)
        if seconds < 60:
            return f"{seconds} с"
        return f"{seconds // 60} мин {seconds % 60} с"

    def _summary(self) -> str:
        if not self.counters:
            return "нечего считать"
        return ", ".join(f"{k} {v}" for k, v in self.counters.items())

    def done(self) -> None:
        self.log.info(f"{self.title}: готово за {self._elapsed()} — {self._summary()}")

    def failed(self, error: BaseException) -> None:
        self.log.error(
            f"{self.title}: прервано через {self._elapsed()} — {self._summary()}; причина: {error}"
        )
