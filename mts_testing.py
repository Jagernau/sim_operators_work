from time import sleep
from data_collector import mts_collector
from database import crud
from help_funcs import mts_status_convert
from mts_logger import logger as log
import config
import json


def mts_merge_data():
    base_url = config.MTS_BASE_URL
    username = config.MTS_USERNAME
    password = config.MTS_PASSWORD
    account_parent = config.MTS_ACCOUNT_CLOUD
    contract_num = config.MTS_CONTRACT_NUM

    mts_class = mts_collector.MtsApi(base_url, username, password, accountNo=account_parent)
        
    mts_class.get_access_token()
    mts_data = mts_class.get_from_contract_structure_abonents(contract_num)
    return mts_data

