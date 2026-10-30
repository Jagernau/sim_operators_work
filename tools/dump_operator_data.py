#!/usr/bin/env python3
"""
Выгрузка всего, что отдают API МТС и Билайна, в JSON — чтобы посмотреть,
какие поля есть на самом деле и что из них стоит забирать в базу.

Только чтение. Список методов задан явно ниже, изменяющих вызовов
(change_status, set_rate_plan, set_communication_plan, create, edit, delete,
sms/send) в нём нет и быть не может.

Запуск из папки программы:

    python tools/dump_operator_data.py                    # оба оператора, 3 симки детально
    python tools/dump_operator_data.py --operator beeline --sims 5
    python tools/dump_operator_data.py --operator mts --sims 2

На выходе папка operator_dump_<дата>_<время>/ и рядом такой же .zip —
его и присылайте. В каждом файле: запрос, код ответа, заголовки и тело.

Токены маскируются и в заголовках, и в телах. Остальное сохраняется как есть,
включая MSISDN, ICCID и IMEI — это рабочие данные, смотреть на них и надо.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

import config  # noqa: E402
from api_client import ApiSession, RateLimiter  # noqa: E402
from logging_setup import get_logger  # noqa: E402

log = get_logger("dump_operators")

_SECRET_KEYS = {"access_token", "refresh_token", "client_secret", "password", "authorization"}
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9._~+/\-]{20,}")


# --------------------------------------------------------------------------- #
#  Сохранение
# --------------------------------------------------------------------------- #


def _mask(value):
    """Прячет токены в любой вложенности."""
    if isinstance(value, dict):
        return {
            k: ("…скрыто" if k.lower() in _SECRET_KEYS else _mask(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_mask(v) for v in value]
    if isinstance(value, str):
        return _JWT_RE.sub(lambda m: m.group(0)[:12] + "…скрыто", value)
    return value


class Dumper:
    def __init__(self, out_dir: Path, operator: str):
        self.dir = out_dir / operator
        self.dir.mkdir(parents=True, exist_ok=True)
        self.operator = operator
        self.summary: list[dict] = []

    def save(self, name: str, response, request_note: str = "") -> dict | list | None:
        """Кладёт ответ в файл и возвращает разобранное тело (или None)."""
        try:
            body = response.json()
        except ValueError:
            body = {"_не_json": response.text[:5000]}

        record = {
            "метод": request_note,
            "код": response.status_code,
            "заголовки": _mask(dict(response.headers)),
            "тело": _mask(body),
        }
        path = self.dir / f"{name}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        rate_limit = response.headers.get("X-RateLimit-Limit")
        self.summary.append(
            {
                "файл": f"{self.operator}/{name}.json",
                "метод": request_note,
                "код": response.status_code,
                "X-RateLimit-Limit": rate_limit,
                "X-RateLimit-Remaining": response.headers.get("X-RateLimit-Remaining"),
                "размер_тела": len(response.content),
            }
        )
        status = "ok" if response.status_code == 200 else f"код {response.status_code}"
        limit_note = f", лимит {rate_limit}/мин" if rate_limit else ""
        print(f"  {name:<38} {status}{limit_note}")
        return body if response.status_code == 200 else None

    def skip(self, name: str, reason: str) -> None:
        self.summary.append({"файл": f"{self.operator}/{name}.json", "пропущено": reason})
        print(f"  {name:<38} пропущено: {reason}")

    def fail(self, name: str, error: str, request_note: str = "") -> None:
        """Метод не ответил. Записываем причину и идём дальше — выгрузка не прерывается."""
        record = {"метод": request_note, "ошибка": error}
        (self.dir / f"{name}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.summary.append(
            {"файл": f"{self.operator}/{name}.json", "метод": request_note, "ошибка": error}
        )
        print(f"  {name:<38} ОШИБКА: {error[:60]}")


# --------------------------------------------------------------------------- #
#  МТС
# --------------------------------------------------------------------------- #


def dump_mts(out_dir: Path, sims_limit: int) -> None:
    print("\n=== МТС ===")
    d = Dumper(out_dir, "mts")
    base = str(config.MTS_BASE_URL).rstrip("/")
    api = ApiSession("МТС", RateLimiter(30), log, max_retries=1)

    # ------------------------------------------------------------ токен
    token_response = api.post(
        f"{base}/token",
        auth=(str(config.MTS_USERNAME), str(config.MTS_PASSWORD)),
        data={"grant_type": "client_credentials"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    token_body = d.save("00_token", token_response, "POST /token")
    if not token_body or "access_token" not in str(token_response.text):
        print("  токен не получен, дальше смысла нет")
        return
    token = token_response.json()["access_token"]
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    def get(name: str, url: str, params=None, note: str = ""):
        label = note or url.split("?")[0]
        try:
            return d.save(name, api.get(url, params=params, headers=headers), label)
        except Exception as e:
            d.fail(name, str(e), label)
            return None

    # --------------------------------------------- структура по лицевому счёту
    hierarchy = get(
        "01_hierarchy_account_page0",
        f"{base}/b2b/v1/Service/HierarchyStructure",
        {"account": int(config.MTS_ACCOUNT_NUMBER), "pageNum": 0, "pageSize": 10},
        "GET /b2b/v1/Service/HierarchyStructure?account=…&pageNum=0&pageSize=10",
    )
    # Проверка пагинации. В прошлой выгрузке pageNum=0 и pageNum=1 вернули
    # одни и те же десять номеров — значит нумерация, похоже, начинается с 1.
    # Снимаем страницы 1, 2 и 3, чтобы увидеть, где начинается сдвиг.
    for page in (1, 2, 3):
        get(
            f"02_hierarchy_page{page}",
            f"{base}/b2b/v1/Service/HierarchyStructure",
            {"account": int(config.MTS_ACCOUNT_NUMBER), "pageNum": page, "pageSize": 10},
            f"GET HierarchyStructure, pageNum={page}, pageSize=10",
        )
    # большой pageSize — проверить, принимает ли МТС 100
    get(
        "03_hierarchy_pagesize100",
        f"{base}/b2b/v1/Service/HierarchyStructure",
        {"account": int(config.MTS_ACCOUNT_NUMBER), "pageNum": 0, "pageSize": 100},
        "GET HierarchyStructure, pageSize=100",
    )
    if getattr(config, "MTS_ACCOUNT_NUMBER_SCOUT", None):
        get(
            "04_hierarchy_account_scout",
            f"{base}/b2b/v1/Service/HierarchyStructure",
            {"account": int(config.MTS_ACCOUNT_NUMBER_SCOUT), "pageNum": 0, "pageSize": 10},
            "GET HierarchyStructure, второй лицевой счёт",
        )
    if getattr(config, "MTS_CONTRACT_NUM", None):
        get(
            "05_hierarchy_by_contract",
            f"{base}/b2b/v1/Service/HierarchyStructure",
            {"contract": config.MTS_CONTRACT_NUM},
            "GET HierarchyStructure?contract=…",
        )

    # ------------------------------------------------ вытаскиваем номера и ICCID
    sim_pairs: list[tuple[str, str]] = []
    try:
        relations = hierarchy[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
        for row in relations[:sims_limit]:
            product = row["product"]
            msisdn = str(product["productSerialNumber"])
            iccid = ""
            for ch in product.get("productCharacteristic", []):
                if str(ch.get("name")).upper() in ("SIM", "ICCID"):
                    iccid = str(ch.get("value"))
            sim_pairs.append((msisdn, iccid))
    except (KeyError, IndexError, TypeError) as e:
        print(f"  не разобрал список абонентов: {e}")

    if not sim_pairs:
        d.skip("06_по_номерам", "не из чего брать номера")
        return

    print(f"  детально по {len(sim_pairs)} номерам")

    for i, (msisdn, iccid) in enumerate(sim_pairs, 1):
        tail = f"{i:02d}_{msisdn}"

        get(
            f"10_{tail}_hierarchy_by_msisdn",
            f"{base}/b2b/v1/Service/HierarchyStructure",
            {"msisdn": msisdn},
            "GET HierarchyStructure?msisdn=… (поиск по номеру)",
        )
        if iccid:
            get(
                f"11_{tail}_hierarchy_by_iccid",
                f"{base}/b2b/v1/Service/HierarchyStructure",
                {"sim": iccid},
                "GET HierarchyStructure?sim=… (поиск по ICCID)",
            )
        get(
            f"12_{tail}_product_blocks",
            f"{base}/b2b/v1/Product/ProductInfo",
            {
                "category.name": "MobileConnectivity",
                "marketSegment.characteristic.name": "MSISDN",
                "marketSegment.characteristic.value": msisdn,
                "productOffering.actionAllowed": "none",
                "productOffering.productSpecification.productSpecificationType.name": "block",
                "applyTimeZone": "true",
            },
            "GET ProductInfo … Type.name=block (блокировки)",
        )
        get(
            f"13_{tail}_product_services",
            f"{base}/b2b/v1/Product/ProductInfo",
            {
                "category.name": "MobileConnectivity",
                "marketSegment.characteristic.name": "MSISDN",
                "marketSegment.characteristic.value": msisdn,
                "productOffering.actionAllowed": "none",
                "productOffering.productSpecification.productSpecificationType.name": "service",
                "fields": "CalculatePrices",
            },
            "GET ProductInfo … Type.name=service (услуги со стоимостью)",
        )
        get(
            f"14_{tail}_billplan",
            f"{base}/b2b/v1/Product/BillPlanInfo",
            {
                "productCharacteristic.name": "MSISDN",
                "productCharacteristic.value": msisdn,
                "fields": (
                    "productCharacteristic,place.role,place.externalID,productOffering.name,"
                    "productOffering.href,productOffering.externalID,productOffering.validFor,"
                    "TariffProductWithRegionalTariff"
                ),
                "productLine.name": "MobileConnectivity",
            },
            "GET BillPlanInfo (тарифный план)",
        )
        get(
            f"15_{tail}_location",
            f"{base}/b2b/v1/Service/CurrentSubscriberLocation",
            {"msisdn": msisdn},
            "GET CurrentSubscriberLocation (страна пребывания)",
        )
        get(
            f"16_{tail}_bills_validity",
            f"{base}/b2b/v1/Bills/ValidityInfo",
            {
                "fields": "MOAF",
                "customerAccount.accountNo": msisdn,
                "customerAccount.productRelationship.product.productLine.name": "Counters",
            },
            "GET Bills/ValidityInfo (остатки пакетов)",
        )

    # Блокировки по широкому кругу номеров: нужны коды externalID всех типов,
    # чтобы в программе опираться на код (BL0005), а не на русское название.
    shiroko = [m for m, _ in sim_pairs]
    try:
        relations = hierarchy[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
        shiroko = [r["product"]["productSerialNumber"] for r in relations][:10]
    except (KeyError, IndexError, TypeError):
        pass

    print(f"  блокировки ещё по {len(shiroko)} номерам — собираем коды типов")
    for i, msisdn in enumerate(shiroko, 1):
        get(
            f"18_blocks_{i:02d}_{msisdn}",
            f"{base}/b2b/v1/Product/ProductInfo",
            {
                "category.name": "MobileConnectivity",
                "marketSegment.characteristic.name": "MSISDN",
                "marketSegment.characteristic.value": msisdn,
                "productOffering.actionAllowed": "none",
                "productOffering.productSpecification.productSpecificationType.name": "block",
                "applyTimeZone": "true",
            },
            "GET ProductInfo … Type.name=block",
        )

    # без фильтров — вдруг отдаст справочник целиком
    get("20_all_products", f"{base}/b2b/v1/Product/ProductInfo", None, "GET ProductInfo без фильтров")

    (out_dir / "mts" / "_summary.json").write_text(
        json.dumps(d.summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  {api.stats()}")
    api.close()


# --------------------------------------------------------------------------- #
#  Билайн
# --------------------------------------------------------------------------- #


def dump_beeline(out_dir: Path, sims_limit: int) -> None:
    print("\n=== Билайн ===")
    d = Dumper(out_dir, "beeline")
    base = str(config.BILINE_BASE_URL).rstrip("/")
    dash = str(config.BILINE_DASHBORD)
    api = ApiSession("Билайн", RateLimiter(60), log, max_retries=1)

    token_response = api.post(
        f"{base}/oauth/token",
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
    )
    d.save("00_oauth_token", token_response, "POST /oauth/token")
    if token_response.status_code != 200:
        print("  токен не получен, дальше смысла нет")
        return
    token = token_response.json()["access_token"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Requested-With": "XMLHttpRequest",
    }

    def post(name: str, tail: str, payload: dict | None = None, note: str = ""):
        label = note or f"POST {tail}"
        try:
            return d.save(
                name,
                api.post(f"{base}{tail}", headers=headers, data=json.dumps(payload or {})),
                label,
            )
        except Exception as e:
            d.fail(name, str(e), label)
            return None

    def get(name: str, tail: str, note: str = ""):
        label = note or f"GET {tail}"
        try:
            return d.save(name, api.get(f"{base}{tail}", headers=headers), label)
        except Exception as e:
            d.fail(name, str(e), label)
            return None

    api_dash = f"/api/v0/dashboards/{dash}"

    # --------------------------------------------------------- список SIM
    first = post(
        "01_list_all_sim_perpage5",
        f"{api_dash}/sim_cards/list_all_sim",
        {"page": 1, "perpage": 5, "order": {"id": "asc"}},
        "POST sim_cards/list_all_sim, perpage=5 — смотрим полный состав полей",
    )
    post(
        "02_list_all_sim_perpage200",
        f"{api_dash}/sim_cards/list_all_sim",
        {"page": 1, "perpage": 200, "order": {"id": "asc"}},
        "POST list_all_sim, perpage=200 — принимает ли большой размер страницы",
    )
    post(
        "03_list_all_sim_perpage500",
        f"{api_dash}/sim_cards/list_all_sim",
        {"page": 1, "perpage": 500, "order": {"id": "asc"}},
        "POST list_all_sim, perpage=500 — где потолок",
    )

    # ------------------------------------------------- идентификаторы симок
    sim_ids: list[int] = []
    try:
        for item in (first or {}).get("data", {}).get("items", [])[:sims_limit]:
            if item.get("id"):
                sim_ids.append(int(item["id"]))
    except (AttributeError, TypeError, ValueError) as e:
        print(f"  не разобрал items: {e}")

    if sim_ids:
        print(f"  детально по {len(sim_ids)} симкам: {sim_ids}")
    else:
        d.skip("10_по_симкам", "в списке нет id")

    for i, sid in enumerate(sim_ids, 1):
        tail = f"{i:02d}_{sid}"
        get(f"10_{tail}_sim_card", f"{api_dash}/sim_cards/{sid}", "GET sim_cards/{id} — карточка SIM")
        get(f"11_{tail}_detect_device", f"{api_dash}/sim_cards/{sid}/detect_device", "GET detect_device — IMEI и модель")
        get(f"12_{tail}_last_activity", f"{api_dash}/sim_cards/{sid}/last_activity", "GET last_activity — последнее сетевое событие")
        get(f"13_{tail}_get_balance", f"{api_dash}/sim_cards/{sid}/get_balance", "GET get_balance")
        get(f"14_{tail}_esim", f"{api_dash}/sim_cards/{sid}/esim", "GET esim — EID и статус профиля")
        post(f"15_{tail}_events", f"{api_dash}/sim_cards/{sid}/events", {"page": 1, "perpage": 20, "order": {"id": "desc"}}, "POST sim_cards/{id}/events — события по SIM")
        post(f"16_{tail}_sms_list", f"{api_dash}/sim_cards/{sid}/sms/list", {"page": 1, "perpage": 20, "order": {"id": "desc"}}, "POST sms/list — техсообщения с устройства")
        # update_location инициирует LBS-запрос в сети: тоже чтение, но платное у части тарифов
        get(f"17_{tail}_update_location", f"{api_dash}/sim_cards/{sid}/update_location", "GET update_location — координаты по LBS")

    # ------------------------------------------------------------ справочники
    post("30_rate_plans", f"{api_dash}/rate_plans", {"page": 1, "perpage": 50, "order": {"id": "asc"}}, "POST rate_plans — тарифные планы")
    post("31_communication_plans", f"{api_dash}/communication_plans", {"page": 1, "perpage": 50}, "POST communication_plans — наборы услуг")
    post("32_sim_groups", f"{api_dash}/sim_groups", {"page": 1, "perpage": 50}, "POST sim_groups — группы SIM")
    post("33_zones", f"{api_dash}/zones", {"page": 1, "perpage": 50, "order": {"id": "asc"}}, "POST zones — зоны")
    post("34_custom_fields", f"{api_dash}/custom_fields", {"page": 1, "perpage": 50}, "POST custom_fields — пользовательские поля")
    post("35_events", f"{api_dash}/events", {"page": 1, "perpage": 50, "order": {"id": "desc"}}, "POST events — события дашборда")
    post("36_web_hooks", f"{api_dash}/web_hooks", {"page": 1, "perpage": 50}, "POST web_hooks — текущие подписки")
    post("37_events_subscriptions", f"{api_dash}/events_subscriptions", {"page": 1, "perpage": 50}, "POST events_subscriptions")
    post("38_all_sms", f"{api_dash}/all_sms", {"page": 1, "perpage": 20, "order": {"id": "desc"}}, "POST all_sms — все техсообщения")
    post("39_sms_templates", f"{api_dash}/sms/template/list", {"page": 1, "perpage": 50}, "POST sms/template/list")
    post("40_sms_schedules", f"{api_dash}/sms/schedule/list", {"page": 1, "perpage": 50, "order": {"id": "asc"}}, "POST sms/schedule/list")
    post("41_sms_dispatch", f"{api_dash}/sms/dispatch/list", {"page": 1, "perpage": 20, "order": {"id": "asc"}}, "POST sms/dispatch/list")
    post("42_directions", "/api/v0/dictionaries/directions", {}, "POST dictionaries/directions — направления")

    (out_dir / "beeline" / "_summary.json").write_text(
        json.dumps(d.summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  {api.stats()}")
    api.close()


# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description="Выгрузка ответов API операторов в JSON")
    parser.add_argument("--operator", choices=("mts", "beeline", "both"), default="both")
    parser.add_argument("--sims", type=int, default=3, help="сколько симок обойти детально")
    parser.add_argument("--out", default=None, help="куда класть (по умолчанию рядом с программой)")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = Path(args.out) if args.out else Path(f"operator_dump_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()

    if args.operator in ("mts", "both"):
        try:
            dump_mts(out_dir, args.sims)
        except Exception as e:
            print(f"  МТС: сорвалось — {e}")
            log.error(f"МТС: {e}", exc_info=True)

    if args.operator in ("beeline", "both"):
        try:
            dump_beeline(out_dir, args.sims)
        except Exception as e:
            print(f"  Билайн: сорвалось — {e}")
            log.error(f"Билайн: {e}", exc_info=True)

    archive = shutil.make_archive(str(out_dir), "zip", root_dir=out_dir.parent, base_dir=out_dir.name)
    files = len(list(out_dir.rglob("*.json")))

    print(f"\nГотово за {int(time.monotonic() - started)} с")
    print(f"Файлов: {files}")
    print(f"Папка:  {out_dir.resolve()}")
    print(f"Архив:  {archive}")
    print("\nПрисылайте архив — посмотрю, что из полей стоит забирать в базу.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
