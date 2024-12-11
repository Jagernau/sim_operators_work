from time import sleep
import requests
import json

import sys

sys.path.append('../')
from sim_operators_work.mts_logger import logger as log

class MtsApi:
    def __init__(self, base_url, username, password, accountNo):
        """ 
        При инициализации принимает:
        1 Базовый адрес
        2 Логин в АПИ ЛК
        3 Пароль в АПИ ЛК
        4 Номер лицевого счёта
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.accountNo = accountNo
        self.access_token = None

    def get_access_token(self):
        sleep(2)
        log.info(f"Начало обращения к МТС для получения токена")

        url = f"{self.base_url}/token"
        auth = (f"{self.username}", f"{self.password}")
        data = {
            "grant_type": "client_credentials"
        }
        response = requests.post(url, auth=auth, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            log.info(f"Получен токен доступа от МТС: {self.access_token}")
        else:
            log.error(f"Ошибка получения токена от МТС: {response.status_code} - {response.text}")
            raise ValueError('Не получает ТОКЕН')


    def get_structure_abonents(self, pageNum: int): # Получение симок
        """ 
        Метод для получения структуры абонентов
        Принимает:
        1 Номер лицевого счёта self
        2 Номер страницы
        По умолчанию поставил количество результатов на странице: 10 
        :return: dict

        """
        sleep(2)
        log.info(f"Начало обращения к МТС для получения СИМ")

        url = f"{self.base_url}/b2b/v1/Service/HierarchyStructure?account={int(self.accountNo)}&pageNum={int(pageNum)}&pageSize=10"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            log.info(f"Получены данные по всем сим страница - {pageNum} {response.status_code}")
            return response.json()
        else:
            log.error(f"Данные по МТС не полученны со страницы - {pageNum} {response.status_code}")
            raise ValueError('Не получает ИНФО ПО СИМ')


    def get_detail_internet_from_tel_number(self, tel_number): # Полный хаос не понятно
        """ 
        Метод предназначен для получения информации об остатках пакетов минут, интернет, SMS.
        Принимает:
        1 Номер телефона
        """
        url = f"{self.base_url}/b2b/v1/Bills/ValidityInfo?fields=MOAF&customerAccount.accountNo={tel_number}&customerAccount.productRelationship.product.productLine.name=Counters"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        return response.json()


    def get_detail_service_from_tel_number(self, tel_number):
        """ 
        Запрос списка подключенных услуг с указанием стоимости
        Принимает:
        1 Номер телефона
        """
        sleep(2)
        url = f"{self.base_url}/b2b/v1/Product/ProductInfo?category.name=MobileConnectivity&marketSegment.characteristic.name=MSISDN&marketSegment.characteristic.value={tel_number}&productOffering.actionAllowed=none&productOffering.productSpecification.productSpecificationType.name=service&fields=CalculatePrices&applyTimeZone"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            log.info(f"Получены статусы услуг {response.status_code}")
            return response.json()
        else:
            log.error(f"Данные по услугам МТС не полученны {response.status_code}")
            raise ValueError('Не получает услуги')



    def get_detail_blocks_from_tel_number(self, tel_number):
        """ 
        Запрос списка блокировок с
        Принимает:
        1 Номер телефона
        """
        sleep(2)

        log.info(f"Начало получения детализации по блокировкам сим {tel_number}")

        url = f"{self.base_url}/b2b/v1/Product/ProductInfo?category.name=MobileConnectivity&marketSegment.characteristic.name=MSISDN&marketSegment.characteristic.value={tel_number}&productOffering.actionAllowed=none&productOffering.productSpecification.productSpecificationType.name=block&applyTimeZone=true"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            log.info(f"Конец получения детализации по блокировкам сим {tel_number}")
            return response.json()
        else:

            log.error(f"Не получены блокировки по СИМ {tel_number} ---- {response.status_code} ---- {response.text}")
            raise ValueError('Не получает СТАТУСЫ')


    def get_top_tarif_from_tel_number(self, tel_number):
        """ 
        Отдаёт Информацию о действующем тарифном плане
        Принимает:
        1 Номер телефона
        """
        url = f"{self.base_url}/b2b/v1/Product/BillPlanInfo?productCharacteristic.name=MSISDN&productCharacteristic.value={tel_number}&fields=productCharacteristic,place.role,place.externalID,productOffering.name,productOffering.href,productOffering.externalID,productOffering.validFor,TariffProductWithRegionalTariff&productLine.name=MobileConnectivity"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        return response.json()

    def get_detail_location_from_tel_number(self, tel_number):
        """ 
        Определение страны пребывания абонента
        Принимает:
        1 Номер телефона
        """
        url = f"{self.base_url}/b2b/v1/Service/CurrentSubscriberLocation?msisdn={tel_number}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        return response.json()

    def get_all_services(self):
        """ 
        Информация по всем услугам
        """
        url = f"{self.base_url}/b2b/v1/Product/ProductInfo"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        response = requests.get(url=url, headers=headers)
        return response.text




# mts_api = MtsApi(base_url, username, password, accountNo="")
# mts_api.get_access_token()
# # # #all_sims = mts_api.get_all_sims(parent_tel_number)
# structure_abonents = mts_api.get_structure_abonents(pageNum=1)
# # #
# detail_service = mts_api.get_detail_service_from_tel_number("79159357944")
# # # #detail_internet = mts_api.get_detail_internet_from_tel_number("79108933613")
# # # detail_blocks = mts_api.get_detail_blocks_from_tel_number("79867505908")
# # # #detail_location = mts_api.get_detail_location_from_tel_number()
# # # #top_tarif = mts_api.get_top_tarif_from_tel_number("79101313428")
# # # #get_all_services = mts_api.get_all_services()
#
# result = {i["name"] for i in detail_service}
# print(result)
# #
# with open('mts_all_abon_1_page_scout.json', 'w', encoding='utf-8') as file:
#     json.dump(structure_abonents, file, indent=2, ensure_ascii=False)


