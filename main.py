import clear_mts_entry
import beeline_entry
import schedule
import time
from mts_logger import logger as mts_log 
from beeline_logger import logger as beeline_log 
import threading

def process_mts():
    try:
        mts_log.info("Начала потока MTS")
        clear_mts_entry.mts_merge_data()
        mts_log.info("Конец потока MTS")
    except Exception as e:
        mts_log.error(f"В обработке потока MTS возникла ошибка {e}")

def process_beeline():
    try:
        beeline_log.info("Начало потока Beeline")
        beeline_entry.beeline_merge_data()
        beeline_log.info("Конец потока Beeline")
    except Exception as e:
        beeline_log.error(f"В обработке потока Beeline возникла ошибка {e}")

def job():
    mts_thread = threading.Thread(target=process_mts)
    beeline_thread = threading.Thread(target=process_beeline)

    mts_thread.start()
    beeline_thread.start()

    mts_thread.join()
    beeline_thread.join()

if __name__ == '__main__':
    # Запланировать выполнение job() каждый день в 23:40
    schedule.every().day.at("18:40").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
