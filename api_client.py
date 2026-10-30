"""
Общий HTTP-слой для коллекторов sim_operators_work.

Решает три вещи, из-за которых сейчас ловятся троттлинги и теряется время:

  1. RateLimiter — ровная выдача запросов (token bucket) вместо sleep(2)
     в каждом методе. Лимит задаётся в запросах в минуту и меняется на ходу.
  2. ApiSession — одна keep-alive сессия на весь прогон (не новое TLS-рукопожатие
     на каждый запрос), обязательный таймаут, разбор 429 с Retry-After
     и экспоненциальным отступом, чтение заголовков X-RateLimit-*.
  3. TokenCache — токен живёт столько, сколько сказал оператор, и запрашивается
     один раз, а не на каждой странице.

Зависимости те же, что уже в requirements.txt (requests).

Пример:

    from api_client import ApiSession, RateLimiter

    api = ApiSession("mts", RateLimiter(rate_per_min=60), log)
    r = api.get(url, headers=headers)      # вернёт Response или бросит ApiError
"""

from __future__ import annotations

import random
import threading
import time
from typing import Callable, Optional

import requests


class ApiError(RuntimeError):
    """Запрос не удался после всех повторов."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class RateLimitedOut(ApiError):
    """Оператор держит нас в троттлинге дольше, чем мы готовы ждать."""


# --------------------------------------------------------------------------- #
#  Ограничитель частоты
# --------------------------------------------------------------------------- #


class RateLimiter:
    """
    Token bucket. Пропускает не больше rate_per_min запросов в минуту,
    распределяя их ровно, а не пачкой.

    `set_rate()` позволяет понизить скорость на ходу — например, когда оператор
    прислал X-RateLimit-Remaining близко к нулю.
    """

    def __init__(self, rate_per_min: float, burst: int = 1):
        self._lock = threading.Lock()
        self._burst = max(1, burst)
        self._tokens = float(self._burst)
        self._updated = time.monotonic()
        self.set_rate(rate_per_min)

    def set_rate(self, rate_per_min: float) -> None:
        with self._lock:
            self._rate = max(0.1, float(rate_per_min)) / 60.0  # запросов в секунду

    @property
    def rate_per_min(self) -> float:
        return self._rate * 60.0

    def acquire(self) -> float:
        """Блокирует вызывающий поток, пока не придёт очередь. Возвращает, сколько ждали."""
        waited = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self._burst, self._tokens + (now - self._updated) * self._rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return waited
                need = (1.0 - self._tokens) / self._rate
            time.sleep(need)
            waited += need


# --------------------------------------------------------------------------- #
#  Кеш токена
# --------------------------------------------------------------------------- #


class TokenCache:
    """
    Хранит токен и сам обновляет его, когда до конца срока осталось меньше `margin`.

        cache = TokenCache(fetch=lambda: ("eyJ...", 3600))
        headers["Authorization"] = f"Bearer {cache.token}"

    `fetch` должна вернуть (токен, время жизни в секундах).
    """

    def __init__(self, fetch: Callable[[], tuple[str, int]], margin: int = 300):
        self._fetch = fetch
        self._margin = margin
        self._token: Optional[str] = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    @property
    def token(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._expires_at - self._margin:
                return self._token
            token, ttl = self._fetch()
            if not token:
                raise ApiError("Оператор не вернул токен")
            self._token = token
            self._expires_at = time.monotonic() + max(60, int(ttl or 3600))
            return self._token

    def invalidate(self) -> None:
        """Сбросить токен — например, после 401 token expired."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0


# --------------------------------------------------------------------------- #
#  Сессия
# --------------------------------------------------------------------------- #


