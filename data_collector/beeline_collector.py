"""
Клиент API Билайн M2M (Центр Управления M2M).

Главное исправление: в payload списка SIM поле называется perpage, без
подчёркивания. Прежний per_page API не распознавал, применял размер страницы
по умолчанию, а код брал из страницы только items[0] — в базу попадала
одна симка из тридцати.

Дальше — токен берётся один раз (живёт год), темп держит RateLimiter,
sleep() из методов убран, добавлены методы detect_device и last_activity.
"""

from __future__ import annotations

import json
from typing import Iterator, Optional

import config
from api_client import ApiError, ApiSession, RateLimiter, TokenCache
from logging_setup import get_logger

log = get_logger("beeline")

# Сколько запросов в минуту. Билайн отдаёт X-RateLimit-Limit, и ApiSession
# подстраивается под него сам; это стартовое значение до первого ответа.
RATE_PER_MIN = int(getattr(config, "BILINE_RATE_PER_MIN", 0) or 60)

# Размер страницы списка SIM. Живой API это поле игнорирует и всегда отдаёт
# по 30 записей, но передавать его не мешает: обход идёт по last_page из
# пагинатора, так что реальный размер страницы роли не играет.
PAGE_SIZE = int(getattr(config, "BILINE_PAGE_SIZE", 0) or 30)


