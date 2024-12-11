import requests
import json
import sys

from time import sleep

sys.path.append('../')
from sim_operators_work.beeline_logger import logger as log
from sim_operators_work import config as config
from sim_operators_work import help_funcs


class BilineApi:
    def __init__(self, base_url, client_id, client_secret, username, password):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = None

    def get_access_token(self):
        """
        Метод для получения токена доступа
        :return: str
        """
        sleep(1.5)
        log.info(f"Начало обращения к Билайн для получения токена")
        url = f"{self.base_url}/oauth/token"
        data = {
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password"
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            log.info(f"Получен токен доступа от Билайн: {self.access_token}")
        else:
            log.error(f"Ошибка получения токена от Билайн: {response.status_code} - {response.text}")
            raise ValueError('Не получает ТОКЕН Билайн')


    def get_all_sims_pag(self, dashboard_id: str, page):
        """ 
        Метод для получения всех SIM-карт Требуется пагинация
        :param dashboard_id: str
        :param page: int
        :return: dict
        """
        sleep(2)
        log.info(f"Начало обращения к Билайн для получения СИМ")

        url = f"{self.base_url}/api/v0/dashboards/{dashboard_id}/sim_cards/list_all_sim"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest"
        }

        payload = {
             "page": int(page),
             "per_page": 0,
             "order": {
               "id": "desc"
               }
            }

        response = requests.post(url=url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            log.info(f"Получены данные по всем сим страница Билайн - {page} {response.status_code}")
            return response.json()
        else:
            log.error(f"Данные по Билайн не полученны со страницы - {page} {response.status_code}")
            raise ValueError('Не получает ИНФО ПО СИМ Билайн')


    def get_all_services(self, dashboard_id: str):
        """ 
        Выводит все услуги 
        :param dashboard_id: str
        :return: {}
        """
        url = f"{self.base_url}/api/v0/dashboards/{dashboard_id}/communication_plans"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = requests.post(url=url, headers=headers)
        return response.json()
    def get_detail_services_name(self, dashboard_id: str, tarif_name: str):
        """ 
        Выводит услугу по имени 
        :param dashboard_id: str
        :return: {}
        """
        url = f"{self.base_url}/api/v0/dashboards/{dashboard_id}/communication_plans"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest"
        }
        payload = {
                "query": {
                    "name": {
                        "value": f'{tarif_name}',
                        "type": "search"
                        }
                }
        }
        response = requests.post(url=url, headers=headers, data=json.dumps(payload))
        return response.json()

    def get_sim_services_tarif_id(self, dashboard_id: str, communication_plan_id: int):
        """ 
        Отдаёт услуги по communication_plan_id
        :param dashboard_id: str
        :return: {}
        """
        url = f"{self.base_url}/api/v0/dashboards/{dashboard_id}/communication_plans"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest"
        }
        payload = {
                "query": {
                    "id": {
                        "value": int(communication_plan_id),
                        "type": "eq"
                        }
                }
        }
        response = requests.post(url=url, headers=headers, data=json.dumps(payload))
        return response.json()



    def get_sim_tarif_plan_id(self, dashboard_id: str, plan_id: int):
        """ 
        Отдаёт тариф по plan_id
        :param dashboard_id: str
        :return: {}
        """
        url = f"{self.base_url}/api/v0/dashboards/{dashboard_id}/rate_plans"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "XMLHttpRequest"
        }
        payload = {
                "query": {
                    "id": {
                        "value": int(plan_id),
                        "type": "eq"
                        }
                }
        }
        response = requests.post(url=url, headers=headers, data=json.dumps(payload))
        return response.json()

# biline_api = BilineApi(base_url, client_id, client_secret, username, password)
# biline_api.get_access_token()
# all_sims = biline_api.get_all_sims_pag(dashboard_id, page=1200)
# #all_serv = biline_api.get_all_services(dashboard_id)
# #detail_serv_name = biline_api.get_detail_services_name(dashboard_id, "Beeline Russia CSD 20 GRPS LTE")
# #detail_serv_id = biline_api.get_sim_services_tarif_id(dashboard_id, 1842202)
# #detail_tarif = biline_api.get_sim_tarif_plan_id(dashboard_id, 6255)
#
# with open('beeline_all_sims_page_1200.json', 'w', encoding='utf-8') as file:
#     json.dump(all_sims, file, indent=2, ensure_ascii=False)
