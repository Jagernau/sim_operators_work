"""
Клиент МТС Бизнес API.

Что изменилось:
  * токен берётся один раз и живёт свои 3600 секунд (раньше запрашивался
    на каждой странице обхода);
  * значение токена больше не пишется в лог;
  * sleep(2) из каждого метода убран — темп держит RateLimiter, который
    умеет разбирать 429 (errorCode 1011 «too many requests»);
  * у всех запросов есть таймаут;
  * размер страницы вынесен в настройку: pageSize=10 означал отдельный
    запрос структуры на каждые 10 симок.

Лимиты МТС публично не опубликованы и зависят от подключённого пакета.
Подобрать можно скриптом tools/measure_api_limits.py.
"""

from __future__ import annotations

from typing import Optional

import config
from api_client import ApiError, ApiSession, RateLimiter, TokenCache
from logging_setup import get_logger

log = get_logger("mts")

RATE_PER_MIN = int(getattr(config, "MTS_RATE_PER_MIN", 0) or 30)
PAGE_SIZE = int(getattr(config, "MTS_PAGE_SIZE", 0) or 100)


class MtsApi:
    def __init__(self, base_url, username, password, accountNo):
        self.base_url = str(base_url).rstrip("/")
        self.username = username
        self.password = password
        self.accountNo = accountNo

        self.api = ApiSession("МТС", RateLimiter(RATE_PER_MIN), log)
        self._tokens = TokenCache(fetch=self._fetch_token)

    # ------------------------------------------------------------------ токен

    def _fetch_token(self) -> tuple[str, int]:
        response = self.api.post(
            f"{self.base_url}/token",
            auth=(str(self.username), str(self.password)),
            data={"grant_type": "client_credentials"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            raise ApiError(
                f"МТС: токен не выдан, {response.status_code} {response.text[:200]}",
                status=response.status_code,
            )
        data = response.json()
        ttl = int(data.get("expires_in") or 3600)
        log.info(f"МТС: токен получен, живёт {ttl} с")
        return data["access_token"], ttl

    @property
    def access_token(self) -> str:
        return self._tokens.token

    def get_access_token(self) -> str:
        """Оставлено для совместимости со старым кодом. Лишних запросов не делает."""
        return self.access_token

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def _get(self, url: str, params: Optional[dict] = None, what: str = "запрос"):
        response = self.api.get(url, params=params, headers=self._headers())

        if response.status_code == 401:
            # errorCode 1013 «token expired» — обновляем токен и повторяем один раз
            self._tokens.invalidate()
            response = self.api.get(url, params=params, headers=self._headers())

        if response.status_code != 200:
            raise ApiError(
                f"МТС: {what} вернул {response.status_code} {response.text[:200]}",
                status=response.status_code,
            )
        return response.json()

    # ------------------------------------------------------------- структура

    def get_structure_abonents(self, pageNum: int, pageSize: int | None = None):
        """
        Страница списка абонентов по лицевому счёту.

        pageSize берётся из модуля в момент вызова, а не фиксируется в сигнатуре:
        значение дефолтного аргумента вычисляется один раз при импорте, и
        настройка из .env до метода тогда не доходит.
        """
        size = int(pageSize or PAGE_SIZE)
        return self._get(
            f"{self.base_url}/b2b/v1/Service/HierarchyStructure",
            {"account": int(self.accountNo), "pageNum": int(pageNum), "pageSize": size},
            what=f"структура, страница {pageNum}",
        )

    def get_from_contract_structure_abonents(self, contractNum: int):
        """Лицевые счета по номеру договора."""
        return self._get(
            f"{self.base_url}/b2b/v1/Service/HierarchyStructure",
            {"contract": contractNum},
            what="структура по договору",
        )

    def get_by_iccid(self, iccid: str):
        """Точечный поиск по ICCID — удобно для сверки одной симки."""
        return self._get(
            f"{self.base_url}/b2b/v1/Service/HierarchyStructure",
            {"sim": str(iccid)},
            what=f"поиск по ICCID {iccid}",
        )

    def get_by_msisdn(self, msisdn: str):
        return self._get(
            f"{self.base_url}/b2b/v1/Service/HierarchyStructure",
            {"msisdn": str(msisdn)},
            what=f"поиск по номеру {msisdn}",
        )

    # -------------------------------------------------------- данные по номеру

    def get_detail_blocks_from_tel_number(self, tel_number):
        """Блокировки по номеру."""
        url = (
            f"{self.base_url}/b2b/v1/Product/ProductInfo"
            "?category.name=MobileConnectivity"
            "&marketSegment.characteristic.name=MSISDN"
            f"&marketSegment.characteristic.value={tel_number}"
            "&productOffering.actionAllowed=none"
            "&productOffering.productSpecification.productSpecificationType.name=block"
            "&applyTimeZone=true"
        )
        return self._get(url, what=f"блокировки {tel_number}")

    def get_detail_service_from_tel_number(self, tel_number):
        """Подключённые услуги со стоимостью."""
        url = (
            f"{self.base_url}/b2b/v1/Product/ProductInfo"
            "?category.name=MobileConnectivity"
            "&marketSegment.characteristic.name=MSISDN"
            f"&marketSegment.characteristic.value={tel_number}"
            "&productOffering.actionAllowed=none"
            "&productOffering.productSpecification.productSpecificationType.name=service"
            "&fields=CalculatePrices&applyTimeZone"
        )
        return self._get(url, what=f"услуги {tel_number}")

    def get_top_tarif_from_tel_number(self, tel_number):
        """Действующий тарифный план."""
        url = (
            f"{self.base_url}/b2b/v1/Product/BillPlanInfo"
            "?productCharacteristic.name=MSISDN"
            f"&productCharacteristic.value={tel_number}"
            "&fields=productCharacteristic,place.role,place.externalID,productOffering.name,"
            "productOffering.href,productOffering.externalID,productOffering.validFor,"
            "TariffProductWithRegionalTariff&productLine.name=MobileConnectivity"
        )
        return self._get(url, what=f"тариф {tel_number}")

    def get_detail_location_from_tel_number(self, tel_number):
        """Страна пребывания абонента — видно роуминг."""
        return self._get(
            f"{self.base_url}/b2b/v1/Service/CurrentSubscriberLocation",
            {"msisdn": tel_number},
            what=f"локация {tel_number}",
        )

    # ------------------------------------------------------------------ прочее

    def stats(self) -> str:
        return self.api.stats()

    def close(self) -> None:
        self.api.close()
