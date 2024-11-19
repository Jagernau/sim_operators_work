import database.mysql_models as models
from database.db_conectors import MysqlDatabase
from sqlalchemy import update

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
    - operator: int
    - owner: int
    - tel_num: str
    - iccid: str
    - status: int
    """
    unic_db_iccid = {item[0] for item in get_all_sim_issid()}

    # Внесение симки
    db = MysqlDatabase()
    session = db.session
    if marge_data["iccid"] not in unic_db_iccid:
        sim_card = models.SimCard(
                sim_cell_operator=marge_data["operator"],
                sim_owner=marge_data["owner"],
                sim_tel_number=marge_data["tel_num"],
                sim_iccid=marge_data["iccid"],
                status=marge_data["status"]
                )
        session.add(sim_card)
        session.commit()
        session.close()

        changes = models.GlobalLogging(
                section_type="sim_card",
                edit_id=session.query(
                    models.SimCard.sim_id,
                    models.SimCard.sim_cell_operator,
                    models.SimCard.sim_iccid
                    ).filter(
                        models.SimCard.sim_cell_operator == marge_data["operator"],
                        models.SimCard.sim_iccid == marge_data["iccid"]
                        ).first()[0],
                field="iccid",
                old_value="0",
                new_value=marge_data["iccid"],
                action="add",
                sys_id=marge_data["operator"],
                contragent_id=None
                )
        session.add(changes)
        session.commit()
        session.close()


def update_one_sim(marge_data):
    """
    Рекурсивно проверяет бд, 
    если такая есть, обновляет её
    По iccid
    Принимает словарь вида:
    - operator: int
    - owner: int
    - tel_num: str
    - iccid: str
    - status: int
    """
    unic_db_iccid = {item[0] for item in get_all_sim_issid()}

    # Внесение симки
    db = MysqlDatabase()
    session = db.session
    if marge_data["iccid"] in unic_db_iccid:
        sim_in_db = session.query(
                models.SimCard.sim_iccid
                ).filter(models.SimCard.sim_iccid == marge_data['iccid']).first()
        if marge_data['tel_num'] != sim_in_db.sim_tel_number:
            session.execute(
                            update(models.SimCard)
                            .where(models.SimCard.sim_iccid == marge_data['iccid'])
                            .values(sim_tel_number = marge_data['tel_num']))

            changes = models.GlobalLogging(
                    section_type="sim_card",
                    edit_id=session.query(
                        models.SimCard.sim_id,
                        models.SimCard.sim_cell_operator,
                        models.SimCard.sim_iccid
                        ).filter(
                            models.SimCard.sim_iccid == marge_data["iccid"]
                            ).first()[0],
                    field="sim_tel_number",
                    old_value=sim_in_db.sim_tel_number,
                    new_value=marge_data["tel_num"],
                    action="update",
                    sys_id=marge_data["operator"],
                    contragent_id=None
                    )
            session.add(changes)
            session.commit()


        if marge_data['status'] != sim_in_db.status:
            session.execute(
                            update(models.SimCard)
                            .where(models.SimCard.sim_iccid == marge_data['iccid'])
                            .values(status = marge_data['status']))

            changes = models.GlobalLogging(
                    section_type="sim_card",
                    edit_id=session.query(
                        models.SimCard.sim_id,
                        models.SimCard.sim_cell_operator,
                        models.SimCard.sim_iccid
                        ).filter(
                            models.SimCard.sim_iccid == marge_data["iccid"]
                            ).first()[0],
                    field="status",
                    old_value=sim_in_db.status,
                    new_value=marge_data["status"],
                    action="update",
                    sys_id=marge_data["operator"],
                    contragent_id=None
                    )
            session.add(changes)
            session.commit()


        if marge_data['operator'] != sim_in_db.sim_cell_operator:
            session.execute(
                            update(models.SimCard)
                            .where(models.SimCard.sim_iccid == marge_data['iccid'])
                            .values(sim_cell_operator = marge_data['operator']))

            changes = models.GlobalLogging(
                    section_type="sim_card",
                    edit_id=session.query(
                        models.SimCard.sim_id,
                        models.SimCard.sim_cell_operator,
                        models.SimCard.sim_iccid
                        ).filter(
                            models.SimCard.sim_iccid == marge_data["iccid"]
                            ).first()[0],
                    field="sim_cell_operator",
                    old_value=sim_in_db.sim_cell_operator,
                    new_value=marge_data["operator"],
                    action="update",
                    sys_id=marge_data["operator"],
                    contragent_id=None
                    )
            session.add(changes)
            session.commit()
    session.close()
