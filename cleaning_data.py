
#from database import crud
# from datetime import datetime
#
# start = datetime.now()
#data = crud.get_all_mts()
# end = datetime.now()
#
# for i in data:
#     print(i.block_start)

#
# from time import sleep
# from data_collector import mts_collector
# from database import crud
# from help_funcs import mts_status_convert
# from mts_logger import logger as log
# import config
# import json
#
#
# base_url = config.MTS_BASE_URL
# username = config.MTS_USERNAME
# password = config.MTS_PASSWORD
# account_parent = config.MTS_ACCOUNT_NUMBER
# account_scout = config.MTS_ACCOUNT_NUMBER_SCOUT
#
# mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account_parent)
# mts_class.get_access_token()
# data = mts_class.get_structure_abonents(0)
# with open("all_sim_11_12.json", 'w', encoding='utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=2)