class BilineApi:
    def __init__(self, base_url, client_id, client_secret, username, password, dashboard_id=None):
        self.base_url = str(base_url).rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.dashboard_id = str(dashboard_id or config.BILINE_DASHBORD)

        self.api = ApiSession("Билайн", RateLimiter(RATE_PER_MIN), log)
        self._tokens = TokenCache(fetch=self._fetch_token)

    # ------------------------------------------------------------------ токен

    def _fetch_token(self) -> tuple[str, int]:
        url = f"{self.base_url}/oauth/token"
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
        }
        response = self.api.post(
            url, headers={"Content-Type": "application/json"}, data=json.dumps(payload)
        )
        if response.status_code != 200:
            raise ApiError(f"Билайн: токен не выдан, {response.status_code} {response.text[:200]}")
        data = response.json()
        log.info("Билайн: токен получен")
        return data["access_token"], int(data.get("expires_in") or 3600)

    @property
    def access_token(self) -> str:
        return self._tokens.token

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest",
        }

    def _dash(self, tail: str) -> str:
        return f"{self.base_url}/api/v0/dashboards/{self.dashboard_id}{tail}"

    def _call(self, method: str, url: str, payload: Optional[dict] = None):
        kwargs = {"headers": self._headers()}
        if payload is not None:
            kwargs["data"] = json.dumps(payload)
        response = self.api.request(method, url, **kwargs)

        if response.status_code == 401:
            # Токен мог протухнуть раньше срока — обновляем и пробуем ещё раз.
            self._tokens.invalidate()
            kwargs["headers"] = self._headers()
            response = self.api.request(method, url, **kwargs)

        if response.status_code != 200:
            raise ApiError(
                f"Билайн: {method} {url.rsplit('/', 2)[-1]} вернул {response.status_code}",
                status=response.status_code,
            )
        return response.json()

    # ------------------------------------------------------------- список SIM

    def get_all_sims_pag(self, page: int, perpage: int | None = None) -> dict:
        """
        Одна страница списка SIM.

        Сортировка по возрастанию id: при desc симки, добавленные во время обхода,
        сдвигают страницы и часть записей проскакивает мимо.
        """
        return self._call(
            "POST",
            self._dash("/sim_cards/list_all_sim"),
            {"page": int(page), "perpage": int(perpage or PAGE_SIZE), "order": {"id": "asc"}},
        )

    def iter_all_sims(self, perpage: int | None = None) -> Iterator[dict]:
        """
        Проходит все страницы и отдаёт симки по одной.
        Отдаёт КАЖДУЮ симку со страницы, а не только первую.

        Сколько записей реально придёт на странице, решает оператор (сейчас 30),
        поэтому ориентируемся на last_page и на фактическую длину items.
        """
        perpage = int(perpage or PAGE_SIZE)
        page = 1
        last_page = None
        total = 0
        otdano = 0

        while True:
            data = self.get_all_sims_pag(page, perpage)
            block = data.get("data") or {}
            items = block.get("items") or []
            paginator = block.get("paginator") or {}

            if last_page is None:
                last_page = int(paginator.get("last_page") or 1)
                total = int(paginator.get("total") or 0)
                fakt = paginator.get("per_page")
                log.info(
                    f"Билайн: страниц {last_page}, всего SIM {total}, "
                    f"на странице {fakt} (просили {perpage})"
                )

            if not items:
                break

            otdano += len(items)
            for item in items:
                yield item

            if page >= last_page:
                break
            page += 1

        if total and otdano < total:
            log.warning(
                f"Билайн: обход дал {otdano} SIM из {total} по данным пагинатора — "
                f"часть страниц не прочиталась"
            )

    # --------------------------------------------------- данные по одной SIM

    def detect_device(self, simcard_id: int) -> dict:
        """
        IMEI и модель устройства, в которое вставлена симка.
        Ответ: {"data": {"sim": {"imei": "...", "device_name": "..."}}, "status": "ok"}
        """
        data = self._call("GET", self._dash(f"/sim_cards/{int(simcard_id)}/detect_device"))
        return ((data.get("data") or {}).get("sim")) or {}

    def last_activity(self, simcard_id: int) -> dict:
        """
        Последнее сетевое событие.
        Ответ: dt, direction_id, channel_id, mobile_network (MCC+MNC), ac_type, ac,
        other_party (APN последней сессии).
        """
        data = self._call("GET", self._dash(f"/sim_cards/{int(simcard_id)}/last_activity"))
        return ((data.get("data") or {}).get("result")) or {}

    def get_balance(self, simcard_id: int):
        data = self._call("GET", self._dash(f"/sim_cards/{int(simcard_id)}/get_balance"))
        return data.get("result")

    def update_location(self, simcard_id: int) -> dict:
        """Координаты по LBS: latitude, longitude, precision (метры), dt."""
        data = self._call("GET", self._dash(f"/sim_cards/{int(simcard_id)}/update_location"))
        return (data.get("data") or {}).get("parameters") or {}

    def sim_sms_list(self, simcard_id: int, page: int = 1, perpage: int = 30) -> list:
        """Техсообщения с устройства — created_at показывает, когда оно последний раз писало."""
        data = self._call(
            "POST",
            self._dash(f"/sim_cards/{int(simcard_id)}/sms/list"),
            {"page": page, "perpage": perpage, "order": {"id": "desc"}},
        )
        return ((data.get("data") or {}).get("items")) or []

    def sim_events(self, simcard_id: int, page: int = 1, perpage: int = 30) -> list:
        data = self._call(
            "POST",
            self._dash(f"/sim_cards/{int(simcard_id)}/events"),
            {"page": page, "perpage": perpage, "order": {"id": "desc"}},
        )
        return ((data.get("data") or {}).get("items")) or []

    # ------------------------------------------------------------- справочники

    def get_all_services(self) -> dict:
        return self._call("POST", self._dash("/communication_plans"), {"page": 1, "perpage": 100})

    def get_sim_tarif_plan_id(self, plan_id: int) -> dict:
        return self._call(
            "POST",
            self._dash("/rate_plans"),
            {"query": {"id": {"value": int(plan_id), "type": "eq"}}},
        )

    def get_detail_services_name(self, tarif_name: str) -> dict:
        return self._call(
            "POST",
            self._dash("/communication_plans"),
            {"query": {"name": {"value": str(tarif_name), "type": "search"}}},
        )

    # ------------------------------------------------------------------ прочее

    def stats(self) -> str:
        return self.api.stats()

    def close(self) -> None:
        self.api.close()
