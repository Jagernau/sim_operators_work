
def mts_status_convert(text):
    if text == "Добровольная блокировка":
        return 2
    if text == "Первоначальная блокировка":
        return 3

def beeline_status_convert(text):
    if text == "purged":
        return 0
    if text == "activated":
        return 1
    if text == "deactivated":
        return 2
    if text == "activation_ready":
        return 3

def get_current_page(data: dict):
    """
    Метод для получения текущей страницы
    :param data: dict
    :return: int
    """
    for key, value in data.items():
        if value['class'] == 'current':
            return int(value['text'])

def get_max_page(data: dict):
    """
    Метод для получения максимальной страницы
    :param data: dict
    :return: int
    """
    max_page = 0
    for key, value in data.items():
        if value['text'].isdigit():
            if int(value['text']) > max_page:
                max_page = int(value['text'])
    return max_page


def tele2_status_convert(text):
    if text == "Заблокирован":
        return 0
    elif text == "Активен":
        return 1
    elif text == "Приостановлен":
        return 2
    elif text == "Не активирован":
        return 3
    else:
        return None

