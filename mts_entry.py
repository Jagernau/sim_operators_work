from time import sleep

from data_collector import mts_collector

import config
from database import crud
from help_funcs import mts_status_convert

from logger import logger as log 

def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account = config.MTS_ACCOUNT_NUMBER # Номер лицевого счёта

    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
    json_data = []
    page_count = 0

    
    while True:
        sleep(1.8)
        try:
            mts_class.get_access_token()
            mts_data = mts_class.get_structure_abonents(page_count)
        except Exception as e:
            log.error(f"Не удаётся получить данные с МТС в итерации цикла {e}")
            page_count += 1
            continue
        else:
            mts_data = mts_data if mts_data != None else None
            if mts_data != None:
                if mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] == "hasMore":            
                    all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
                    for i in all_sims:
                        marge = {}
                        tel_num = i["product"]["productSerialNumber"]
                        iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]
                        # если нет блокировки - то пусто
                        try:
                            log.info("Начало получения статуса сим MTS")
                            block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
                            log.info("Cтатус сим MTS успешно получен")

                        except Exception as e:
                            log.error(f"В обработке получения статуса сим MTS возникла ошибка {e}")
                            continue
                        else:
                            if len(block_status) == 0:
                                block_status = 1
                            else:
                                block_status = mts_status_convert(block_status[0]["name"])

                            marge["operator"] = 1
                            marge["owner"] = 1
                            marge["tel_num"] = tel_num
                            marge["iccid"] = iccid
                            marge['status'] = block_status

                            try:
                                log.info(f"Начало попытки записи в БД")
                                crud.add_one_sim(marge)
                                log.info(f"Данные успешно записанны в БД")

                            except Exception as e:
                                log.error(f"Данные в БД не записались, возникла ошибка {e}")

                            json_data.append(marge)

                    page_count += 1

                else:
                    all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
                    for i in all_sims:
                        marge = {}
                        tel_num = i["product"]["productSerialNumber"]
                        iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]
                        # если нет блокировки - то пусто
                        try:
                            log.info("Начало получения статуса сим MTS")
                            block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
                            log.info("Cтатус сим MTS успешно получен")

                        except Exception as e:
                            log.error(f"В обработке получения статуса сим MTS возникла ошибка {e}")
                            continue
                        else:
                            if len(block_status) == 0:
                                block_status = 1
                            else:
                                block_status = mts_status_convert(block_status[0]["name"])

                            marge["operator"] = 1
                            marge["owner"] = 1
                            marge["tel_num"] = tel_num
                            marge["iccid"] = iccid
                            marge['status'] = block_status

                            try:
                                log.info(f"Начало попытки записи в БД")
                                crud.add_one_sim(marge)
                                log.info(f"Данные успешно записанны в БД")

                            except Exception as e:
                                log.error(f"Данные в БД не записались, возникла ошибка {e}")

                            json_data.append(marge)

                    break
            else:
                log.error("НЕТ данных в текущей странице, переход на следующюю")
                continue

#    return json_data


