import threading
import schedule
import time
import clear_mts_entry
import beeline_entry
from logger import logger as log 

def process_mts():
    try:
        log.info("Начало обработки MTS")
        clear_mts_entry.mts_merge_data()
        log.info("Конец обработки MTS")
    except Exception as e:
        log.error(f"В обработке MTS возникла ошибка {e}")

def process_beeline():
    try:
        log.info("Начало обработки Beeline")
        beeline_entry.beeline_merge_data()
        log.info("Конец обработки Beeline")
    except Exception as e:
        log.error(f"В обработке Beeline возникла ошибка {e}")

def job():
    mts_thread = threading.Thread(target=process_mts)
    beeline_thread = threading.Thread(target=process_beeline)

    mts_thread.start()
    beeline_thread.start()

    mts_thread.join()
    beeline_thread.join()

if __name__ == '__main__':
    # Запланировать выполнение job() каждый день в 23:40
    schedule.every().day.at("23:40").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)

