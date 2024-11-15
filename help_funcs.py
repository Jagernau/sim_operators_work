

def mts_status_convert(text):
    if text == "Добровольная блокировка":
        return 2
    if text == "Первоначальная блокировка":
        return 3
