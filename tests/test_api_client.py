"""HTTP-слой: лимитер, кеш токена, разбор 429 и заголовков X-RateLimit."""

from __future__ import annotations

import time

import pytest
import requests

from api_client import ApiError, ApiSession, RateLimitedOut, RateLimiter, TokenCache


@pytest.fixture
def log():
    import logging_setup

    return logging_setup.get_logger("test_api")


# --------------------------------------------------------------------------- #
#  RateLimiter
# --------------------------------------------------------------------------- #


def test_limiter_derzhit_temp():
    limiter = RateLimiter(rate_per_min=120)  # два в секунду
    started = time.monotonic()
    for _ in range(6):
        limiter.acquire()
    elapsed = time.monotonic() - started
    assert 2.0 < elapsed < 3.5, f"6 запросов при 120/мин заняли {elapsed:.2f} с"


def test_limiter_menyaet_skorost_na_hodu():
    limiter = RateLimiter(rate_per_min=60)
    limiter.set_rate(600)
    started = time.monotonic()
    for _ in range(5):
        limiter.acquire()
    assert time.monotonic() - started < 1.0


def test_limiter_ne_opuskaetsya_v_nol():
    limiter = RateLimiter(rate_per_min=60)
    limiter.set_rate(0)
    assert limiter.rate_per_min > 0


def test_limiter_vozvrashchaet_vremya_ozhidaniya():
    limiter = RateLimiter(rate_per_min=60)
    limiter.acquire()               # первый проходит сразу
    waited = limiter.acquire()
    assert waited > 0.5


# --------------------------------------------------------------------------- #
#  TokenCache
# --------------------------------------------------------------------------- #


def test_token_zaprashivaetsya_odin_raz():
    """Главная экономия: раньше токен брался на каждой странице обхода."""
    calls = []

    def fetch():
        calls.append(1)
        return f"token-{len(calls)}", 3600

    cache = TokenCache(fetch)
    for _ in range(500):
        assert cache.token == "token-1"
    assert len(calls) == 1


def test_token_obnovlyaetsya_posle_invalidate():
    calls = []

    def fetch():
        calls.append(1)
        return f"token-{len(calls)}", 3600

    cache = TokenCache(fetch)
    assert cache.token == "token-1"
    cache.invalidate()
    assert cache.token == "token-2"
    assert len(calls) == 2


def test_token_obnovlyaetsya_po_istechenii():
    calls = []

    def fetch():
        calls.append(1)
        return f"token-{len(calls)}", 10      # живёт 10 с при запасе 300 с

    cache = TokenCache(fetch, margin=300)
    assert cache.token == "token-1"
    assert cache.token == "token-2", "истёкший токен должен перезапрашиваться"


def test_token_pustoy_eto_oshibka():
    cache = TokenCache(lambda: ("", 3600))
    with pytest.raises(ApiError):
        _ = cache.token


# --------------------------------------------------------------------------- #
#  429 и ретраи
# --------------------------------------------------------------------------- #


def test_429_potom_uspeh(log, beeline_mock):
    """Три троттлинга подряд, затем нормальный ответ."""
    state, url = beeline_mock
    state.mode = "flaky"
    state.flaky_left = 3

    api = ApiSession("тест", RateLimiter(100000), log, max_retries=5, max_wait=60)
    response = api.get(f"{url}/anything")

    assert response.status_code == 200
    assert api.throttled == 3


def test_429_snizhaet_skorost(log, beeline_mock):
    state, url = beeline_mock
    state.mode = "flaky"
    state.flaky_left = 1

    api = ApiSession("тест", RateLimiter(100), log, max_retries=3, max_wait=60, adaptive=False)
    api.get(f"{url}/anything")

    assert api.limiter.rate_per_min <= 50, "после 429 скорость должна падать вдвое"


def test_postoyannyy_429_ne_beskonechen(log, beeline_mock):
    state, url = beeline_mock
    state.mode = "429"

    api = ApiSession("тест", RateLimiter(100000), log, max_retries=2, max_wait=60)
    started = time.monotonic()
    with pytest.raises(ApiError):
        api.get(f"{url}/anything")
    assert time.monotonic() - started < 30


def test_max_wait_preryvaet_trottling(log, beeline_mock):
    state, url = beeline_mock
    state.mode = "429"

    api = ApiSession("тест", RateLimiter(100000), log, max_retries=50, max_wait=2)
    with pytest.raises(RateLimitedOut):
        api.get(f"{url}/anything")


def test_500_retryitsya_i_padaet(log, mts_mock):
    state, url = mts_mock
    state.mode = "500"

    api = ApiSession("тест", RateLimiter(100000), log, max_retries=1, max_wait=30)
    with pytest.raises(ApiError) as excinfo:
        api.get(f"{url}/b2b/v1/Service/HierarchyStructure")
    assert excinfo.value.status == 500


def test_404_ne_retryitsya(log, mts_mock):
    """404 не в списке повторяемых — возвращается сразу, без пауз."""
    state, url = mts_mock
    state.mode = "404"

    api = ApiSession("тест", RateLimiter(100000), log, max_retries=5)
    started = time.monotonic()
    response = api.get(f"{url}/b2b/v1/Service/HierarchyStructure")

    assert response.status_code == 404
    assert time.monotonic() - started < 2
    assert api.requests_made == 1


