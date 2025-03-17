
# from database import crud
# from datetime import datetime
# #
# start = datetime.now()
# crud.dubles_sim_clear()
# end = datetime.now()
# print(end - start)
#
# for i in data:
#     print(i.block_start)

#
from data_collector import mts_collector
import config
import json


base_url = config.MTS_BASE_URL
username = config.MTS_USERNAME
password = config.MTS_PASSWORD
account_parent = config.MTS_ACCOUNT_NUMBER
account_scout = config.MTS_ACCOUNT_NUMBER_SCOUT

mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account_parent)
mts_class.get_access_token()
# block_detail = mts_class.get_detail_blocks_from_tel_number(79108938162)
# print(block_detail)
data = mts_class.get_structure_abonents(1)
with open("all_sim_03_17_1.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
