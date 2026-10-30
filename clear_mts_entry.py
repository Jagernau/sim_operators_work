"""
Сбор данных по SIM МТС.

Главное исправление: в прежней версии цикл обхода страниц при ошибке делал
continue, не увеличив page_count. Любая устойчивая ошибка — троттлинг, сеть,
протухший токен — и программа крутилась вечно на одной странице, записывая
строку в лог каждые несколько секунд и наращивая список в памяти.

Теперь: три неудачи подряд на одной странице — обход прерывается, списание
не выполняется (неполные данные нельзя принимать за «симки пропали у оператора»).
"""

from __future__ import annotations

import config
from api_client import ApiError, RateLimitedOut
from data_collector import mts_collector
from database import crud
from database.db_conectors import get_session
from help_funcs import mts_status_convert
from logging_setup import Stat, get_logger

log = get_logger("mts")

OPERATOR_ID = 1
MAX_FAILS_PODRYAD = 3


# Коды типов блокировок МТС, снятые с живого API 30.10.2026.
# Сопоставляем по коду, а не по названию: название МТС может изменить,
# и тогда статус молча станет «неизвестен».
BLOCK_CODES = {
    "BL0005": 2,      # Добровольная блокировка
    "BL0008": 3,      # Первоначальная блокировка
}

# Заглушка «бессрочно» в поле endDateTime
PUSTAYA_DATA = "0001-01-01"


def _mts_dt(raw) -> str | None:
    """
    '2026-05-12T12:43:44+03:00' -> '2026-05-12 12:43:44'.
    Время сохраняем целиком: раньше оно отбрасывалось до полуночи.
    """
    if not raw:
        return None
    text = str(raw).strip()
    if text.startswith(PUSTAYA_DATA):
        return None
    text = text.split("+")[0].split("Z")[0].replace("T", " ").strip()
    return text[:19] or None


def _blocks_to_status(block_status) -> tuple[int, str | None, str | None, str | None]:
    """
    Из ответа по блокировкам делает (status, block_start, block_end, код блокировки).

    None на входе означает «не смогли узнать» — это статус 4, а не «активна»:
    принять сбой запроса за снятую блокировку опаснее, чем признать незнание.
    """
    if block_status is None:
        return 4, None, None, None
    if len(block_status) == 0:
        return 1, None, None, None

    block = block_status[0]
    code = block.get("externalID")
    status = BLOCK_CODES.get(code)

    if status is None:
        # код незнакомый — пробуем по названию, как раньше
        status = mts_status_convert(block.get("name"))
    if status is None:
        return 4, None, None, code

    period = block.get("validFor") or {}
    return status, _mts_dt(period.get("startDateTime")), _mts_dt(period.get("endDateTime")), code


def _get_block_status(api: mts_collector.MtsApi, tel_num, stat: Stat):
    """Блокировки по номеру. None означает «не смогли узнать»."""
    try:
        return api.get_detail_blocks_from_tel_number(str(tel_num))
    except RateLimitedOut:
        raise
    except ApiError as e:
        stat.inc("ошибок запроса блокировок")
        log.debug(f"МТС: блокировки {tel_num} — {e}")
        return None


def _process_page(api, session, known, all_sims, stat: Stat) -> list[str]:
    """Обрабатывает симки одной страницы, возвращает их ICCID."""
    iccids: list[str] = []

    for row in all_sims:
        try:
            product = row["product"]
            tel_num = product["productSerialNumber"]
            # productCharacteristic = [{IMSI}, {SIM}]. Ищем по имени, а не по
            # индексу: порядок полей оператор не обещает.
            harakteristiki = {
                str(c.get("name")).upper(): c.get("value")
                for c in product.get("productCharacteristic") or []
            }
            sim_raw = harakteristiki.get("SIM") or harakteristiki.get("ICCID")
            imsi = harakteristiki.get("IMSI")
            # ICCID приходит двадцатизначным, последний символ — контрольная
            # цифра. В базе ICCID хранится без неё, обрезка намеренная.
            iccid = str(sim_raw)[:-1]
        except (KeyError, IndexError, TypeError) as e:
            stat.inc("не разобрал запись")
            log.debug(f"МТС: не разобрал запись — {e}")
            continue

        if not sim_raw:
            stat.inc("не разобрал запись")
            continue

        iccids.append(iccid)

        block_status = _get_block_status(api, tel_num, stat)
        status, block_start, block_end, block_code = _blocks_to_status(block_status)

        if block_code and block_code not in BLOCK_CODES:
            stat.note(f"незнакомый код блокировки {block_code} у {tel_num}")
            stat.inc("незнакомых кодов блокировок")

        crud.upsert_sim(
            session,
            known,
            {
                "operator": OPERATOR_ID,
                "owner": 1,
                "source": "mts",
                "tel_num": tel_num,
                "iccid": iccid,
                "status": status,
                "block_start": block_start,
                "block_end": block_end,
                "operator_block_code": block_code,
                "sim_imsi": imsi,
            },
            stat,
        )
        stat.inc("обработано")
        stat.heartbeat(every=500)

    return iccids


