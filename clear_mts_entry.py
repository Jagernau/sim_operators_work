from time import sleep
from data_collector import mts_collector
from database import crud
from help_funcs import mts_status_convert
from mts_logger import logger as log
import config

def get_block_status(mts_class, tel_num):
    "Получение статуса сим МТС"
    block_status = None
    try:
        log.info("Начало получения статуса сим MTS")
        block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
        log.info("Cтатус сим MTS успешно получен")
    except Exception as e:
        log.error(f"Ошибка при получении статуса: {e}")
        try:
            token = mts_class.get_access_token()
            log.error(f"Повторная попытка получения токена {token}")
            block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
            log.error("Повторная попытка получения блокировок сим успешно прошла")
        except Exception as e:
            log.error(f"Ошибка при повторной попытке получения блокировок: {e}")
    finally:
        return block_status

def process_sim_data(mts_class, all_sims):
    iccids_len = []
    for i in all_sims:
        marge = {}
        tel_num = i["product"]["productSerialNumber"]
        iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]
        iccids_len.append(iccid)

        block_status = get_block_status(mts_class, tel_num)
        if block_status == None:
            marge.update({
                "operator": 1,
                "owner": 1,
                "tel_num": tel_num,
                "iccid": iccid,
                'status': 4,
                "block_start": None
            })

        else:
            clear_block_status = 1 if len(block_status) == 0 else mts_status_convert(block_status[0]["name"])
            
            marge.update({
                "operator": 1,
                "owner": 1,
                "tel_num": tel_num,
                "iccid": iccid,
                'status': clear_block_status,
                "block_start": str(str(block_status[0]['validFor']["startDateTime"]).split("T")[0]) + " 00:00:00" if clear_block_status != 1 else None
            })

        try:
            log.info("Начало попытки записи в БД")
            crud.add_one_sim(marge)
            crud.update_one_sim(marge)
            log.info("Данные успешно записаны в БД")
        except Exception as e:
            log.error(f"Ошибка записи в БД: {e}")

    return iccids_len


def write_off(full_all_accounts_data: list):
    all_iccids_set = []
    check_none = []
    for account_data in full_all_accounts_data:
        if None not in account_data:
            for page in account_data:
                for val in page:
                    all_iccids_set.append(val)
        if None in account_data:
            check_none.append(None)

                    
    log.info(len(all_iccids_set))
    try:
        if None not in check_none and len(all_iccids_set) >= 1:
            crud.write_off_mts_sim(all_iccids_set)
    
    except Exception as e:
        log.error(f"Не удаётся изменить данные по списанию сим в БД {e}")

def get_mts_pages(account):
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
    page_count = 0
    sim_mts_pages = []
    
    while True:
        try:
            mts_class.get_access_token()
            mts_data = mts_class.get_structure_abonents(page_count)
            all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
            pages_data = process_sim_data(mts_class, all_sims)
            sim_mts_pages.append(pages_data)
            page_count += 1
        except Exception as e:
            log.error(f"Не удаётся получить данные с МТС в итерации цикла: {e}")
            sim_mts_pages.append(None)
            continue
        else:
            try:
                next_page = mts_data[0]["partyRole"][0]["customerAccount"][0]["href"]
            except Exception as e:
                log.error(f"Ошибка получения HREF значит страницы закончились: {e}")
                break
            else:
                if next_page != "hasMore":
                    log.error("Нет данных в текущей странице, похоже что эта страница последняя")
                    break

    return sim_mts_pages



def mts_merge_data():
    accounts = [
            config.MTS_ACCOUNT_NUMBER, 
            config.MTS_ACCOUNT_NUMBER_SCOUT
            ]
    all_sim_mts_pages = []

    for account in accounts:
        all_sim_mts_pages.append(get_mts_pages(account))

    write_off(all_sim_mts_pages)

