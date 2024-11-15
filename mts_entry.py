from time import sleep

from sqlalchemy.orm.decl_api import re
from data_collector import mts_collector

import config
from database import crud
from help_funcs import mts_status_convert


def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account = config.MTS_ACCOUNT_NUMBER # Номер лицевого счёта

    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
    json_data = []
    page_count = 0

    
    while True:
        sleep(1)
        mts_class.get_access_token()
        mts_data = mts_class.get_structure_abonents(page_count) if mts_class.get_structure_abonents(page_count) != None else None
        if mts_data != None:
            if mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] == "hasMore":            
                all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
                for i in all_sims:
                    marge = {}
                    tel_num = i["product"]["productSerialNumber"]
                    iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]
                    # если нет блокировки - то пусто
                    block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
                    if len(block_status) == 0:
                        block_status = 1
                    else:
                        block_status = mts_status_convert(block_status[0]["name"])

                    marge["operator"] = 1
                    marge["owner"] = 1
                    marge["tel_num"] = tel_num
                    marge["iccid"] = iccid
                    marge['status'] = block_status

                    crud.add_one_sim(marge)

                    json_data.append(marge)

                page_count += 1


            if mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] != "hasMore":

                all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
                for i in all_sims:
                    marge = {}
                    tel_num = i["product"]["productSerialNumber"]
                    iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]
                    # если нет блокировки - то пусто
                    block_status = mts_class.get_detail_blocks_from_tel_number(str(tel_num))
                    if len(block_status) == 0:
                        block_status = 1
                    else:
                        block_status = mts_status_convert(block_status[0]["name"])

                    marge["operator"] = 1
                    marge["owner"] = 1
                    marge["tel_num"] = tel_num
                    marge["iccid"] = iccid
                    marge['status'] = block_status

                    crud.add_one_sim(marge)

                    json_data.append(marge)
                break
        else:
            break

#    return json_data


