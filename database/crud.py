from os.path import join
import database.mysql_models as models
from database.db_conectors import MysqlDatabase
from sqlalchemy import func, or_, and_
from sqlalchemy import case

def get_all_sim_issid():
    db = MysqlDatabase()
    session = db.session
    result = session.query(
            models.SimCard.sim_iccid
            ).all()
    session.close()
    return result

def add_one_sim(marge_data):
    """
    Рекрусивно проверяет бд, 
    если нет такой сим в бд как у оператора, 
    добавляет его в базу данных.
    1. По оператору
    2. По iccid
    Принимает словарь вида:
    - operator_id: int
    - iccid: str
    - tel_num: str
    - status: int
    """
    db = MysqlDatabase()
    session = db.session
    result = session.query(
            models.SimCard.sim_tel_number).all()
    session.close()
    return result
