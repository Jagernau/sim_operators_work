from time import sleep
from data_collector import mts_collector

import config
from database import crud


def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account = config.MTS_ACCOUNT_NUMBER # Номер лицевого счёта

    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account)
    token = mts_class.get_access_token()
    json_data = []
    page_count = 0
    unic_db_iccid = {item[0] for item in crud.get_all_sim_issid()}

    def get_marge_data(page):
        if mts_class.get_structure_abonents(page_count) != None:
            mts_data = mts_class.get_structure_abonents(page_count)
            marge = {}
            all_sims = mts_data[0]["partyRole"][0]["customerAccount"][0]["productRelationship"]
            for i in all_sims:
                tel_num = i["product"]["productSerialNumber"]
                iccid = str(i["product"]["productCharacteristic"][1]["value"])[:-1]

                marge["operator"] = 1
                marge["tel_num"] = tel_num
                marge["iccid"] = iccid
            return marge
        else:
            return None

    while True:
        sleep(0.5)
        marge_data = get_marge_data(page_count)
        page_count += 1

        if page_count == 4:
            break
#            if mts_data[0]["partyRole"][0]["customerAccount"][0]["href"] != "hasMore":
                #marge_data = get_marge_data(page_count)
                #break
        json_data.append(marge_data)
    return unic_db_iccid


print(mts_merge_data())