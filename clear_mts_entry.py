from time import sleep
from data_collector import mts_collector
from database import crud
from help_funcs import mts_status_convert
from logger import logger as log
import config

def get_block_status(mts_class, tel_num):
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
            return None
    return block_status

def process_sim_data(mts_class, all_sims):
    json_data = []
    for i in all_sims:
        marge = {}
        tel_num = i["product"]["productSerialNumber"]
        iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]

        block_status = get_block_status(mts_class, tel_num)
        if block_status is None:
            continue

        clear_block_status = 1 if len(block_status) == 0 else mts_status_convert(block_status[0]["name"])
        
        marge.update({
            "operator": 1,
            "owner": 1,
            "tel_num": tel_num,
            "iccid": iccid,
            'status': clear_block_status,
            "block_start": block_status[0]['validFor']["startDateTime"] if clear_block_status != 1 else None
        })

        try:
            log.info("Начало попытки записи в БД")
            crud.add_one_sim(marge)
            crud.update_one_sim(marge)
            log.info("Данные успешно записаны в БД")
        except Exception as e:
            log.error(f"Ошибка записи в БД: {e}")

        json_data.append(marge)

    return json_data

def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account_parent = config.MTS_ACCOUNT_NUMBER
    account_scout = config.MTS_ACCOUNT_NUMBER_SCOUT

    for account in [account_parent, account_scout]:
        mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
        page_count = 0
        
        while True:
            try:
                mts_class.get_access_token()
                mts_data = mts_class.get_structure_abonents(page_count)
                if not mts_data or not mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] == "hasMore":
                    log.error("Нет данных в текущей странице, переход на следующую")
                    break
                
                all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
                process_sim_data(mts_class, all_sims)
                page_count += 1
            
            except Exception as e:
                log.error(f"Не удаётся получить данные с МТС в итерации цикла: {e}")
                page_count += 1