class ApiSession:
    """
    Обёртка над requests.Session с лимитером и разбором 429.

    Параметры:
        name          — для сообщений в логе («МТС», «Билайн»)
        limiter       — RateLimiter
        log           — логгер из logging_setup
        timeout       — (на соединение, на чтение)
        max_retries   — сколько раз повторять 429 и 5xx
        max_wait      — дольше этого суммарно не ждём, бросаем RateLimitedOut
        adaptive      — понижать скорость по X-RateLimit-Remaining
    """

    RETRY_STATUSES = (429, 500, 502, 503, 504)

    def __init__(
        self,
        name: str,
        limiter: RateLimiter,
        log,
        timeout: tuple[float, float] = (10.0, 60.0),
        max_retries: int = 5,
        max_wait: float = 300.0,
        adaptive: bool = True,
    ):
        self.name = name
        self.limiter = limiter
        self.log = log
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_wait = max_wait
        self.adaptive = adaptive

        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Базовый темп, к которому возвращаемся после троттлинга
        self._base_rate = limiter.rate_per_min
        self._podryad_uspeshnyh = 0

        # Счётчики для итоговой строки в логе
        self.requests_made = 0
        self.throttled = 0
        self.total_wait = 0.0
        self.snizheniy_skorosti = 0

    # ---------------------------------------------------------------- helpers

    def _retry_after(self, response: requests.Response, attempt: int) -> float:
        """Сколько ждать перед повтором: уважаем Retry-After, иначе 2^attempt с джиттером."""
        header = response.headers.get("Retry-After")
        if header:
            try:
                return min(self.max_wait, float(header))
            except ValueError:
                pass
        return min(60.0, (2 ** attempt) + random.uniform(0, 1.5))

    # Сколько успешных запросов подряд нужно, чтобы вернуть часть темпа
    USPEHOV_DLYA_RAZGONA = 50

    def _razgon(self) -> None:
        """
        Возвращаем темп после троттлинга.

        У МТС нет заголовков X-RateLimit, поэтому поднять скорость обратно
        больше нечем: без этого один случайный 429 сажал бы весь прогон на
        половинный темп до самого конца, а на 6800 запросах это лишний час.
        """
        if self.limiter.rate_per_min >= self._base_rate:
            self._podryad_uspeshnyh = 0
            return
        self._podryad_uspeshnyh += 1
        if self._podryad_uspeshnyh < self.USPEHOV_DLYA_RAZGONA:
            return

        self._podryad_uspeshnyh = 0
        novaya = min(self._base_rate, self.limiter.rate_per_min * 1.25)
        self.limiter.set_rate(novaya)
        self.log.info(
            f"{self.name}: {self.USPEHOV_DLYA_RAZGONA} запросов без отказов, "
            f"поднимаю темп до {novaya:.0f} зап/мин"
        )

    def _read_rate_headers(self, response: requests.Response) -> None:
        """
        Билайн отдаёт X-RateLimit-Limit (запросов в минуту) и X-RateLimit-Remaining.
        Подстраиваем скорость: пока остаток большой — идём по лимиту оператора,
        когда остаётся меньше четверти — притормаживаем вдвое.
        """
        if not self.adaptive:
            return
        limit = response.headers.get("X-RateLimit-Limit")
        remaining = response.headers.get("X-RateLimit-Remaining")
        if not limit:
            return
        try:
            limit_value = float(limit)
            remaining_value = float(remaining) if remaining is not None else limit_value
        except ValueError:
            return
        if limit_value <= 0:
            return

        # 80 % от лимита оператора — рабочая скорость, оставляем запас.
        target = limit_value * 0.8
        if remaining_value < limit_value * 0.25:
            target = max(1.0, target / 2)
        if abs(target - self.limiter.rate_per_min) > 1:
            self.limiter.set_rate(target)
            self._base_rate = max(self._base_rate, target)

    # ---------------------------------------------------------------- request

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        slept = 0.0

        for attempt in range(self.max_retries + 1):
            self.total_wait += self.limiter.acquire()
            try:
                response = self.session.request(method, url, **kwargs)
            except requests.Timeout as e:
                if attempt >= self.max_retries:
                    raise ApiError(f"{self.name}: таймаут — {e}") from e
                pause = min(30.0, 2 ** attempt)
                self.log.warning(f"{self.name}: таймаут, повтор через {pause:.0f} с")
                time.sleep(pause)
                slept += pause
                continue
            except requests.RequestException as e:
                if attempt >= self.max_retries:
                    raise ApiError(f"{self.name}: сеть недоступна — {e}") from e
                pause = min(30.0, 2 ** attempt)
                self.log.warning(f"{self.name}: ошибка сети ({e.__class__.__name__}), повтор через {pause:.0f} с")
                time.sleep(pause)
                slept += pause
                continue

            self.requests_made += 1
            self._read_rate_headers(response)

            if response.status_code not in self.RETRY_STATUSES:
                self._razgon()
                return response

            if response.status_code == 429:
                self.throttled += 1
                self._podryad_uspeshnyh = 0

            if attempt >= self.max_retries:
                raise ApiError(
                    f"{self.name}: {response.status_code} после {attempt + 1} попыток",
                    status=response.status_code,
                )

            pause = self._retry_after(response, attempt)
            if slept + pause > self.max_wait:
                raise RateLimitedOut(
                    f"{self.name}: троттлинг дольше {self.max_wait:.0f} с, прекращаю",
                    status=response.status_code,
                )

            if response.status_code == 429:
                # При троттлинге сразу режем скорость вдвое — вернёмся наверх по заголовкам.
                self.limiter.set_rate(max(1.0, self.limiter.rate_per_min / 2))
                self.snizheniy_skorosti += 1
                self.log.warning(
                    f"{self.name}: троттлинг (429), жду {pause:.0f} с, "
                    f"скорость снижена до {self.limiter.rate_per_min:.0f} зап/мин"
                )
            else:
                self.log.warning(f"{self.name}: {response.status_code}, повтор через {pause:.0f} с")

            time.sleep(pause)
            slept += pause

        raise ApiError(f"{self.name}: не удалось выполнить запрос")

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def stats(self) -> str:
        return (
            f"запросов {self.requests_made}, троттлингов {self.throttled}, "
            f"снижений темпа {self.snizheniy_skorosti}, "
            f"ожидание лимитера {self.total_wait:.0f} с, "
            f"темп {self.limiter.rate_per_min:.0f} из {self._base_rate:.0f} зап/мин"
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
