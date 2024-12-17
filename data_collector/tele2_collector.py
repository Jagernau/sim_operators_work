from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
import random
import sys
sys.path.append('../')
from sim_operators_work.tele2_logger import logger as log

class TeleTwoParser:
    """ 
    Класс для парсинга данных сайта tele2
    Для получения данных симкарт
    """
    def __init__(self, base_url, username, password, user_ip):
        """
        При инициализации принимает:
        1 Базовый адрес
        2 Логин
        3 Пароль
        Инициализируется браузер Chrome по удаленному серверу
        """
        self.base_url = base_url
        self.username = str(username) # номер телефона
        self.password = password
        self.options = Options()
        # CrossBrowser подключение к удаленному серверу
        self.browser = webdriver.Remote(
            command_executor=f"http://{user_ip}:4444/wd/hub",
            options=self.options
        )
        self.password_enter_button = "//*[@id='portal']/div/div[2]/div/label[2]" # кнопка входа по паролю
        self.admine_phone_fields = "//*[@id='phoneNumber__']" # поле ввода номера телефона
        self.password_field = "//input[@name='password' and @type='password' and @data-element='Password']"
        self.enter_button = "//*[@id='portal']/div/div[2]/form/div[2]/button[1]"

    def close_browser(self):
        """
        Метод для закрытия браузера
        """
        time.sleep(random.randint(2, 5))
        self.browser.quit()

    def enter_to_lk_page(self):
        """
        Метод для входа в личный кабинет
        """
        try:
            self.browser.get(self.base_url)
            log.info(f"Получена Главная страница")
            time.sleep(random.randint(10, 20))
            # Нажатие кнопки входа по паролю
            password_button = self.browser.find_element(By.XPATH, self.password_enter_button)
            time.sleep(random.uniform(1.3, 1.9))
            password_button.click()
            time.sleep(random.randint(2, 5))
        except Exception as ex:
            log.error(f"Кнопка входа по паролю не нажата: {ex}")
            self.browser.quit()
            return False
        else:
            try:
                for i in range(len(self.username)):
                #Ввод номера телефона
                    phone_field = self.browser.find_element(By.XPATH, str(self.admine_phone_fields).replace("__", f"{i}"))
                    time.sleep(random.uniform(1.2, 1.8))
                    phone_field.send_keys(self.username[i])
                    time.sleep(random.randint(1, 3))
            except Exception as ex:
                log.error(f"Поле ввода номера телефона не заполнено: {ex}")
                self.browser.quit()
                return False
            else:
                try:
                    # Ввод пароля
                    password_field = self.browser.find_element(By.XPATH, self.password_field)
                    time.sleep(random.uniform(1.2, 2.7))
                    password_field.send_keys(self.password)
                    time.sleep(random.randint(1, 2))
                except Exception as ex:
                    log.error(f"Поле ввода пароля не заполнено: {ex}")
                    self.browser.quit()
                    return True
                else:
                    try:
                        # Нажатие кнопки входа
                        login_button = self.browser.find_element(By.XPATH, self.enter_button)
                        login_button.click()
                        time.sleep(random.randint(10, 20))
                    except Exception as ex:
                        log.error(f"Кнопка входа не нажата: {ex}")
                        self.browser.quit()
                        return False
                    else:
                        return True

    def go_to_first_abon_page(self):
        """
        Метод для перехода на первую страницу абонентов
        """
        try:
            time.sleep(random.randint(10, 15))
            self.browser.get(f"{str(self.base_url).replace('/lk', '')}/subscribers")
            time.sleep(random.randint(10, 15))
        except Exception as ex:
            log.error(f"Перейти на первую страницу абонентов не получилось: {ex}")
            return False
        else:
            return True


    def get_info_paginatios_pages(self):
        """
        Метод для получения страниц пагинации
        Отдаёт словарь с информацией о страницах:
        {
            "pagingPrevLink", или "pagingNextLink", или "pagingLinkPageЧисло": {
                "text": "Числи", или "<<", или ">>"
                "class": "curent", или "disabled", или " "
            }
        }

        """
        # Поиск элемента с классом "paging-links"
        try:
            paging_links_element = self.browser.find_element(By.CSS_SELECTOR, "span.paging__links")
        except Exception as ex:
            log.error(f"Не удалось найти элемент с пагинацией: {ex}")
            return None
        else:
            try:
                # Получение всех элементов пагинации
                pagination_elements = paging_links_element.find_elements(By.TAG_NAME, "a")
                pages = {}

                # Вывод информации о каждом элементе пагинации
                for pagination_element in pagination_elements:
                    element_id = pagination_element.get_attribute("id")
                    element_text = pagination_element.text
                    element_class = pagination_element.get_attribute("class")

                    pages[element_id] = {
                        "text": element_text,
                        "class": element_class
                    }
            except Exception as ex:
                log.error(f"Не удалось найти элемент страницы: {ex}")
                return None
            else:
                return pages

    def go_next_page(self):
        """
        Метод для перехода на следующую страницу
        """
        try:
            time.sleep(random.randint(4, 7))
            next_page = self.browser.find_element(By.XPATH, "//*[@id='pagingNextLink']")
            next_page.click()
            log.info(f"Перешли на следующую страницу")
            time.sleep(random.randint(4, 7))
        except Exception as ex:
            log.error(f"Перейти на следующую страницу не получилось: {ex}")
            return False
        else:
            return True

    def get_phones_from_page(self):
        """
        Метод для получения номеров абонентов
        Отдаёт список с номерами абонентов
        """
        try:
            time.sleep(random.randint(4, 7))
            msisdn_elements = self.browser.find_elements(By.CSS_SELECTOR, "div.subscriber-list__msisdn")

            phones = []

            for msisdn_element in msisdn_elements:
                
                phones.append(str(msisdn_element.text).replace(" ", "").replace("+", "").replace("-",""))
            return phones
        except Exception as ex:
            log.error(f"Получить номера абонентов не получилось: {ex}")
            return None


    def go_detail_page_get_info(self, tel_number):
        """
        Метод для перехода на страницу абонента
        и вытаскивания информации:
        1 Статус
        2 Iccid
        Принимает:
        1 Номер телефона
        Отдаёт словарь с информацией:
        {
            "status": "Статус",
            "iccid": "Iccid"
        }
        """
        try:
            time.sleep(random.randint(5, 10))
            self.browser.get(f"{str(self.base_url).replace('/lk', '')}/subscribers/{tel_number}")
            time.sleep(random.randint(5, 10))
        except Exception as ex:
            log.error(f"Перейти на страницу абонента {tel_number} не получилось: {ex}")
            return None
        else:
            try:
                status_element = self.browser.find_element(By.CSS_SELECTOR, "span.subscriber-profile-slot__status")
                iccid_element = self.browser.find_element(By.CSS_SELECTOR, "span.subscriber-profile-slot__sim")
            except Exception as ex:
                log.error(f"Получить  об элементах {tel_number} не получилось: {ex}")
                return None
            else:
                return {
                    "status": status_element.text,
                    "iccid": iccid_element.text
                }

