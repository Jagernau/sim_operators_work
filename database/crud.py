import database.mysql_models as models
from database.db_conectors import MysqlDatabase
from sqlalchemy import update, func
from datetime import datetime
import sys

sys.path.append('../')
from sim_operators_work.logger import logger as log


def get_all_sim_issid():
    db = MysqlDatabase()
    session = db.session
    result = session.query(
            models.SimCard.sim_iccid
            ).all()
    session.close()
    return result

def all_mts_sim_issid():
    db = MysqlDatabase()
    session = db.session
    result = session.query(
            models.SimCard.sim_iccid
            ).filter(models.SimCard.sim_cell_operator == 1).all()
    session.close()
    return result

def get_all_mts():
    db = MysqlDatabase()
    session = db.session
    result = session.query(
            models.SimCard
            ).filter(models.SimCard.sim_cell_operator == 1).all()
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
    - block_start: str
    """
    unic_db_iccid = {item[0] for item in get_all_sim_issid()}

    # Внесение симки
    db = MysqlDatabase()
    session = db.session
    if marge_data["iccid"] not in unic_db_iccid:
        try:
            sim_card = models.SimCard(
                    sim_cell_operator=marge_data["operator"],
                    sim_owner=marge_data["owner"],
                    sim_tel_number=marge_data["tel_num"],
                    sim_iccid=marge_data["iccid"],
                    status=marge_data["status"],
                    block_start=marge_data["block_start"]
                    )
            session.add(sim_card)
            session.commit()

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

        except Exception as e:
            print(f"В добавлении сим по одному возникла ошибка {e}")
        finally:
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
                models.SimCard
                ).filter(models.SimCard.sim_iccid == marge_data['iccid']).first()
        try:
            if str(sim_in_db.sim_tel_number) != str(marge_data['tel_num']):

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

                session.execute(
                                update(models.SimCard)
                                .where(models.SimCard.sim_iccid == marge_data['iccid'])
                                .values(sim_tel_number = str(marge_data['tel_num'])))

                session.commit()

        except Exception as e:
            print(f"В обновлении сим ТЕЛЕФОНА возникла ошибка {e}")

        try:
            if sim_in_db.status != int(marge_data['status']):
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
                        new_value=int(marge_data["status"]),
                        action="update",
                        sys_id=marge_data["operator"],
                        contragent_id=None
                        )
                session.add(changes)
                session.commit()

                session.execute(
                                update(models.SimCard)
                                .where(models.SimCard.sim_iccid == marge_data['iccid'])
                                .values(status = marge_data['status']))
                session.commit()
        except Exception as e:
            print(f"В обновлении сим СТАТУСА возникла ошибка {e}")

        try:
            if int(sim_in_db.sim_cell_operator) != int(marge_data['operator']):
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
                        old_value=int(sim_in_db.sim_cell_operator),
                        new_value=int(marge_data["operator"]),
                        action="update",
                        sys_id=marge_data["operator"],
                        contragent_id=None
                        )
                session.add(changes)
                session.commit()

                session.execute(
                                update(models.SimCard)
                                .where(models.SimCard.sim_iccid == marge_data['iccid'])
                                .values(sim_cell_operator = marge_data['operator']))

                session.commit()

        except Exception as e:
            print(f"В обновлении сим ОПЕРАТОРА возникла ошибка {e}")

        try:
            date = datetime.strptime(str(marge_data["block_start"]), "%Y-%m-%d %H:%M:%S") if marge_data["block_start"] != None else None
            if sim_in_db.block_start != date:
                changes = models.GlobalLogging(
                        section_type="sim_card",
                        edit_id=session.query(
                            models.SimCard.sim_id,
                            models.SimCard.sim_cell_operator,
                            models.SimCard.sim_iccid
                            ).filter(
                                models.SimCard.sim_iccid == marge_data["iccid"]
                                ).first()[0],
                        field="block_start",
                        old_value=sim_in_db.block_start,
                        new_value=date,
                        action="update",
                        sys_id=marge_data["operator"],
                        contragent_id=None
                        )
                session.add(changes)
                session.commit()

                session.execute(
                                update(models.SimCard)
                                .where(models.SimCard.sim_iccid == marge_data['iccid'])
                                .values(block_start = date))

                session.commit()

        except Exception as e:
            print(f"В обновлении сим ОПЕРАТОРА возникла ошибка {e}")

        finally:
         session.close()



def write_off_mts_sim(result_mts):
    """
    Списание сим МТС
    """
    unic_db_iccid = {item[0] for item in all_mts_sim_issid()}

    # Внесение симки
    db = MysqlDatabase()
    session = db.session
    for i in unic_db_iccid:
        if str(i) not in result_mts:
            try:
                sim_in_db = session.query(models.SimCard).filter(models.SimCard.sim_iccid == str(i)).first()
                if sim_in_db.status != 0:
                    changes = models.GlobalLogging(
                            section_type="sim_card",
                            edit_id=sim_in_db.sim_id,
                            field="status",
                            old_value=sim_in_db.status,
                            new_value=0,
                            action="update",
                            sys_id=1,
                            contragent_id=None
                            )
                    session.add(changes)
                    session.commit()

                    session.execute(
                                    update(models.SimCard)
                                    .where(models.SimCard.sim_iccid == str(i))
                                    .values(status = 0))
                    session.commit()

                    if sim_in_db.block_start != None:
                        changes = models.GlobalLogging(
                                section_type="sim_card",
                                edit_id=sim_in_db.sim_id,
                                field="block_start",
                                old_value=sim_in_db.block_start,
                                new_value=None,
                                action="update",
                                sys_id=1,
                                contragent_id=None
                                )
                        session.add(changes)
                        session.commit()

                        session.execute(
                                        update(models.SimCard)
                                        .where(models.SimCard.sim_iccid == str(i))
                                        .values(block_start = None))
                        session.commit()


            except Exception as e:
                print(f"В списании {i} возникла ошибка {e}")

            finally:
             session.close()


def dubles_sim_clear():
    db = MysqlDatabase()
    session = db.session
    cut_all_sims = session.query(models.SimCard).filter(
            models.SimCard.sim_cell_operator==1,
            func.length(models.SimCard.sim_iccid) < 19,
            func.length(models.SimCard.sim_iccid) > 6,
            models.SimCard.contragent_id != None,
            ).all()

    for cut in cut_all_sims:
        full = session.query(models.SimCard).filter(
                models.SimCard.sim_cell_operator == 1,
                func.length(models.SimCard.sim_iccid) == 19,
                models.SimCard.contragent_id == None,
                models.SimCard.sim_iccid.like(f'%{cut.sim_iccid}%')
                ).first()
        if full:
            session.execute(
                            update(models.SimCard)
                            .where(models.SimCard.sim_id == full.sim_id)
                            .values(
                                terminal_imei=cut.terminal_imei,
                                contragent_id=cut.contragent_id
                                )
                            )
            session.commit()
    session.close()

