#!/usr/bin/env python3
"""
Поиск предельного темпа обращений к API операторов.

МТС лимиты не публикует и заголовков X-RateLimit не отдаёт (проверено на живых
ответах 30.10.2026) — остаётся измерять. Билайн сам сообщает X-RateLimit-Limit:
60/мин на /oauth/token и 600/мин на рабочих методах, так что для него замер
нужен разве что для проверки.

Замер идёт в три фазы:

  1. ВСПЛЕСК — пачка запросов подряд без пауз. Ловит посекундный лимит,
     который лестница по минутам не увидит.
  2. ЛЕСТНИЦА — ровный темп, ступенями вверх, до первого 429.
  3. ВОССТАНОВЛЕНИЕ — если поймали 429, замеряем, через сколько снова пускает.

Важно мерить тот метод, которым идёт массовый обход. У МТС это ProductInfo
(блокировки по каждому номеру) — на 6800 симок приходится 6800 таких запросов,
а HierarchyStructure вызывается всего несколько десятков раз за прогон.

Запуск из папки программы:

    python tools/measure_api_limits.py --operator mts                 # блокировки
    python tools/measure_api_limits.py --operator mts --method structure
    python tools/measure_api_limits.py --operator beeline
    python tools/measure_api_limits.py --operator mts --max-rpm 600 --no-burst

Скрипт только читает. Запускать в нерабочее время: квота общая на организацию,
и упереться в потолок днём означает отвалившиеся запросы у соседних интеграций.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

import config  # noqa: E402
from api_client import ApiSession, RateLimiter  # noqa: E402
from logging_setup import get_logger  # noqa: E402

log = get_logger("measure_limits")

# Ступени темпа, запросов в минуту.
LADDER = [20, 40, 60, 90, 120, 180, 240, 300, 400, 600]

# Сколько запросов отправить во всплеске (без пауз вообще).
BURST_SIZE = 15

# Сколько запросов обычно нужно за один боевой прогон — для пересчёта в часы.
ZAPROSOV_ZA_PROGON = {"mts": 6800, "beeline": 44}


# --------------------------------------------------------------------------- #
#  Подготовка запросов
# --------------------------------------------------------------------------- #


def _mts_token() -> str:
    response = requests.post(
        f"{str(config.MTS_BASE_URL).rstrip('/')}/token",
        auth=(str(config.MTS_USERNAME), str(config.MTS_PASSWORD)),
        data={"grant_type": "client_credentials"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=(10, 30),
    )
    response.raise_for_status()
    payload = response.json()
    log.info(f"МТС: токен получен, живёт {payload.get('expires_in')} с")
    return payload["access_token"]


def _mts_nomera(token: str, nado: int) -> list[str]:
    """Берём реальные номера: ProductInfo по одному и тому же номеру может кешироваться."""
    base = str(config.MTS_BASE_URL).rstrip("/")
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    nomera: list[str] = []
    page = 1
    while len(nomera) < nado and page <= 10:
        response = requests.get(
            f"{base}/b2b/v1/Service/HierarchyStructure",
            params={"account": int(config.MTS_ACCOUNT_NUMBER), "pageNum": page, "pageSize": 100},
            headers=headers,
            timeout=(10, 60),
        )
        if response.status_code != 200:
            break
        try:
            relations = response.json()[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
        except (KeyError, IndexError, TypeError):
            break
        if not relations:
            break
        nomera.extend(str(r["product"]["productSerialNumber"]) for r in relations)
        page += 1
    return nomera[:nado]


def mts_probe(method: str):
    """(описание, функция запроса) для МТС."""
    token = _mts_token()
    base = str(config.MTS_BASE_URL).rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    if method == "structure":
        url = f"{base}/b2b/v1/Service/HierarchyStructure"
        params = {"account": int(config.MTS_ACCOUNT_NUMBER), "pageNum": 1, "pageSize": 100}

        def do(api: ApiSession, nomer_zaprosa: int):
            return api.session.get(url, params=params, headers=headers, timeout=(10, 60))

        return "МТС HierarchyStructure (pageSize=100)", do

    # по умолчанию — блокировки: именно их программа запрашивает тысячами
    nomera = _mts_nomera(token, 400)
    if not nomera:
        raise SystemExit("не удалось получить список номеров для замера")
    log.info(f"МТС: для замера взято {len(nomera)} разных номеров")

    url = f"{base}/b2b/v1/Product/ProductInfo"

    def do(api: ApiSession, nomer_zaprosa: int):
        params = {
            "category.name": "MobileConnectivity",
            "marketSegment.characteristic.name": "MSISDN",
            "marketSegment.characteristic.value": nomera[nomer_zaprosa % len(nomera)],
            "productOffering.actionAllowed": "none",
            "productOffering.productSpecification.productSpecificationType.name": "block",
            "applyTimeZone": "true",
        }
        return api.session.get(url, params=params, headers=headers, timeout=(10, 60))

    return f"МТС ProductInfo — блокировки, по {len(nomera)} разным номерам", do


def beeline_probe(method: str):
    """(описание, функция запроса) для Билайна."""
    response = requests.post(
        f"{str(config.BILINE_BASE_URL).rstrip('/')}/oauth/token",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "username": config.BILINE_USERNAME,
                "password": config.BILINE_PASSWORD,
                "client_id": config.BILINE_CLIENT_ID,
                "client_secret": config.BILINE_CLIENT_SECRET,
                "grant_type": "password",
            }
        ),
        timeout=(10, 30),
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    log.info("Билайн: токен получен")

    base = str(config.BILINE_BASE_URL).rstrip("/")
    url = f"{base}/api/v0/dashboards/{config.BILINE_DASHBORD}/sim_cards/list_all_sim"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Requested-With": "XMLHttpRequest",
    }

    def do(api: ApiSession, nomer_zaprosa: int):
        body = json.dumps({"page": (nomer_zaprosa % 40) + 1, "perpage": 30, "order": {"id": "asc"}})
        return api.session.post(url, headers=headers, data=body, timeout=(10, 60))

    return "Билайн list_all_sim", do


PROBES = {"mts": mts_probe, "beeline": beeline_probe}


# --------------------------------------------------------------------------- #
#  Фаза 1. Всплеск
# --------------------------------------------------------------------------- #


def faza_vsplesk(api: ApiSession, do, count: int) -> dict:
    """
    Запросы подряд, без пауз. Если у оператора есть посекундный лимит,
    он проявится именно здесь, а не на минутной лестнице.
    """
    ok = throttled = other = 0
    pervyy_429 = None
    nachalo = time.monotonic()
    retry_after = None

    for i in range(count):
        try:
            response = do(api, i)
        except requests.RequestException:
            other += 1
            continue
        if response.status_code == 200:
            ok += 1
        elif response.status_code == 429:
            throttled += 1
            if pervyy_429 is None:
                pervyy_429 = i + 1
                retry_after = response.headers.get("Retry-After")
        else:
            other += 1

    proshlo = time.monotonic() - nachalo
    return {
        "ok": ok,
        "throttled": throttled,
        "other": other,
        "sekund": proshlo,
        "v_sekundu": count / proshlo if proshlo else 0,
        "pervyy_429": pervyy_429,
        "retry_after": retry_after,
    }


# --------------------------------------------------------------------------- #
#  Фаза 2. Лестница
# --------------------------------------------------------------------------- #


def run_step(api: ApiSession, do, count: int) -> dict:
    """Одна ступень: count запросов ровным темпом, который держит лимитер."""
    ok = throttled = other = 0
    durations = []
    rate_limit_header = None
    min_remaining = None
    first_429_at = None
    retry_after = None

    for i in range(1, count + 1):
        api.limiter.acquire()
        started = time.monotonic()
        try:
            response = do(api, i)
        except requests.RequestException as e:
            other += 1
            log.warning(f"запрос {i}: сеть — {e.__class__.__name__}")
            continue
        durations.append(time.monotonic() - started)

        limit = response.headers.get("X-RateLimit-Limit")
        remaining = response.headers.get("X-RateLimit-Remaining")
        if limit:
            rate_limit_header = limit
        if remaining is not None:
            try:
                value = int(remaining)
                min_remaining = value if min_remaining is None else min(min_remaining, value)
            except ValueError:
                pass

        if response.status_code == 200:
            ok += 1
        elif response.status_code == 429:
            throttled += 1
            if first_429_at is None:
                first_429_at = i
                retry_after = response.headers.get("Retry-After")
                log.warning(
                    f"429 на запросе {i}; Retry-After={retry_after}; "
                    f"тело: {response.text[:200]}".replace("\n", " ")
                )
        else:
            other += 1
            if other == 1:
                log.warning(
                    f"код {response.status_code} на запросе {i}: "
                    f"{response.text[:200]}".replace("\n", " ")
                )

    return {
        "ok": ok,
        "throttled": throttled,
        "other": other,
        "avg_ms": round(statistics.mean(durations) * 1000) if durations else 0,
        "p95_ms": round(sorted(durations)[int(len(durations) * 0.95) - 1] * 1000)
        if len(durations) >= 2
        else 0,
        "limit_header": rate_limit_header,
        "min_remaining": min_remaining,
        "first_429_at": first_429_at,
        "retry_after": retry_after,
    }


# --------------------------------------------------------------------------- #
#  Фаза 3. Восстановление
# --------------------------------------------------------------------------- #


def faza_vosstanovleniya(api: ApiSession, do, predel: float = 180.0) -> float | None:
    """
    После 429 ждём, пробуя раз в 5 секунд, и засекаем, когда снова пустят.
    Это и есть длина окна, за которое оператор считает квоту.
    """
    nachalo = time.monotonic()
    popytka = 0
    while time.monotonic() - nachalo < predel:
        time.sleep(5)
        popytka += 1
        try:
            response = do(api, popytka)
        except requests.RequestException:
            continue
        if response.status_code == 200:
            return time.monotonic() - nachalo
    return None


# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description="Поиск предельного темпа API операторов")
    parser.add_argument("--operator", choices=sorted(PROBES), required=True)
    parser.add_argument(
        "--method",
        choices=("blocks", "structure"),
        default="blocks",
        help="для МТС: blocks — ProductInfo (так ходит боевой обход), structure — HierarchyStructure",
    )
    parser.add_argument("--max-rpm", type=int, default=300)
    parser.add_argument(
        "--step-requests",
        type=int,
        default=0,
        help="запросов на ступени; по умолчанию равно темпу, то есть ровно минута работы",
    )
    parser.add_argument("--cooldown", type=float, default=65.0)
    parser.add_argument("--no-burst", action="store_true", help="пропустить фазу всплеска")
    args = parser.parse_args()

    title, do = PROBES[args.operator](args.method)
    log.info(f"Проверяю: {title}")
    print(f"\nПроверяю: {title}")

    # ---------------------------------------------------------- фаза всплеска
    posekundnyy = None
    if not args.no_burst:
        print(f"\n[1] Всплеск: {BURST_SIZE} запросов подряд без пауз")
        api = ApiSession(args.operator, RateLimiter(100000), log, adaptive=False, max_retries=0)
        try:
            burst = faza_vsplesk(api, do, BURST_SIZE)
        finally:
            api.close()

        print(
            f"    успешно {burst['ok']}, 429 {burst['throttled']}, прочих {burst['other']}; "
            f"заняло {burst['sekund']:.1f} с ({burst['v_sekundu']:.1f} зап/с)"
        )
        if burst["throttled"]:
            posekundnyy = burst["pervyy_429"]
            print(
                f"    → посекундный лимит есть: первый 429 на запросе {posekundnyy}"
                + (f", Retry-After={burst['retry_after']}" if burst["retry_after"] else "")
            )
            print(f"    жду {args.cooldown:.0f} с перед лестницей")
            time.sleep(args.cooldown)
        else:
            print("    → посекундного лимита не видно, пачка прошла целиком")

    # -------------------------------------------------------------- лестница
    # Чтобы упереться в лимит «N запросов в минуту», надо за минуту отправить
    # больше N запросов. Поэтому на каждой ступени держим темп ровно минуту,
    # а не фиксированные 20-30 запросов: иначе высокие квоты не нащупать.
    stupeni = [r for r in LADDER if r <= args.max_rpm]
    zaprosov = {r: (args.step_requests or r) for r in stupeni}
    ocenka = sum(zaprosov[r] / r * 60 + args.cooldown for r in stupeni) / 60

    print(f"\n[2] Лестница: на каждой ступени держим темп минуту")
    print(f"    всего до {stupeni[-1]} зап/мин — примерно {ocenka:.0f} мин, "
          f"{sum(zaprosov.values())} запросов")
    print(f"{'зап/мин':>8} {'запросов':>9} {'успешно':>8} {'429':>5} {'прочие':>7} {'сред.мс':>8}  заголовки")
    print("-" * 82)

    results = []
    safe_rate = None
    pymal_429 = False
    poslednii_do = None

    for rate in stupeni:
        limiter = RateLimiter(rate_per_min=rate, burst=1)
        api = ApiSession(args.operator, limiter, log, adaptive=False, max_retries=0)
        try:
            step = run_step(api, do, zaprosov[rate])
            poslednii_do = do
        finally:
            api.close()

        step["rate"] = rate
        results.append(step)

        headers_note = ""
        if step["limit_header"]:
            headers_note = f"X-RateLimit-Limit={step['limit_header']}"
            if step["min_remaining"] is not None:
                headers_note += f", мин. остаток={step['min_remaining']}"

        print(
            f"{rate:>8} {zaprosov[rate]:>9} {step['ok']:>8} {step['throttled']:>5} "
            f"{step['other']:>7} {step['avg_ms']:>8}  {headers_note}"
        )

        if step["throttled"]:
            pymal_429 = True
            print(f"\n→ Троттлинг начался на {rate} зап/мин (первый 429 — запрос №{step['first_429_at']}).")
            if step["retry_after"]:
                print(f"  Оператор просит подождать {step['retry_after']} с.")
            break
        if step["other"] > step["ok"]:
            print(f"\n→ На {rate} зап/мин пошли прочие ошибки, останавливаюсь. Смотрите лог.")
            break

        safe_rate = rate
        if rate != stupeni[-1]:
            time.sleep(args.cooldown)

    # --------------------------------------------------------- восстановление
    if pymal_429 and poslednii_do is not None:
        print("\n[3] Жду восстановления, проверяю раз в 5 секунд")
        api = ApiSession(args.operator, RateLimiter(100000), log, adaptive=False, max_retries=0)
        try:
            vosstanovlenie = faza_vosstanovleniya(api, poslednii_do)
        finally:
            api.close()
        if vosstanovlenie:
            print(f"    снова пускает через {vosstanovlenie:.0f} с после первого отказа")
            if vosstanovlenie < 75:
                print("    → окно квоты похоже на минутное")
            else:
                print("    → окно длиннее минуты, учитывайте при расчёте темпа")
        else:
            print("    за 3 минуты не отпустило — окно длинное, выясняйте у оператора")

    # ------------------------------------------------------------------ итог
    print("\n" + "=" * 78)
    if safe_rate:
        recommended = max(1, int(safe_rate * 0.7))
        print(f"Без троттлинга прошло: {safe_rate} зап/мин.")
        print(f"Ставьте с запасом 30 %:  {args.operator.upper()}_RATE_PER_MIN = {recommended}")

        za_progon = ZAPROSOV_ZA_PROGON.get(args.operator)
        if za_progon:
            minut = za_progon / recommended
            chasov = minut / 60
            print(
                f"\nПри {recommended} зап/мин полный обход ({za_progon} запросов) "
                f"займёт {minut:.0f} мин ≈ {chasov:.1f} ч."
            )
            if chasov > 3:
                print("Это долго. Варианты: просить у оператора расширение квоты,")
                print("либо запрашивать блокировки не для всех симок каждый день.")
        log.info(f"{args.operator}: безопасно {safe_rate} зап/мин, рекомендую {recommended}")
    else:
        print("Троттлинг поймали уже на первой ступени — уменьшайте LADDER и пробуйте снова.")

    if posekundnyy:
        print(f"\nПосекундный лимит: пачка упёрлась на {posekundnyy}-м запросе.")
        print("Лимитер в программе выдаёт запросы равномерно, так что в бою это не мешает.")

    if any(r["limit_header"] for r in results):
        print("\nОператор сам сообщает лимит в X-RateLimit-Limit — ориентируйтесь на него.")
    else:
        print("\nЗаголовков X-RateLimit-* в ответах нет, темп держим своим лимитером.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
