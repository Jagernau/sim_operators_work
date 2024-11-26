

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
