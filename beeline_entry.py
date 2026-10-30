"""
Сбор данных по SIM Билайна.

Главное по итогам выгрузки живого API 30.10.2026: метод list_all_sim уже
возвращает IMEI устройства, модель, время последней активности, APN, IMSI,
последний IP и координаты по сотовой сети. Отдельный запрос detect_device
на каждую симку не нужен — всё приходит в списке, за 44 запроса на 1295 SIM.

Поле perpage живой API игнорирует и всегда отдаёт по 30 записей, поэтому
размер страницы в настройках ни на что не влияет; обход идёт по last_page
из пагинатора.

detect_device остался доступен через настройку BILINE_DETECT_DEVICE: он даёт
более подробное название модели («SIMCOM Wireless Solutions Co Ltd SIM800C»
вместо «SIMCOM SIM800»), но стоит одного запроса на симку.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import config
from api_client import ApiError, RateLimitedOut
from data_collector import beeline_collector
from database import crud
from database.db_conectors import get_session
from help_funcs import beeline_status_convert
from logging_setup import Stat, get_logger

log = get_logger("beeline")

DETECT_DEVICE = str(getattr(config, "BILINE_DETECT_DEVICE", "") or "0") == "1"
DEVICE_REFRESH_DAYS = int(getattr(config, "BILINE_DEVICE_REFRESH_DAYS", 0) or 7)
DETECT_LIMIT = int(getattr(config, "BILINE_DETECT_LIMIT", 0) or 500)

OPERATOR_ID = 3


def _clean(value) -> str | None:
    """Билайн отдаёт пустые строки вместо null — приводим к None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sim_to_dict(item: dict) -> dict | None:
    """
    Разбирает элемент list_all_sim.

    Вложенный объект sim несёт всё интересное: imei, device_name,
    last_activity_dt, apn, imsi, last_ip. Координаты лежат отдельно,
    в cell_location, и у части симок нулевые.
    """
    sim = item.get("sim") or {}
    iccid = _clean(sim.get("iccid")) or _clean(item.get("iccid"))
    if not iccid:
        return None

    blockings = item.get("blockings") or []
    location = item.get("cell_location") or {}

    latitude = location.get("latitude")
    longitude = location.get("longitude")
    # нулевые координаты означают «местоположение неизвестно», а не точку в Гвинейском заливе
    if not latitude or str(latitude) in ("0", "0.0"):
        latitude = longitude = None

    data = {
        "operator": OPERATOR_ID,
        "owner": 1,
        "source": "beeline",
        "tel_num": _clean(sim.get("msisdn")),
        "iccid": iccid,
        "status": beeline_status_convert(str(item.get("status"))),
        "block_start": None,
        "sim_imsi": _clean(sim.get("imsi")),
        "operator_imei": _clean(sim.get("imei")),
        "operator_device_name": _clean(sim.get("device_name")),
        "operator_last_activity": _clean(sim.get("last_activity_dt")),
        "operator_apn": _clean(sim.get("apn")),
        "operator_last_ip": _clean(sim.get("last_ip")),
        "operator_blockings": ",".join(blockings)[:255] if blockings else None,
        "operator_rate_plan": _clean(item.get("rate_plan_name")),
        "operator_rate_plan_ends": _clean(item.get("rate_plan_ends")),
        "operator_lat": latitude,
        "operator_lon": longitude,
        "operator_loc_range": location.get("range") or None,
    }
    return data


def _nado_utochnit_model(sim_row) -> bool:
    """detect_device дёргаем только ради подробного названия модели."""
    if sim_row is None:
        return False
    if not sim_row.operator_imei:
        return False          # устройства у оператора нет, уточнять нечего
    if not sim_row.operator_device_name:
        return True
    if sim_row.operator_sync_at is None:
        return True
    return sim_row.operator_sync_at < datetime.now() - timedelta(days=DEVICE_REFRESH_DAYS)


def beeline_merge_data() -> None:
    stat = Stat("Билайн", log)
    api = None
    session = None

    try:
        api = beeline_collector.BilineApi(
            config.BILINE_BASE_URL,
            config.BILINE_CLIENT_ID,
            config.BILINE_CLIENT_SECRET,
            config.BILINE_USERNAME,
            config.BILINE_PASSWORD,
            config.BILINE_DASHBORD,
        )

        session = get_session()
        known = crud.load_known_iccids(session)
        log.info(f"Билайн: в базе уже {len(known)} ICCID")

        import database.mysql_models as models

        utochnit: list[tuple[int, str]] = []       # (id симки у оператора, iccid)

        for item in api.iter_all_sims():
            data = _sim_to_dict(item)
            if data is None:
                stat.inc("пропущено без ICCID")
                continue

            if data["status"] is None:
                stat.note(f"неизвестный статус {item.get('status')!r} у {data['iccid']}")
                stat.inc("неизвестный статус")

            if data["operator_imei"]:
                stat.inc("с IMEI от оператора")
            if data["operator_lat"]:
                stat.inc("с координатами")

            sim_id = crud.upsert_sim(session, known, data, stat)
            stat.inc("обработано")
            stat.heartbeat(every=500)

            if DETECT_DEVICE and sim_id and item.get("id") and len(utochnit) < DETECT_LIMIT:
                row = session.query(models.SimCard).filter(
                    models.SimCard.sim_id == sim_id
                ).first()
                if _nado_utochnit_model(row):
                    utochnit.append((int(item["id"]), data["iccid"]))

        # --------------------------------------- уточнение модели устройства
        if utochnit:
            log.info(f"Билайн: уточняю модель устройства по {len(utochnit)} симкам")
            for simcard_id, iccid in utochnit:
                try:
                    device = api.detect_device(simcard_id)
                except RateLimitedOut as e:
                    log.warning(f"Билайн: уточнение моделей остановлено — {e}")
                    stat.inc("уточнение прервано троттлингом")
                    break
                except ApiError as e:
                    stat.inc("ошибок detect_device")
                    log.debug(f"Билайн: {iccid} — {e}")
                    continue

                if not device.get("device_name"):
                    continue

                crud.upsert_sim(
                    session,
                    known,
                    {
                        "operator": OPERATOR_ID,
                        "owner": 1,
                        "source": "beeline",
                        "iccid": iccid,
                        "tel_num": None,
                        "status": None,
                        "operator_imei": device.get("imei"),
                        "operator_device_name": device.get("device_name"),
                    },
                    stat,
                )
                stat.inc("модель уточнена")

        log.info(f"Билайн: {api.stats()}")
        stat.done()

    except Exception as e:
        stat.failed(e)
        raise
    finally:
        if session is not None:
            session.close()
        if api is not None:
            api.close()
