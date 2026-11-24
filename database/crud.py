"""
Работа с таблицей sim_cards.

Что изменилось против прежней версии:

  * движок больше не создаётся в каждой функции (см. db_conectors.py);
  * множество известных ICCID читается ОДИН раз за прогон, а не дважды на каждую
    симку — раньше это был полный SELECT по всей таблице 2 × N раз;
  * add_one_sim + update_one_sim заменены одной upsert_sim с одним commit на симку
    вместо пяти;
  * print() заменены на логгер;
  * в write_off_mts_sim исправлено закрытие сессии — раньше session.close() стоял
    внутри цикла и закрывал сессию на первой итерации;
  * пишутся данные от оператора (operator_imei и прочие) и история смены IMEI.

ВАЖНО: перед первым запуском накатите migrations/001_operator_data.sql и
перегенерируйте модели (python database/generate_models.py) — код ждёт в
models.SimCard новые колонки operator_* и класс models.SimImeiHistory.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import update

import database.mysql_models as models
from database.db_conectors import session_scope, get_session
from logging_setup import get_logger

log = get_logger("db")

# Поля оператора, которые просто перезаписываются без записи в global_logging:
# это телеметрия, а не наши данные, и история по ним копится отдельно.
_OPERATOR_FIELDS = (
    "operator_device_name",
    "operator_last_activity",
    "operator_apn",
    "operator_mcc_mnc",
    "operator_last_ip",
    "operator_blockings",
    "operator_rate_plan",
    "operator_rate_plan_ends",
    "operator_block_code",
    "mts_telematics_100mb",
    "operator_lat",
    "operator_lon",
    "operator_loc_range",
)

# Поля, изменение которых пишется в global_logging: это наши данные о симке,
# а не телеметрия оператора.
_TRACKED_FIELDS = ("sim_imsi",)


# --------------------------------------------------------------------------- #
#  Чтение
# --------------------------------------------------------------------------- #


def load_known_iccids(session) -> dict[str, int]:
    """
    {iccid: sim_id} по всей таблице. Читается один раз за прогон и передаётся
    в upsert_sim — это снимает полный SELECT на каждую симку.
    """
    rows = session.query(models.SimCard.sim_iccid, models.SimCard.sim_id).all()
    return {row[0]: row[1] for row in rows if row[0]}


def all_mts_sim_issid() -> list[str]:
    with session_scope() as session:
        rows = session.query(models.SimCard.sim_iccid).filter(
            models.SimCard.sim_cell_operator == 1
        ).all()
        return [r[0] for r in rows]


def get_all_sim_issid():
    """Оставлено для совместимости. В цикле не вызывать — читает всю таблицу."""
    with session_scope() as session:
        return session.query(models.SimCard.sim_iccid).all()


def get_all_mts():
    with session_scope() as session:
        return session.query(models.SimCard).filter(
            models.SimCard.sim_cell_operator == 1
        ).all()


# --------------------------------------------------------------------------- #
#  Запись
# --------------------------------------------------------------------------- #


def _log_change(session, sim_id: int, field: str, old, new, action: str, operator: int) -> None:
    """Строка в global_logging. Без commit — коммитит вызывающий."""
    session.add(
        models.GlobalLogging(
            section_type="sim_card",
            edit_id=sim_id,
            field=field,
            old_value=str(old)[:255] if old is not None else None,
            new_value=str(new)[:255] if new is not None else None,
            action=action,
            sys_id=operator,
            contragent_id=None,
        )
    )


def _parse_dt(value) -> Optional[datetime]:
    """Принимает datetime, 'YYYY-MM-DD HH:MM:SS', ISO-строку оператора или None."""
    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "").replace("T", " ")
    if "." in text:
        text = text.split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    log.debug(f"не разобрал дату: {value!r}")
    return None


def upsert_sim(session, known_iccids: dict[str, int], data: dict, stat=None) -> Optional[int]:
    """
    Добавляет симку или обновляет изменившиеся поля. Один commit на симку.

    data:
        operator, owner, tel_num, iccid, status, block_start   — как раньше
        operator_imei, operator_device_name, operator_last_activity,
        operator_apn, operator_mcc_mnc, operator_blockings,
        operator_rate_plan, operator_rate_plan_ends            — новые, необязательные

    Возвращает sim_id или None, если записать не удалось.
    """
    iccid = data.get("iccid")
    if not iccid:
        if stat:
            stat.inc("пропущено без ICCID")
        return None

    def bump(key: str) -> None:
        if stat:
            stat.inc(key)

    # ---------------------------------------------------------------- вставка
    if iccid not in known_iccids:
        try:
            sim = models.SimCard(
                sim_cell_operator=data["operator"],
                sim_owner=data["owner"],
                sim_tel_number=data["tel_num"],
                sim_iccid=iccid,
                status=data["status"],
                block_start=_parse_dt(data.get("block_start")),
                block_end=_parse_dt(data.get("block_end")),
            )
            if data.get("sim_imsi"):
                sim.sim_imsi = data["sim_imsi"]
            _apply_operator_fields(sim, data)
            session.add(sim)
            session.flush()                      # получаем sim_id без отдельного SELECT

            _log_change(session, sim.sim_id, "iccid", "0", iccid, "add", data["operator"])
            session.commit()

            known_iccids[iccid] = sim.sim_id
            bump("добавлено")
            return sim.sim_id
        except Exception as e:
            session.rollback()
            log.error(f"не добавил симку {iccid}: {e}")
            bump("ошибок записи")
            return None

    # -------------------------------------------------------------- обновление
    try:
        sim = session.query(models.SimCard).filter(models.SimCard.sim_iccid == iccid).first()
        if sim is None:
            known_iccids.pop(iccid, None)
            bump("ошибок записи")
            return None

        changes: dict = {}
        operator = data["operator"]

        new_tel = data.get("tel_num")
        if new_tel is not None and str(sim.sim_tel_number or "") != str(new_tel):
            _log_change(session, sim.sim_id, "sim_tel_number", sim.sim_tel_number, new_tel, "update", operator)
            changes["sim_tel_number"] = str(new_tel)

        new_status = data.get("status")
        if new_status is not None and sim.status != int(new_status):
            _log_change(session, sim.sim_id, "status", sim.status, int(new_status), "update", operator)
            changes["status"] = int(new_status)

        if sim.sim_cell_operator is not None and int(sim.sim_cell_operator) != int(operator):
            _log_change(session, sim.sim_id, "sim_cell_operator", sim.sim_cell_operator, operator, "update", operator)
            changes["sim_cell_operator"] = operator

        new_block = _parse_dt(data.get("block_start"))
        if sim.block_start != new_block:
            _log_change(session, sim.sim_id, "block_start", sim.block_start, new_block, "update", operator)
            changes["block_start"] = new_block

        if "block_end" in data:
            new_end = _parse_dt(data.get("block_end"))
            if sim.block_end != new_end:
                _log_change(session, sim.sim_id, "block_end", sim.block_end, new_end, "update", operator)
                changes["block_end"] = new_end

        for field in _TRACKED_FIELDS:
            if not data.get(field):
                continue
            if str(getattr(sim, field) or "") != str(data[field]):
                _log_change(session, sim.sim_id, field, getattr(sim, field), data[field], "update", operator)
                changes[field] = data[field]

        # IMEI от оператора — отдельно, со своей историей
        new_imei = data.get("operator_imei")
        if new_imei and str(sim.operator_imei or "") != str(new_imei):
            if sim.operator_imei:
                session.add(
                    models.SimImeiHistory(
                        sim_id=sim.sim_id,
                        sim_iccid=iccid,
                        old_imei=sim.operator_imei,
                        new_imei=new_imei,
                        device_name=data.get("operator_device_name"),
                        source=data.get("source") or str(operator),
                    )
                )
                log.info(
                    f"SIM {iccid}: оператор показывает другой терминал — "
                    f"было {sim.operator_imei}, стало {new_imei}"
                )
                bump("смен IMEI у оператора")
            changes["operator_imei"] = new_imei

        for field in _OPERATOR_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if field.endswith(("_activity", "_ends")):
                value = _parse_dt(value)
            if getattr(sim, field) != value:
                changes[field] = value

        if any(k.startswith("operator_") for k in data):
            changes["operator_sync_at"] = datetime.now()

        if not changes:
            bump("без изменений")
            return sim.sim_id

        session.execute(
            update(models.SimCard).where(models.SimCard.sim_id == sim.sim_id).values(**changes)
        )
        session.commit()
        bump("обновлено")
        return sim.sim_id

    except Exception as e:
        session.rollback()
        log.error(f"не обновил симку {iccid}: {e}")
        bump("ошибок записи")
        return None


def _apply_operator_fields(sim, data: dict) -> None:
    """Проставляет поля оператора на новом объекте SimCard."""
    if data.get("operator_imei"):
        sim.operator_imei = data["operator_imei"]
    for field in _OPERATOR_FIELDS:
        if field in data:
            value = data[field]
            if field.endswith(("_activity", "_ends")):
                value = _parse_dt(value)
            setattr(sim, field, value)
    if any(k.startswith("operator_") for k in data):
        sim.operator_sync_at = datetime.now()


# --------------------------------------------------------------------------- #
#  Списание
# --------------------------------------------------------------------------- #


def write_off_mts_sim(iccids_u_operatora: Iterable[str], stat=None) -> None:
    """
    Симки, которых больше нет у оператора, переводит в статус 0 (списана).

    iccids_u_operatora — ICCID, реально пришедшие от оператора в этом прогоне.
    Вызывать только при ПОЛНОМ обходе: если часть страниц не прочиталась,
    живые симки будут помечены списанными.
    """
    u_operatora = set(str(i) for i in iccids_u_operatora)
    if not u_operatora:
        log.error("списание отменено: от оператора не пришло ни одного ICCID")
        return

    session = get_session()
    try:
        v_baze = session.query(models.SimCard).filter(
            models.SimCard.sim_cell_operator == 1,
            models.SimCard.status != 0,
        ).all()

        spisano = 0
        for sim in v_baze:
            if str(sim.sim_iccid) in u_operatora:
                continue
            try:
                _log_change(session, sim.sim_id, "status", sim.status, 0, "update", 1)
                values = {"status": 0}
                if sim.block_start is not None:
                    _log_change(session, sim.sim_id, "block_start", sim.block_start, None, "update", 1)
                    values["block_start"] = None
                session.execute(
                    update(models.SimCard).where(models.SimCard.sim_id == sim.sim_id).values(**values)
                )
                session.commit()
                spisano += 1
            except Exception as e:
                session.rollback()
                log.error(f"не списал симку {sim.sim_iccid}: {e}")

        if spisano:
            log.info(f"списано симок МТС: {spisano}")
        if stat:
            stat.inc("списано", spisano)
    finally:
        session.close()      # было внутри цикла — закрывалось на первой итерации


# --------------------------------------------------------------------------- #
#  Обслуживание
# --------------------------------------------------------------------------- #


def dubles_sim_clear() -> None:
    """Переносит client_name с обрезанных записей Теле2 на полные."""
    with session_scope() as session:
        cut_all_sims = session.query(models.SimCard).filter(
            models.SimCard.sim_cell_operator == 2,
            models.SimCard.sim_iccid == None,            # noqa: E711
            models.SimCard.contragent_id == None,        # noqa: E711
            models.SimCard.sim_tel_number != None,       # noqa: E711
            models.SimCard.client_name != None,          # noqa: E711
        ).all()

        perenes = 0
        for cut in cut_all_sims:
            full = session.query(models.SimCard).filter(
                models.SimCard.sim_cell_operator == 2,
                models.SimCard.sim_tel_number == cut.sim_tel_number,
                models.SimCard.sim_iccid != None,        # noqa: E711
            ).first()
            if full:
                session.execute(
                    update(models.SimCard)
                    .where(models.SimCard.sim_id == full.sim_id)
                    .values(client_name=cut.client_name)
                )
                perenes += 1
        log.info(f"перенесено имён клиентов: {perenes}")
