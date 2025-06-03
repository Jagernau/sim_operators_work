import clear_mts_entry
import beeline_entry
import tele2_entry
import schedule
import time
from mts_logger import logger as mts_log 
from beeline_logger import logger as beeline_log 
from tele2_logger import logger as tele2_logger 
import multiprocessing

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

def process_tele2():
    try:
        tele2_logger.info("Начало потока Теле2")
        tele2_entry.tele2_merge_data()
        tele2_logger.info("Конец потока Теле2")
    except Exception as e:
        tele2_logger.error(f"В обработке потока Теле2 возникла ошибка {e}")

def job():
    mts_thread = multiprocessing.Process(target=process_mts)
    beeline_thread = multiprocessing.Process(target=process_beeline)
    tele2_thread = multiprocessing.Process(target=process_tele2)

    mts_thread.start()
    beeline_thread.start()
    tele2_thread.start()

    mts_thread.join()
    beeline_thread.join()
    tele2_thread.join()



if __name__ == '__main__':
    # Запланировать выполнение job() каждый день в 10:30
    schedule.every().day.at("10:30").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
