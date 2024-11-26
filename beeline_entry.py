from time import sleep
from data_collector import beeline_collector
from database import crud
from logger import logger as log
import config
from help_funcs import beeline_status_convert

def beeline_merge_data():
    base_url = config.BILINE_BASE_URL
    client_id = config.BILINE_CLIENT_ID
    client_secret = config.BILINE_CLIENT_SECRET
    username = config.BILINE_USERNAME
    password = config.BILINE_PASSWORD
    dashboard_id = config.BILINE_DASHBORD
    
    try:
        beeline_class = beeline_collector.BilineApi(base_url, client_id, client_secret, username, password)
        beeline_class.get_access_token()
        first_page = beeline_class.get_all_sims_pag(str(dashboard_id), 0)
    except Exception as e:
        log.error(f"Ошибка получения первой страницы Билайн: {e}")
    else:
        all_pages_num = first_page["data"]["paginator"]["last_page"]

        for i in range(int(all_pages_num) +1):
            try:
                marge_data = {}
                beeline_class.get_access_token()
                beeline_data = beeline_class.get_all_sims_pag(str(dashboard_id), i)["data"]["items"][0]
                marge_data.update({
                        "operator": 3,
                        "owner": 1,
                        "tel_num": beeline_data["sim"]["msisdn"],
                        "iccid": beeline_data["sim"]["iccid"],
                        "status": beeline_status_convert(str(beeline_data["status"])),
                        "block_start": None
                        })
            except Exception as e:
                log.error(f"Ошибка получения страницы {i} Билайн: {e}")
                continue
            else:
                try:
                    log.info("Начало попытки записи Билайн в БД")
                    crud.add_one_sim(marge_data)
                    crud.update_one_sim(marge_data)
                    log.info("Данные успешно записаны Билайн в БД")
                except Exception as e:
                    log.error(f"Ошибка записи Билайн в БД: {e}")

