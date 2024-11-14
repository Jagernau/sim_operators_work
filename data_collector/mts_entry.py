from time import sleep
import mts_collector

import sys
sys.path.append('../')
from sim_operators_work import config


def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account = config.MTS_ACCOUNT_NUMBER # Номер лицевого счёта

    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
    token = mts_class.get_access_token()
    json_data = []
    page_count = 0
    while True:
        sleep(0.5)
        if mts_class.get_structure_abonents(page_count) != None:
            mts_data = mts_class.get_structure_abonents(page_count)
            marge = {}
            all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
            for i in all_sims:
                tel_num = i["product"]["productSerialNumber"]
                iccid = i["product"]["productCharacteristic"][1]["value"]
                marge["tel_num"] = tel_num
                marge["iccid"] = iccid
#            page_count += 1
            if page_count == 4:
                break
            else:
                page_count += 1
#            if mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] != "hasMore":
                #break
            json_data.append(marge)
    return json_data


print(mts_merge_data())