def get_mts_pages(account, session, known, stat: Stat) -> tuple[list[str], bool]:
    """
    Полный обход страниц одного лицевого счёта.
    Возвращает (список ICCID, обход завершён целиком).
    """
    api = mts_collector.MtsApi(
        config.MTS_BASE_URL, config.MTS_USERNAME, config.MTS_PASSWORD, accountNo=account
    )
    iccids: list[str] = []
    # Нумерация страниц у МТС начинается с единицы: pageNum=0 и pageNum=1
    # возвращают одну и ту же первую страницу (проверено на живом API
    # 30.10.2026). Старт с нуля означал лишний проход по первой сотне.
    page = 1
    fails = 0
    polnyy_obhod = False

    try:
        while True:
            try:
                data = api.get_structure_abonents(page)
                all_sims = data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
            except RateLimitedOut as e:
                log.error(f"МТС: счёт {account} — троттлинг не кончается, прерываю ({e})")
                break
            except (ApiError, KeyError, IndexError, TypeError) as e:
                fails += 1
                if fails >= MAX_FAILS_PODRYAD:
                    log.error(
                        f"МТС: счёт {account}, страница {page} не даётся "
                        f"{MAX_FAILS_PODRYAD} раза подряд ({e}), прерываю обход"
                    )
                    break
                log.warning(f"МТС: счёт {account}, страница {page} — попытка {fails}: {e}")
                continue

            fails = 0

            if not all_sims:
                polnyy_obhod = True
                break

            iccids.extend(_process_page(api, session, known, all_sims, stat))

            try:
                next_page = data[0]["partyRole"][0]["customerAccount"][0]["href"]
            except (KeyError, IndexError, TypeError):
                polnyy_obhod = True
                break

            if next_page != "hasMore":
                polnyy_obhod = True
                break

            page += 1

        log.info(f"МТС: счёт {account} — страниц {page}, SIM {len(iccids)}; {api.stats()}")
    finally:
        api.close()

    return iccids, polnyy_obhod


def mts_merge_data() -> None:
    stat = Stat("МТС", log)
    session = None

    accounts = [config.MTS_ACCOUNT_NUMBER, config.MTS_ACCOUNT_NUMBER_SCOUT]

    try:
        session = get_session()
        known = crud.load_known_iccids(session)
        log.info(f"МТС: в базе уже {len(known)} ICCID")

        vse_iccid: list[str] = []
        vse_scheta_proshli = True

        for account in accounts:
            iccids, polnyy = get_mts_pages(account, session, known, stat)
            vse_iccid.extend(iccids)
            if not polnyy:
                vse_scheta_proshli = False
                stat.note(f"счёт {account} прочитан не полностью")

        # Списываем только когда ВСЕ счета прочитаны целиком: иначе живые симки
        # будут помечены как исчезнувшие у оператора.
        if vse_scheta_proshli and vse_iccid:
            crud.write_off_mts_sim(vse_iccid, stat)
        else:
            log.warning(
                "МТС: списание пропущено — обход неполный "
                f"(счетов прочитано целиком: {vse_scheta_proshli}, ICCID собрано: {len(vse_iccid)})"
            )
            stat.inc("списание пропущено")

        stat.done()

    except Exception as e:
        stat.failed(e)
        raise
    finally:
        if session is not None:
            session.close()
