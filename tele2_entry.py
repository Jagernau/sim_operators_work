from data_collector.tele2_collector import TeleTwoParser
from database import crud
import config
import help_funcs
from tele2_logger import logger as log

def tele2_merge_data():
    tel_number = config.TELE_TWO_USERNAME
    password = config.TELE_TWO_PASSWORD
    base_url = config.TELE_TWO_BASE_URL
    user_ip = config.USER_IP

    tele_two_parser = TeleTwoParser(base_url, tel_number, password, user_ip)
    enter_try = tele_two_parser.enter_to_lk_page()
    if enter_try:
        first_page_try =tele_two_parser.go_to_first_abon_page()
        if first_page_try:
            all_phones = []

            all_pages = tele_two_parser.get_info_paginatios_pages()
            if all_pages:
                max_page = help_funcs.get_max_page(all_pages)
                for i in range(max_page):
                    try:
                        pagination_info = tele_two_parser.get_info_paginatios_pages()
                        current_page = help_funcs.get_current_page(pagination_info)
                        if current_page == max_page:
                            # остановить цикл

                            phones_from_page = tele_two_parser.get_phones_from_page()
                            all_phones.append({'page':current_page, 'phones':phones_from_page})
                            break
                        else:
                            phones_from_page = tele_two_parser.get_phones_from_page()
                            all_phones.append({'page':current_page, 'phones':phones_from_page})
                            tele_two_parser.go_next_page()
                    except Exception as e:
                        continue

            if len(all_phones) >= 1:
                for i in all_phones:
                    page = i['page']
                    phones = i['phones']
                    for phone in phones:
                        # если телефон не пустой ''
                        if phone != 'Номерабонента' and phone != None and phone !="":
                           detail_info = tele_two_parser.go_detail_page_get_info(phone)
                           if detail_info == None:
                               continue
                           log.info(f"Обработанна страница {page}, Телефон {phone}")
                           if detail_info['iccid'] and detail_info['status']:
                               marge_data = {}
                               marge_data.update({
                                        "operator": 2,
                                        "owner": 1,
                                        "tel_num": phone,
                                        "iccid": str(detail_info['iccid']).replace("ID SIM-карты: ", '')[:-1],
                                        "status": help_funcs.tele2_status_convert(str(detail_info['status'])),
                                        "block_start": None
                                        })
                               if marge_data["iccid"] != None and marge_data["status"] != None:
                                    try:
                                        crud.add_one_sim(marge_data)
                                        crud.update_one_sim(marge_data)
                                        log.info("Данные успешно записаны Теле2 в БД")
                                    except Exception as e:
                                        log.error(f"Ошибка записи Теле2 в БД: {e}")

