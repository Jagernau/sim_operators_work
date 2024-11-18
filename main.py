import mts_entry

import schedule
import time
from logger import logger as log 

def job():

    # MTS
    try:
        log.info("Начало обработки MTS")

        mts_entry.mts_merge_data()

        log.info("Конец обработки MTS")
    except Exception as e:
        log.error(f"В обработке MTS возникла ошибка {e}")


if __name__ == '__main__':

    schedule.every().day.at("23:40").do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