# --------------------------------------------------------------------------- #
#  Заголовки X-RateLimit
# --------------------------------------------------------------------------- #


def test_skorost_podstraivaetsya_pod_zagolovok(log, beeline_mock):
    state, url = beeline_mock
    state.rate_limit_header = "100"

    api = ApiSession("тест", RateLimiter(10), log, adaptive=True)
    api.get(f"{url}/anything")

    assert api.limiter.rate_per_min == pytest.approx(80, abs=1), "ожидаем 80% от лимита оператора"


def test_adaptive_vyklyuchen_ne_menyaet_skorost(log, beeline_mock):
    state, url = beeline_mock
    state.rate_limit_header = "600"

    api = ApiSession("тест", RateLimiter(30), log, adaptive=False)
    api.get(f"{url}/anything")

    assert api.limiter.rate_per_min == pytest.approx(30, abs=1)


def test_bez_zagolovkov_skorost_ne_menyaetsya(log, mts_mock):
    """У МТС заголовков X-RateLimit может не быть — темп держим своим лимитером."""
    state, url = mts_mock
    state.rate_limit_header = None

    api = ApiSession("тест", RateLimiter(45), log, adaptive=True)
    api.get(f"{url}/b2b/v1/Service/HierarchyStructure")

    assert api.limiter.rate_per_min == pytest.approx(45, abs=1)


# --------------------------------------------------------------------------- #
#  Таймауты и сеть
# --------------------------------------------------------------------------- #


def test_timeout_propisan_po_umolchaniyu(log, monkeypatch, beeline_mock):
    """Без таймаута зависший запрос вешал весь прогон до бесконечности."""
    state, url = beeline_mock
    api = ApiSession("тест", RateLimiter(100000), log, timeout=(3.0, 7.0))

    seen = {}
    original = api.session.request

    def spy(method, url_, **kwargs):
        seen.update(kwargs)
        return original(method, url_, **kwargs)

    monkeypatch.setattr(api.session, "request", spy)
    api.get(f"{url}/anything")

    assert seen["timeout"] == (3.0, 7.0)


def test_nedostupnyy_host_daet_apierror(log):
    api = ApiSession("тест", RateLimiter(100000), log, max_retries=1, timeout=(1, 1))
    with pytest.raises(ApiError):
        api.get("http://127.0.0.1:9/nothing")


def test_stats_soderzhit_schetchiki(log, beeline_mock):
    state, url = beeline_mock
    api = ApiSession("тест", RateLimiter(100000), log)
    api.get(f"{url}/anything")

    text = api.stats()
    assert "запросов 1" in text
    assert "троттлингов 0" in text


def test_session_zakryvaetsya_kak_kontekst(log, beeline_mock):
    state, url = beeline_mock
    with ApiSession("тест", RateLimiter(100000), log) as api:
        api.get(f"{url}/anything")
    assert api.requests_made == 1


# --------------------------------------------------------------------------- #
#  Восстановление темпа после троттлинга
# --------------------------------------------------------------------------- #


def test_temp_vosstanavlivaetsya_posle_trottlinga(log, beeline_mock, monkeypatch):
    """
    У МТС заголовков X-RateLimit нет, поднять скорость обратно больше нечем.
    Без разгона один случайный 429 сажал бы весь прогон на половинный темп.
    """
    state, url = beeline_mock
    state.mode = "flaky"
    state.flaky_left = 1

    api = ApiSession("тест", RateLimiter(200), log, max_retries=3, max_wait=30, adaptive=False)
    monkeypatch.setattr(api, "USPEHOV_DLYA_RAZGONA", 5)

    api.get(f"{url}/anything")                 # ловим 429, темп падает вдвое
    posle_429 = api.limiter.rate_per_min
    assert posle_429 == pytest.approx(100, abs=1)

    for _ in range(5):
        api.get(f"{url}/anything")

    assert api.limiter.rate_per_min > posle_429, "после череды успехов темп должен расти"
    assert api.snizheniy_skorosti == 1


def test_razgon_ne_prevyshaet_bazovyy_temp(log, beeline_mock, monkeypatch):
    """Разгон возвращает к исходному значению, но не выше него."""
    state, url = beeline_mock

    api = ApiSession("тест", RateLimiter(120), log, adaptive=False)
    monkeypatch.setattr(api, "USPEHOV_DLYA_RAZGONA", 2)

    for _ in range(20):
        api.get(f"{url}/anything")

    assert api.limiter.rate_per_min == pytest.approx(120, abs=1)


def test_schetchik_snizheniy_v_statistike(log, beeline_mock):
    state, url = beeline_mock
    state.mode = "flaky"
    state.flaky_left = 2

    api = ApiSession("тест", RateLimiter(200), log, max_retries=5, max_wait=30, adaptive=False)
    api.get(f"{url}/anything")

    assert "снижений темпа" in api.stats()
    assert api.snizheniy_skorosti == 2
