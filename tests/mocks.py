"""
Поддельные API операторов для тестов.

Поднимают настоящий HTTP-сервер на localhost, поэтому проверяется и работа
requests, и заголовки, и коды ответов — а не только наши функции.

Режимы задаются через поле mode у хендлера:
    "ok"        нормальные ответы
    "429"       всегда троттлинг с Retry-After
    "500"       всегда ошибка сервера
    "404"       всегда не найдено (быстрый путь: не ретраится)
    "flaky"     первые N запросов 429, дальше нормально
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class MockState:
    """Общее состояние мока: счётчики вызовов и режим."""

    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self.calls: dict[str, int] = {}
        self.payloads: list[dict] = []
        self.perpage_seen: list[int] = []
        self.flaky_left = 0
        self.rate_limit_header: str | None = None
        self.sims_total = 10
        self.pages_total = 1
        self.sim_page_size = 30

    def count(self, key: str) -> int:
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.calls[key]

    def get(self, key: str) -> int:
        return self.calls.get(key, 0)


class _Base(BaseHTTPRequestHandler):
    state: MockState = None  # подставляется фабрикой

    def _send(self, obj, code=200, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        if self.state.rate_limit_header:
            self.send_header("X-RateLimit-Limit", self.state.rate_limit_header)
            self.send_header("X-RateLimit-Remaining", "500")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_payload(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}
        self.state.payloads.append(payload)
        return payload

    def _maybe_fail(self) -> bool:
        """Возвращает True, если ответ уже отправлен из-за режима."""
        mode = self.state.mode
        if mode == "429":
            self._send({"errorCode": 1011, "message": "too many requests"}, 429, {"Retry-After": "1"})
            return True
        if mode == "500":
            self._send({"message": "server error"}, 500)
            return True
        if mode == "404":
            self._send({"message": "not found"}, 404)
            return True
        if mode == "flaky" and self.state.flaky_left > 0:
            self.state.flaky_left -= 1
            self._send({"errorCode": 1011}, 429, {"Retry-After": "1"})
            return True
        return False

    def log_message(self, *args):
        pass


class MtsHandler(_Base):
    """Поддельный МТС Бизнес API."""

    def do_POST(self):
        if self.path.startswith("/token"):
            self.state.count("token")
            if self.state.mode == "token_fail":
                return self._send({"message": "bad credentials"}, 401)
            return self._send(
                {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.mts-secret-value.sig",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "default",
                }
            )
        self._send({}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if "HierarchyStructure" in parsed.path:
            self.state.count("structure")
            if self._maybe_fail():
                return

            page = int(query.get("pageNum", ["0"])[0])
            size = int(query.get("pageSize", ["10"])[0])
            self.state.perpage_seen.append(size)

            # Живой МТС: pageNum=0 и pageNum=1 отдают одну и ту же первую
            # страницу, дальше идёт нормальный сдвиг. Нумерация с единицы.
            start = (max(1, page) - 1) * size
            if start >= self.state.sims_total:
                return self._send(
                    [{"partyRole": [{"customerAccount": [{"productRelationship": [], "href": "end"}]}]}]
                )

            relations = []
            for i in range(start, min(start + size, self.state.sims_total)):
                relations.append(
                    {
                        "relationshipType": "child",
                        "product": {
                            "description": "Нижегородская область",
                            "productSerialNumber": f"7910000{i:04d}",
                            "productCharacteristic": [
                                {"name": "IMSI", "value": f"25001870338{i:04d}"},
                                {"name": "SIM", "value": f"897010116870{i:07d}0"},
                            ],
                        },
                    }
                )
            href = "hasMore" if start + size < self.state.sims_total else "end"
            return self._send(
                [
                    {
                        "name": "ООО Сантел сервис",
                        "partyRole": [
                            {
                                "id": "857199510",
                                "customerAccount": [
                                    {"accountNo": "252303159685", "href": href, "productRelationship": relations}
                                ],
                            }
                        ],
                    }
                ]
            )

        if "ProductInfo" in parsed.path:
            self.state.count("blocks")
            if self._maybe_fail():
                return
            msisdn = query.get("marketSegment.characteristic.value", [""])[0]
            # Коды сняты с живого ответа: BL0005 — добровольная, BL0008 — первоначальная.
            if msisdn.endswith(("2", "5", "8")):
                return self._send([self._block("BL0005", "Добровольная блокировка")])
            if msisdn.endswith(("3", "6")):
                return self._send([self._block("BL0008", "Первоначальная блокировка")])
            return self._send([])

    @staticmethod
    def _block(code: str, name: str) -> dict:
        return {
            "externalID": code,
            "name": name,
            "status": "ACTIVE",
            "actionAllowed": ["NONE"],
            "validFor": {
                "startDateTime": "2026-09-15T12:43:44+03:00",
                "endDateTime": "0001-01-01T00:00:00+03:00",
            },
            "productSpecification": {"name": "Block"},
            "product": [
                {
                    "externalID": "13166600789",
                    "productCharacteristic": [
                        {"name": "IsActivated", "value": "true"},
                        {"name": "IsBlocked", "value": "false"},
                    ],
                }
            ],
        }

        if "BillPlanInfo" in parsed.path:
            self.state.count("billplan")
            return self._send([{"productOffering": {"name": "М2М Старт"}}])

        if "CurrentSubscriberLocation" in parsed.path:
            self.state.count("location")
            return self._send({"country": "RU"})

        self._send({}, 404)


class BeelineHandler(_Base):
    """Поддельный Билайн M2M API."""

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = self._read_payload()

        if parsed.path == "/oauth/token":
            self.state.count("token")
            if self.state.mode == "token_fail":
                return self._send({"message": "bad credentials"}, 401)
            return self._send(
                {
                    "token_type": "Bearer",
                    "expires_in": 31536000,
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.bee-secret-value.sig",
                    "refresh_token": "def502004ff8bc7ffb23b76154e83eac",
                }
            )

        if parsed.path.endswith("/sim_cards/list_all_sim"):
            self.state.count("list_all_sim")
            if self._maybe_fail():
                return
            if self.state.mode == "needs_auth" and self.state.get("list_all_sim") == 1:
                return self._send({"message": "Unauthenticated"}, 401)

            # Живой Билайн поле perpage игнорирует и всегда отдаёт по 30.
            # Запрошенное значение запоминаем, но размер страницы берём свой.
            self.state.perpage_seen.append(payload.get("perpage"))
            size = self.state.sim_page_size

            page = int(payload.get("page") or 1)
            total = self.state.sims_total
            last_page = max(1, (total + size - 1) // size)
            start = (page - 1) * size

            items = []
            for i in range(start, min(start + size, total)):
                # Структура снята с живого ответа 30.10.2026: imei, device_name,
                # last_activity_dt, apn и координаты приходят прямо в списке.
                pustaya = i % 5 == 0          # каждая пятая — списанная, без устройства
                items.append(
                    {
                        "id": 4021634 + i,
                        "name": "",
                        "status": "purged" if pustaya else "activated",
                        "type": "regular",
                        "contract_id": 100221902,
                        "activated_at": "" if pustaya else "2022-08-04 05:27:12",
                        "attached_at": "2022-08-04 05:27:12",
                        "rate_plan_ends": "",
                        "created_at": "2022-08-04 05:27:12",
                        "rate_plan_id": None if pustaya else 6255,
                        "rate_plan_name": "" if pustaya else "M2M 30 MB%_SANTEHL",
                        "blockings": [] if pustaya else (["blocking_platform"] if i % 7 == 0 else []),
                        "processings": [],
                        "esia_state": True,
                        "sim": {
                            "id": 4021634 + i,
                            "imsi": f"25099028341{i:04d}",
                            "iccid": f"897019917073006{i:04d}",      # ровно 19 знаков
                            "apn": "" if pustaya else "m2m.beeline.ru",
                            "imei": "" if pustaya else f"86779303618{i:04d}",
                            "msisdn": f"7089936{i:04d}",
                            "unisim_id": "",
                            "device_name": "" if pustaya else "SIMCOM SIM800",
                            "device_type": 3,
                            "device_options": ["2g", "sms", "voice", "csd"],
                            "pdp_context": False,
                            "communication_plan_id": None,
                            "communication_plan_name": "",
                            "last_ip": "" if pustaya else "10.219.211.53",
                            "sim_ip": "",
                            "last_activity_dt": "" if pustaya else "2024-11-02 11:51:35",
                            "stationarity_class": 0,
                        },
                        "custom_fields": [],
                        "counters": [],
                        "online_counters": [],
                        "quote_names": [],
                        "profile_apns": [],
                        "group_names": [],
                        "control_name": "",
                        "cell_location": (
                            {"latitude": 0, "longitude": 0, "range": 0}
                            if pustaya
                            else {"latitude": "56.146108", "longitude": "44.331631", "range": 225}
                        ),
                    }
                )
            return self._send(
                {
                    "data": {
                        "items": items,
                        "paginator": {
                            "current_page": page,
                            "from": start + 1,
                            "last_page": last_page,
                            "per_page": size,
                            "to": start + len(items),
                            "total": total,
                        },
                    },
                    "status": "ok",
                }
            )

        self.state.count("other_post")
        if self._maybe_fail():
            return
        self._send({"data": {"items": [], "paginator": {"current_page": 1, "last_page": 1, "total": 0}}, "status": "ok"})

    def do_GET(self):
        path = urlparse(self.path).path

        if path.endswith("/detect_device"):
            self.state.count("detect_device")
            if self._maybe_fail():
                return
            return self._send(
                {"data": {"sim": {"imei": "990018947099424", "device_name": "XIAOMI Redmi 10A"}}, "status": "ok"}
            )

        if path.endswith("/last_activity"):
            self.state.count("last_activity")
            if self._maybe_fail():
                return
            return self._send(
                {
                    "data": {
                        "result": {
                            "dt": "2026-10-29T12:00:00Z",
                            "direction_id": 200,
                            "channel_id": 8,
                            "mobile_network": "25099",
                            "ac_type": 0,
                            "ac": 0,
                            "other_party": "m2m.beeline.ru",
                        }
                    },
                    "status": "ok",
                }
            )

        if path.endswith("/get_balance"):
            self.state.count("get_balance")
            return self._send({"result": 123.45})

        if path.endswith("/update_location"):
            self.state.count("update_location")
            return self._send(
                {
                    "data": {
                        "date": "2026-10-29T12:00:00Z",
                        "parameters": {
                            "dt": "2026-10-29T09:31:43",
                            "latitude": "56.3269",
                            "longitude": "44.0059",
                            "precision": "385",
                        },
                    },
                    "status": "ok",
                }
            )

        if path.endswith("/esim"):
            self.state.count("esim")
            return self._send({"message": "not an esim"}, 404)

        self.state.count("other_get")
        if self._maybe_fail():
            return
        self._send({"status": "ok"})


def start_mock(handler_cls, state: MockState) -> tuple[HTTPServer, str]:
    """
    Поднимает сервер на свободном порту, возвращает (сервер, базовый URL).
    Останавливать через server.shutdown().
    """
    handler = type(handler_cls.__name__ + "Bound", (handler_cls,), {"state": state})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
