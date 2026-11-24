# coding: utf-8
from sqlalchemy import BigInteger, CheckConstraint, Column, DECIMAL, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, SmallInteger, String, TIMESTAMP, Table, Text, Time, text
from sqlalchemy.dialects.mysql import DATETIME, LONGTEXT, SMALLINT, TEXT, TINYINT, VARCHAR
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class CellOperator(Base):
    __tablename__ = 'Cell_operator'
    __table_args__ = {'comment': 'Таблица для хранения информации об операторах сотовой связи'}

    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR(60), nullable=False, comment='Имя сотового оператора')
    ca_price = Column(Integer, comment='цена для клиентов')
    sun_price = Column(Integer, comment='Цена для Сантел')


t_GOS_DUBLI = Table(
    'GOS_DUBLI', metadata,
    Column('gov_number', String(70)),
    Column('duplicate_count', BigInteger, server_default=text("'0'"))
)


t_ICCID_меньше_19 = Table(
    'ICCID меньше 19', metadata,
    Column('sim_iccid', String(40))
)


t_OKDESK_CONTACTS = Table(
    'OKDESK_CONTACTS', metadata,
    Column('change_time', TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")),
    Column('ca_name', String(255)),
    Column('name', String(50)),
    Column('email', String(80))
)


class PPDKLogging(Base):
    __tablename__ = 'PPDK_logging'

    log_id = Column(Integer, primary_key=True, comment='Лог')
    column_name = Column(VARCHAR(200), nullable=False, comment='Название колонки')
    old_val = Column(VARCHAR(700), comment='Старое значение')
    new_val = Column(VARCHAR(700), comment='Новое значение')
    change_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Дата изменения')
    exist_id = Column(Integer, comment='OST_order_no')
    type_req = Column(VARCHAR(100), comment='Тип изменения')


class PPDKTransneft(Base):
    __tablename__ = 'PPDK_transneft'
    __table_args__ = {'comment': 'Заявки по ППДК транснефть'}

    id = Column(Integer, primary_key=True)
    OST_order_no = Column(Integer, nullable=False, comment='№ заявки в ОСТ\\r\\n')
    formation_date_app = Column(DateTime, nullable=False, comment='"Дата форми-\\r\\nрования заявки"\\r\\n')
    OST = Column(VARCHAR(200), nullable=False, comment='ОСТ\\r\\n')
    organization = Column(VARCHAR(300), nullable=False, comment='Организация\\r\\n')
    type_work = Column(VARCHAR(100), nullable=False, comment='Вид работ\\r\\n')
    vehicle_reg_plate = Column(VARCHAR(100), nullable=False, comment='"Регистра-\\r\\nционный знак ТС"\\r\\n')
    vehic_invent_numb = Column(VARCHAR(200), comment='Инв. № ТС\\r\\n')
    vehic_model = Column(VARCHAR(300), nullable=False, comment='Марка, модель ТС')
    vehicle_type = Column(VARCHAR(200), comment='Тип ТС\\r\\n')
    fault = Column(VARCHAR(300), comment='Неисправность\\r\\n')
    comment = Column(VARCHAR(800), nullable=False, comment='Комментарий\\r\\n')
    date_first_initial = Column(DateTime, nullable=False, comment='"План. дата работ (перво-\\r\\nначальная предложенная заказчиком)"\\r\\n')
    plan_date_work = Column(DateTime, nullable=False, comment='План. дата работ (оконча-\\r\\nтельная)')
    repair_area = Column(VARCHAR(700), comment='Площадка ремонта\\r\\n')
    date_transfer_MVDP = Column(DateTime, comment='Дата передачи в МВДП\\r\\n')
    date_agreement_contrac = Column(DateTime, comment='Дата согласования Исполнителем\\r\\n')
    processing_time = Column(DateTime, comment='Срок обработки\\r\\n')
    performer = Column(VARCHAR(300), comment='Исполнитель\\r\\n')
    date_centralized = Column(DateTime, comment='Дата и время Централизованной приемки работ\\r\\n')
    date_acceptance = Column(DateTime, comment='Дата и время приемки работ в ОСТ\\r\\n')
    dat_accept_works_OST = Column(DateTime, comment='Время приемки работ в ОСТ (в формате чч:мм)\\r\\n')
    status_req = Column(VARCHAR(100), comment='Статус\\r\\n')
    dat_closing_app = Column(DateTime, comment='Дата закрытия заявки\\r\\n')
    comment_primary_doc = Column(VARCHAR(300), comment='Комментарий, первичный документ из ППДК ОСТ\\r\\n')
    summary_act = Column(VARCHAR(300), comment='Сводный акт (в Модуле)\\r\\n')
    completion_date = Column(DateTime, comment='Дата завершения работ в ОСТ\\r\\n')
    days_overdue = Column(Integer, comment='Кол-во дней просрочки\\r\\n')


class AdditionalStatus(Base):
    __tablename__ = 'additional_statuses'
    __table_args__ = (
        Index('add_status_name', 'add_status_name', 'status_code', unique=True),
        {'comment': 'Таблица дополнительных статусов'}
    )

    id_status = Column(Integer, primary_key=True)
    add_status_name = Column(VARCHAR(200), nullable=False, comment='Имя дополнителя приостановленной причины')
    status_code = Column(Integer, nullable=False, index=True, comment='Код статуса')
    detail = Column(VARCHAR(300), nullable=False, comment='Детальное описание')


class AuthGroup(Base):
    __tablename__ = 'auth_group'
    __table_args__ = {'comment': 'Таблица для хранения групп пользователей ЦМС'}

    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR(150), nullable=False, unique=True, comment='Название группы пользователей ЦМС')


class AuthUser(Base):
    __tablename__ = 'auth_user'
    __table_args__ = {'comment': 'Таблица пользователей ЦМС'}

    id = Column(Integer, primary_key=True)
    password = Column(VARCHAR(128), nullable=False, comment='пароль')
    last_login = Column(DATETIME(fsp=6), comment='последний вход')
    is_superuser = Column(TINYINT(1), nullable=False, comment='принадлежность к суперпользователю')
    username = Column(VARCHAR(150), nullable=False, unique=True, comment='логин')
    first_name = Column(VARCHAR(150), nullable=False, comment='имя')
    last_name = Column(VARCHAR(150), nullable=False, comment='фамилия')
    email = Column(VARCHAR(254), nullable=False, comment='почта')
    is_staff = Column(TINYINT(1), nullable=False, comment='является ли сотрудником')
    is_active = Column(TINYINT(1), nullable=False, comment='активность аккаунта')
    date_joined = Column(DATETIME(fsp=6), nullable=False, comment='дата создания аккаунта')


class Billing(Base):
    __tablename__ = 'billing'
    __table_args__ = {'comment': 'Таблица снимок параметров билинга за день'}

    bil_id = Column(Integer, primary_key=True, comment='ID билинга')
    sys_mon_id = Column(Integer, nullable=False, comment='ID системы мониторинга')
    sys_mon_price = Column(Integer, nullable=False, comment='Стоимость СМ для КЛ')
    retrans_id = Column(Integer, comment='ID ретрансляции')
    retrans_name = Column(VARCHAR(50), comment='Название ретрансляции')
    retrans_price = Column(Integer, comment='Цена ретрансляции')
    obj_id = Column(Integer, nullable=False, comment='ID объекта в БД')
    obj_name = Column(VARCHAR(100), nullable=False, comment='Название объекта')
    sim_id = Column(Integer, comment='ID СИМКАРТЫ')
    sim_operat_name = Column(VARCHAR(50), comment='Имя оператора')
    sim_price = Column(Integer, comment='Цена сим для КЛ')
    client_id = Column(Integer, comment='ID клиента')
    client_name = Column(VARCHAR(300), comment='Имя клиента')
    client_inn = Column(VARCHAR(200), comment='ИНН Клиента')
    discount_client = Column(JSON, comment="СКИДКИ КЛИЕНТА\\r\\n[{'dis_id': 1, 'dis_name': 'Лояльность'},\\r\\n {'dis_id': 2, 'dis_name': 'Кол-во объектов > 50'},\\r\\n]")
    discount_client_rate = Column(Integer, comment='Итоговый процент Скидки')
    obj_status_id = Column(Integer, nullable=False, comment='ID статуса объекта')
    discount_obj = Column(JSON, comment="СКИДКИ КЛИЕНТА [{'dis_id': 1, 'dis_name': 'Лояльность'}, {'dis_id': 2, 'dis_name': 'Дружественный'}, ]")
    discount_obj_rate = Column(Integer, comment='Процент скидок на объект')
    record_time = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время создания записи')
    obj_status_name = Column(VARCHAR(50), nullable=False, comment='Имя статуса объекта')
    obj_group_name = Column(VARCHAR(400), comment='Название группы объектов как в СМ')
    obj_group_id = Column(VARCHAR(400), nullable=False, comment='ИД группы объектов')
    obj_id_in_sys = Column(VARCHAR(300), nullable=False, comment='ID объекта в системе мониторинга')
    sys_mon_name = Column(VARCHAR(100), nullable=False, comment='Название системы мониторинга')
    client_login = Column(VARCHAR(400), comment='Логин клиента')
    client_kpp = Column(VARCHAR(200), comment='Клиентский КПП')
    total_sum = Column(Integer, comment='Итоговая сумма')
    obj_imei = Column(VARCHAR(100), comment='IMEI объекта')


class DevicesVendor(Base):
    __tablename__ = 'devices_vendor'
    __table_args__ = {'comment': 'Таблица для хранения информации о производителях устройств'}

    id = Column(Integer, primary_key=True)
    vendor_name = Column(VARCHAR(35), comment='Название фирмы производителя терминалов')


class DiscountClient(Base):
    __tablename__ = 'discount_client'
    __table_args__ = {'comment': 'Таблица с вариантами скидок'}

    dis_cl_id = Column(Integer, primary_key=True, comment='ID Скидки')
    dis_cl_name = Column(VARCHAR(100), nullable=False, comment='Название Скидки')
    dis_cl_rate = Column(DECIMAL(10, 2), nullable=False, comment='Скидка Надбавка')


class DiscountObj(Base):
    __tablename__ = 'discount_obj'
    __table_args__ = {'comment': 'Варианты скидок на объекты'}

    dis_obj_id = Column(Integer, primary_key=True, comment='ID скидки на объекты')
    dis_obj_name = Column(VARCHAR(100), nullable=False, comment='Название скидок на объекты')
    dis_obj_rate = Column(Integer, nullable=False, comment='Процент скидки на объект')


class DjangoContentType(Base):
    __tablename__ = 'django_content_type'
    __table_args__ = (
        Index('django_content_type_app_label_model_76bd3d3b_uniq', 'app_label', 'model', unique=True),
        {'comment': 'Таблица для хранения типов содержимого Django ЦМС'}
    )

    id = Column(Integer, primary_key=True)
    app_label = Column(VARCHAR(100), nullable=False, comment='из какого приложения')
    model = Column(VARCHAR(100), nullable=False, comment='из какой модели')


class DjangoMigration(Base):
    __tablename__ = 'django_migrations'
    __table_args__ = {'comment': 'Таблица для хранения информации о миграциях Django ЦМС'}

    id = Column(BigInteger, primary_key=True)
    app = Column(VARCHAR(255), nullable=False, comment='таблица')
    name = Column(VARCHAR(255), nullable=False, comment='действие')
    applied = Column(DATETIME(fsp=6), nullable=False, comment='дата')


class DjangoSession(Base):
    __tablename__ = 'django_session'
    __table_args__ = {'comment': 'Таблица для хранения сессий Django Заходов в ЦМС'}

    session_key = Column(VARCHAR(40), primary_key=True)
    session_data = Column(LONGTEXT, nullable=False)
    expire_date = Column(DATETIME(fsp=6), nullable=False, index=True)


class EmailsSend(Base):
    __tablename__ = 'emails_sends'
    __table_args__ = {'comment': 'Таблица по email рассылкам'}

    send_id = Column(BigInteger, primary_key=True)
    sends_time = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время отправки')
    email = Column(VARCHAR(100), nullable=False, comment='Почта')
    send_status = Column(TINYINT, nullable=False, comment='Успешность отправки\\r\\n0 - отправлено\\r\\n1 - не отправлено')
    confir_status = Column(TINYINT, nullable=False, comment='0 - Не подтверждена\\r\\n1 - Подтверждена')
    mail_header = Column(VARCHAR(200), nullable=False, comment='Заголовок письма')
    mail_body = Column(LONGTEXT, nullable=False, comment='Текст рассылки')
    client_name = Column(VARCHAR(400), nullable=False, comment='Имя клиента')
    sender_mail = Column(VARCHAR(100), nullable=False, comment='Почта рассыльщика')
    user_login = Column(VARCHAR(100), nullable=False, comment='Логин юзера запустившего рассылку')
    uid_header = Column(VARCHAR(200), nullable=False, comment='Уникальный ИД темы рассылки')
    sender_params = Column(JSON, nullable=False, comment='Параметры рассылки')
    attachment_path = Column(VARCHAR(500), comment='Место хранения файла')
    comment = Column(VARCHAR(500), comment='Комментарий')
    send_type = Column(TINYINT, nullable=False, comment='Через что ведётся рассылка:\\r\\n0 - почта\\r\\n1 - ОКДЕСК')


class GlobalLogging(Base):
    __tablename__ = 'global_logging'
    __table_args__ = {'comment': 'Первоначальная Таблица для хранения изменений в таблицах объектов и клиентов 1с через Python, до тригерного логирования'}

    id = Column(Integer, primary_key=True)
    section_type = Column(VARCHAR(50), nullable=False, comment='изменения в объектах или клиентах')
    edit_id = Column(Integer, nullable=False, comment='id изменённого')
    field = Column(VARCHAR(50), nullable=False, comment='поле изменения')
    old_value = Column(VARCHAR(8000), comment='старое значение')
    new_value = Column(VARCHAR(8000), comment='новое значение')
    change_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    sys_id = Column(Integer, comment='Система мониторинга')
    action = Column(VARCHAR(100), comment='добавление, изменение или удаление')
    contragent_id = Column(Integer, comment='логгирование контрагента')


class GuaranteeTerm(Base):
    __tablename__ = 'guarantee_terms'
    __table_args__ = {'comment': 'Таблица для хранения родителей контрагентов'}

    gt_id = Column(Integer, primary_key=True, comment='ID гарантийного срока')
    gt_term = Column(Integer, comment='Срок гарантии (дней)')
    gt_type = Column(VARCHAR(255), comment='Тип гарантии')


class Holding(Base):
    __tablename__ = 'holdings'
    __table_args__ = {'comment': 'Таблица для хранения информации о Холдингах по тз'}

    holding_id = Column(Integer, primary_key=True)
    holding_name = Column(VARCHAR(255), comment='Имя родителя контрагента (Холдинг)')


class InfoServTarifClient(Base):
    __tablename__ = 'info_serv_tarif_client'
    __table_args__ = {'comment': 'Сопоставление ТАРИФ СЕРВИСОВ КЛИЕНТ'}

    tarif_client_id = Column(Integer, primary_key=True, comment='ИД отношений')
    tarif_id = Column(Integer, nullable=False, index=True, comment='ID Тарифа')
    client_id = Column(Integer, nullable=False, index=True, comment='ID Клиента')
    start_tarif = Column(Date, comment='Начало тарифа у клиента')
    end_tarif = Column(Date, comment='Конец тарифа')


class InfoServTarif(Base):
    __tablename__ = 'info_serv_tarifs'
    __table_args__ = {'comment': 'Таблица с ТАРИФАМИ СЕРВИСОВ'}

    tarif_id = Column(Integer, primary_key=True, comment='ИД тарифов')
    name = Column(VARCHAR(100), nullable=False, comment='Название тарифа')
    price = Column(Integer, nullable=False, comment='Цена тарифа с НДС')
    count = Column(Integer, comment='Количество доступных сервисов')
    moth_subs = Column(Integer, comment='Количество месяцев')
    special_process = Column(TINYINT, comment='Требуется ли обработка специалиста 0-не нужна\\r\\n1-нужна')
    specialist_price = Column(Integer, server_default=text("'0'"), comment='Выплата специалисту за 1 ОМ в месяц')


class InformationService(Base):
    __tablename__ = 'information_services'
    __table_args__ = {'comment': 'Таблица для информационных сервисов Клиентов'}

    serv_id = Column(Integer, primary_key=True, comment='ID Сервиса')
    serv_name = Column(VARCHAR(100), nullable=False, unique=True, comment='Название сервиса')
    serv_price = Column(Integer, comment='Цена за сервис')


class LogChange(Base):
    __tablename__ = 'log_changes'
    __table_args__ = {'comment': 'Таблица логирования изменений в данных Базы'}

    log_id = Column(Integer, primary_key=True)
    changes_date = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='Дата изменения')
    changes_table = Column(VARCHAR(250), comment='В какой таблице были внесены изменения')
    changes_action = Column(TINYINT, comment='Название действия:\\r\\n0 - Del\\r\\n1 - Insert\\r\\n2 - Update')
    obj_key = Column(Integer, comment='Ключ элемента, Практически везде ID. Делаю по ID int')
    changes_column = Column(VARCHAR(255), comment='Название столбца')
    old_val = Column(VARCHAR(255), comment='Старое значение')
    new_val = Column(VARCHAR(255), comment='Новое значение')


class LoginUsersPhone(Base):
    __tablename__ = 'login_users_phones'
    __table_args__ = {'comment': 'Таблица с логинами и паролями и телефонами'}

    id = Column(Integer, primary_key=True, comment='ID записи')
    phone = Column(VARCHAR(12), nullable=False, comment='телефон')
    login = Column(VARCHAR(12), nullable=False, comment='Логин')
    password = Column(VARCHAR(19), nullable=False, comment='Пароль')
    mess_name = Column(VARCHAR(40), nullable=False, comment='Имя в месседжере')
    mess_user_id = Column(VARCHAR(100), nullable=False, comment='ID в меседжере')


class MonitoringSystem(Base):
    __tablename__ = 'monitoring_system'
    __table_args__ = {'comment': 'Таблица для хранения информации о системах мониторинга'}

    mon_sys_id = Column(Integer, primary_key=True)
    mon_sys_name = Column(VARCHAR(60), comment='Название системы мониторинга')
    mon_sys_obj_price_suntel = Column(Integer, comment='Стоимость объекта для Сантел')
    mon_sys_ca_obj_price_default = Column(Integer, comment='Базовая стоимость объекта для Контрагента')
    mon_url = Column(VARCHAR(200), comment='Адресс Системы мониторинга')


class NdsTable(Base):
    __tablename__ = 'nds_table'

    nds_id = Column(Integer, primary_key=True)
    nds_suntel_name = Column(VARCHAR(100), nullable=False, comment='Принадлежность к подразделению Сантел')
    nds_rate = Column(Integer, nullable=False, comment='Процент НДС в числовом')
    nds_create_date = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Дата создания НДС')


class ObjectRetranslator(Base):
    __tablename__ = 'object_retranslators'
    __table_args__ = {'comment': 'Таблица для хранения информации о ретрансляторах'}

    retranslator_id = Column(Integer, primary_key=True)
    retranslator_name = Column(VARCHAR(50), comment='Имя ретранслятора')
    retranslator_suntel_price = Column(Integer, comment='цена ретрансляции для Сантел')
    retranslator_ca_price = Column(Integer, comment='Цена ретрансляции для клиента')
    retrans_adres = Column(VARCHAR(200), comment='Адрес куда ретранслируется')
    retrans_protocol = Column(TINYINT, nullable=False, comment='Виды протоколов:\\r\\n1- Egts\\r\\n2 - Wialon ретранслятор\\r\\n3- Wialon IPS')


class ObjectStatus(Base):
    __tablename__ = 'object_statuses'
    __table_args__ = {'comment': 'Таблица для хранения информации о статусах объектов'}

    status_id = Column(Integer, primary_key=True)
    status = Column(VARCHAR(50), comment='Название статуса')
    abon_bool = Column(TINYINT(1), nullable=False, comment='На абонентке или нет')


class OkDeskLoggingIs(Base):
    __tablename__ = 'ok_desk_logging_iss'
    __table_args__ = {'comment': 'Логгирование изменение в заявках ОКДЕСК'}

    id = Column(Integer, primary_key=True)
    section_type = Column(VARCHAR(100), comment='изменения в объектах или клиентах')
    edit_id = Column(Integer, comment='id изменённого')
    field = Column(VARCHAR(100), comment='поле изменения')
    old_value = Column(JSON, comment='старое значение')
    new_value = Column(JSON, comment='новое значение')
    change_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment='Время создания заявки')
    action = Column(VARCHAR(100), comment='добавление, изменение или удаление\t')


class OnecContact(Base):
    __tablename__ = 'onec_contacts'
    __table_args__ = {'comment': 'Контакты'}

    contact_id = Column(Integer, primary_key=True, comment='Идентификатор Контактов')
    surname = Column(VARCHAR(50), comment='Фамилия')
    name = Column(VARCHAR(50), comment='Имя')
    patronymic = Column(VARCHAR(50), comment='Отчество')
    position = Column(VARCHAR(100), comment='Должность')
    phone = Column(VARCHAR(80), comment='Телефон')
    mobiletelephone = Column(VARCHAR(80), comment='МобТелефон')
    email = Column(VARCHAR(80), comment='ЭлПочта')
    unique_partner_identifier = Column(VARCHAR(200), comment='УникальныйИдентификаторПартнера')
    unique_contact_identifier = Column(VARCHAR(200), comment='УникальныйИдентификаторКонтактногоЛица')
    ok_desk_id = Column(Integer, comment='ИД в ОК ДЕСК')
    usesokdesk = Column(TINYINT, nullable=False, comment='ИспользуетOKDESK\\r\\nИспользуется Ли в ОКДЕСК\\r\\n0-НЕТ\\r\\n1_ДА')
    connectedtelegram_bot = Column(TINYINT, nullable=False, comment='ПодключенКТелеграм_Боту\\r\\nПодключённ ли к телеграмм\\r\\n0-нет\\r\\n1-Да')
    nametelegram = Column(VARCHAR(200), comment='ИмяВТелеграм')
    connectedcmob_application = Column(TINYINT, nullable=False, comment='ПодключенКМоб_Приложению\\r\\n0-нет\\r\\n1-да')
    idbmob_application = Column(VARCHAR(200), comment='IDВМоб_Приложении')
    access_personal_okdesk = Column(TINYINT, nullable=False, server_default=text("'0'"), comment='Предоставлен ли доступ клиенту к ОКДЕСК')
    sign_verification = Column(TINYINT, comment='Проверен')


class OnecContract(Base):
    __tablename__ = 'onec_contracts'
    __table_args__ = {'comment': 'Таблица с договорами из 1С'}

    contract_id = Column(Integer, primary_key=True, comment='Внутренний ID контракта')
    name_contract = Column(VARCHAR(100), comment='НаименованиеДоговора')
    contract_number = Column(VARCHAR(100), comment='НомерДоговора')
    contract_date = Column(Date, comment='ДатаДоговора')
    contract_status = Column(VARCHAR(50), comment='Статус')
    organization = Column(VARCHAR(200), comment='Организация')
    partner = Column(VARCHAR(1000), comment='Партнер')
    counterparty = Column(VARCHAR(1000), comment='Контрагент')
    contract_commencement_date = Column(Date, comment='ДатаНачалаДействия')
    contract_expiration_date = Column(Date, comment='ДатаОкончанияДействия')
    contract_purpose = Column(VARCHAR(200), comment='Цель')
    type_calculations = Column(VARCHAR(200), comment='ВидРасчетов')
    category = Column(VARCHAR(100), comment='Категория')
    manager = Column(VARCHAR(200), comment='Менеджер')
    subdivision = Column(VARCHAR(600), comment='Подразделение')
    contact_person = Column(VARCHAR(300), comment='КонтактноеЛицо')
    organization_bank_account = Column(VARCHAR(300), comment='БанковскийСчетОрганизации')
    counterparty_bank_account = Column(VARCHAR(300), comment='БанковскийСчетКонтрагента')
    detailed_calculations = Column(VARCHAR(200), comment='ДетализацияРасчетов')
    unique_partner_identifier = Column(VARCHAR(500), comment='УникальныйИдентификаторПартнера')
    unique_counterparty_identifier = Column(VARCHAR(500), comment='УникальныйИдентификаторКонтрагента')
    ok_desk_id = Column(Integer, unique=True, comment='ID в ОК-деск')
    unique_contract_identifier = Column(VARCHAR(200), nullable=False, unique=True, comment='УникальныйИдентификаторДоговораКонтрагента')
    signing_status = Column(VARCHAR(100), comment='СтатусПодписания')


class OnecOrder(Base):
    __tablename__ = 'onec_order'
    __table_args__ = {'comment': 'Таблица заказ нарядов из 1С'}

    order_id = Column(Integer, primary_key=True)
    order_unic_id = Column(VARCHAR(50), nullable=False, comment='УникальныйИдентификаторАктаТО')
    order_num = Column(VARCHAR(50), nullable=False, comment='ЗаказНарядНомер')
    order_data = Column(DateTime, nullable=False, comment='Дата')
    edit_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время создания записи')
    file_path = Column(VARCHAR(200), unique=True, comment='ПутьКФайлу')
    obj_id = Column(Integer, comment='ВнутреннийIDОбъектаБД2')


class ReprogTerm(Base):
    __tablename__ = 'reprog_terms'
    __table_args__ = {'comment': 'Таблица перепрограммирования терминалов'}

    reprog_id = Column(Integer, primary_key=True)
    type_term = Column(VARCHAR(100), comment='Тип терминала')
    imei = Column(VARCHAR(100), nullable=False, unique=True, comment='Имей терминала')
    vehicle_name = Column(VARCHAR(150), comment='Имя объекта')
    client_name = Column(VARCHAR(300), comment='Имя клиента')
    comand_name = Column(VARCHAR(200), comment='Название команды')
    comand = Column(VARCHAR(200), comment='Команда')
    send_type = Column(VARCHAR(200), comment='Тип через что была отправка')
    monitoring_system = Column(Integer, comment='Система мониторинга')
    full_device_name = Column(VARCHAR(200), comment='Полное название типа терминала')
    data_reprog = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='Дата репрог')


class RequestsFromOKDESK(Base):
    __tablename__ = 'requests_from_OKDESK'

    db_id = Column(Integer, primary_key=True, comment='Внутренний ИД')
    ok_desk_id = Column(Integer, nullable=False, unique=True, comment='ИД заявки в ОКДЕСК')
    title = Column(VARCHAR(300), comment='Название заявки')
    created_at = Column(DateTime, comment='Дата создания')
    completed_at = Column(DateTime, comment='Закончена')
    deadline_at = Column(DateTime, comment='Конечный срок')
    delay_to = Column(DateTime, comment='Продлена до')
    planned_reaction_a = Column(DateTime, comment='Плановая дата реакции')
    reacted_at = Column(DateTime, comment='Время реакции')
    without_answer = Column(TINYINT, comment='Без ответа')
    updated_at = Column(DateTime, comment='Обновлено')
    status = Column(JSON, comment='Статус заявки')
    type_req = Column(JSON, comment='Тип заявки')
    priority = Column(JSON, comment='Приоритет заявки')
    company = Column(JSON, comment='Компания на ком заявка')
    contact = Column(JSON, comment='Контакт')
    service_object = Column(JSON, comment='Объект')
    agreement = Column(JSON, comment='договор')
    equipments = Column(JSON, comment='Оборудование')
    req_data_db = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время создания записи в БД')
    comments = Column(JSON, comment='Коментарии')
    specifications = Column(JSON, comment='Спецификации Заявки')
    observers = Column(JSON, comment='Наблюдатели')
    assignee = Column(JSON, comment='Исполнители')
    parameters = Column(JSON, comment='Параметры заявки')
    source = Column(VARCHAR(100), comment='Способ регистрации заявки')


class SensorVendor(Base):
    __tablename__ = 'sensor_vendor'
    __table_args__ = {'comment': 'Производители датчиков'}

    id = Column(Integer, primary_key=True, comment='ID изготовителя Датчиков')
    name = Column(VARCHAR(200), nullable=False, comment='Имя производителя')


class ShtrafovnetCompaniesCache(Base):
    __tablename__ = 'shtrafovnet_companies_cache'
    __table_args__ = {'comment': 'Периодический снапшот GET /v3/companies для офлайн-поиска дублей по ИНН'}

    shtrafovnet_company_id = Column(Integer, primary_key=True)
    inn = Column(String(20), index=True)
    display_name = Column(String(255))
    status = Column(String(20))
    synced_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class ShtrafovnetSyncLog(Base):
    __tablename__ = 'shtrafovnet_sync_log'
    __table_args__ = (
        Index('idx_entity', 'entity_type', 'entity_local_id'),
        {'comment': 'Аудит операций с API Штрафов.Нет'}
    )

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String(150))
    entity_type = Column(Enum('company', 'car'), nullable=False)
    entity_local_id = Column(Integer)
    action = Column(String(50), nullable=False)
    request_json = Column(Text)
    response_json = Column(Text)
    success = Column(TINYINT(1), nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class SmsReply(Base):
    __tablename__ = 'sms_reply'
    __table_args__ = {'comment': 'Ответы от СМС'}

    reply_id = Column(Integer, primary_key=True)
    text_data = Column(VARCHAR(300), comment='Ответ')
    naming = Column(VARCHAR(100), nullable=False, comment='От кого отправлен запрос')
    user_contact = Column(VARCHAR(100), nullable=False, comment='На какой телефон отправлен запрос')
    received_at = Column(VARCHAR(100), comment='получено по адресу')
    internal_id = Column(VARCHAR(300), nullable=False, comment='ID Отправки')
    created_reply_time = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время создания записи')


class SmsSending(Base):
    __tablename__ = 'sms_sending'
    __table_args__ = {'comment': 'Таблица отправленных СМС'}

    sending_id = Column(Integer, primary_key=True)
    request_data = Column(VARCHAR(300), nullable=False, comment='Запрос')
    naming = Column(VARCHAR(100), nullable=False, comment='От кого отправлен запрос')
    user_contact = Column(VARCHAR(100), nullable=False, comment='На какой телефон отправлен запрос')
    internal_id = Column(VARCHAR(300), comment='Уникальный ИД заявки')
    created_send_time = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время создании записи')


class TachographTable(Base):
    __tablename__ = 'tachograph_table'
    __table_args__ = {'comment': 'Таблица тахографии Сантел сервис'}

    id_tacho = Column(Integer, primary_key=True, comment='ИД запрограммированого ТАХО')
    card_number = Column(VARCHAR(200), comment='Номер карты')
    activation_date = Column(Date, nullable=False, comment='Дата активизации')
    serial_cryptographic = Column(VARCHAR(200), nullable=False, unique=True, comment='Серийный номер блока СКЗИ')
    tachograph_serial = Column(VARCHAR(200), comment='Серийный номер тахографа')
    organization = Column(VARCHAR(200), comment='Организация')
    client_inn = Column(VARCHAR(200), comment='ИНН')
    ogrn = Column(VARCHAR(200), comment='ОГРН')
    address = Column(VARCHAR(200), comment='Адрес')
    vehicle_number = Column(VARCHAR(200), nullable=False, comment='ГРЗ ТС')
    vin_ts = Column(VARCHAR(200), nullable=False, comment='ВИН ТС')
    pts = Column(VARCHAR(200), nullable=False, comment='ПТС')
    vehicle_manufactur = Column(VARCHAR(100), nullable=False, comment='Производитель ТС')
    vehicle_model = Column(VARCHAR(100), nullable=False, comment='Модель ТС')
    vehicle_color = Column(VARCHAR(100), nullable=False, comment='Цвет ТС')
    year_vehicle = Column(Integer, nullable=False, comment='Год выпуска ТС')
    send_to_okdesk = Column(TINYINT, nullable=False, server_default=text("'0'"), comment='Признак отправки')


class UserLogging(Base):
    __tablename__ = 'user_logging'
    __table_args__ = {'comment': 'Таблица для хранения логов действий пользователей Базы данных, например пользователя Битрикс или Разработчиков Махалова'}

    id = Column(Integer, primary_key=True)
    user_name = Column(VARCHAR(50))
    action_type = Column(VARCHAR(50))
    action_date = Column(Date)
    action_time = Column(Time)
    old_val = Column(TEXT)
    new_val = Column(VARCHAR(300))
    action_description = Column(TEXT)


t_v_sim_gde_stoit = Table(
    'v_sim_gde_stoit', metadata,
    Column('sim_iccid', String(40)),
    Column('sim_tel_number', String(40)),
    Column('operator', String(60)),
    Column('imei_u_nas', String(25)),
    Column('imei_u_operatora', String(25)),
    Column('model_ustroystva', String(100)),
    Column('operator_last_activity', DateTime),
    Column('operator_lat', DECIMAL(10, 6)),
    Column('operator_lon', DECIMAL(10, 6)),
    Column('tochnost_metrov', Integer),
    Column('operator_apn', String(100)),
    Column('operator_last_ip', String(45)),
    Column('ca_name', String(255)),
    Column('client_name', String(270))
)


t_v_sim_imei_check = Table(
    'v_sim_imei_check', metadata,
    Column('sim_id', Integer, server_default=text("'0'")),
    Column('sim_iccid', String(40)),
    Column('sim_tel_number', String(40)),
    Column('operator', String(60)),
    Column('imei_u_nas', String(25)),
    Column('imei_u_operatora', String(25)),
    Column('operator_device_name', String(100)),
    Column('operator_last_activity', DateTime),
    Column('obektov_s_etim_imei', BigInteger, server_default=text("'0'")),
    Column('poslednee_soobshenie_monitoring', DateTime),
    Column('ca_name', String(255)),
    Column('client_name', String(270)),
    Column('sverka_s_nashimi', String(22)),
    Column('sverka_s_monitoringom', String(25))
)


t_v_sim_imei_musor = Table(
    'v_sim_imei_musor', metadata,
    Column('sim_id', Integer, server_default=text("'0'")),
    Column('sim_iccid', String(40)),
    Column('sim_tel_number', String(40)),
    Column('sim_cell_operator', Integer),
    Column('terminal_imei', String(25)),
    Column('client_name', String(270)),
    Column('chto_ne_tak', String(26))
)


t_v_sim_molchit = Table(
    'v_sim_molchit', metadata,
    Column('sim_iccid', String(40)),
    Column('sim_tel_number', String(40)),
    Column('operator', String(60)),
    Column('terminal_imei', String(25)),
    Column('operator_imei', String(25)),
    Column('operator_device_name', String(100)),
    Column('operator_last_activity', DateTime),
    Column('dney_molchit', BigInteger),
    Column('ca_name', String(255)),
    Column('client_name', String(270))
)


t_v_sim_polnota_dannyh = Table(
    'v_sim_polnota_dannyh', metadata,
    Column('operator', String(60)),
    Column('vsego_sim', BigInteger, server_default=text("'0'")),
    Column('s_imei_operatora', DECIMAL(23, 0)),
    Column('s_imei_nashim', DECIMAL(23, 0)),
    Column('rashozhdeniy', DECIMAL(23, 0)),
    Column('s_imsi', DECIMAL(23, 0)),
    Column('s_aktivnostyu', DECIMAL(23, 0)),
    Column('s_koordinatami', DECIMAL(23, 0)),
    Column('poslednyaya_sverka', DateTime)
)


t_Вытягивание_госНомеров_по_типу_А123АБ12 = Table(
    'Вытягивание госНомеров по типу А123АБ12', metadata,
    Column('object_name', String(70)),
    Column('contragent_id', Integer)
)


t_Дубли_ICCID_по_маске_19_символов = Table(
    'Дубли ICCID по маске 19 символов', metadata,
    Column('sim_iccid', String(19)),
    Column('count', BigInteger, server_default=text("'0'"))
)


t_Дубли_номеров = Table(
    'Дубли номеров', metadata,
    Column('gn', String(25)),
    Column('ct', BigInteger, server_default=text("'0'"))
)


t_Не_привязанные_Объекты_к_КЛиентам = Table(
    'Не привязанные Объекты к КЛиентам', metadata,
    Column('mon_sys_name', String(60)),
    Column('object_name', String(70)),
    Column('owner_contragent', String(200)),
    Column('owner_user', String(255))
)


t_Одинаковые_инн = Table(
    'Одинаковые инн', metadata,
    Column('ca_inn', String(60)),
    Column('count', BigInteger, server_default=text("'0'"))
)


t_Одинаковые_логины = Table(
    'Одинаковые логины', metadata,
    Column('login', String(60)),
    Column('count', BigInteger, server_default=text("'0'"))
)


t_Сим_1378___Терминал_4752 = Table(
    'Сим 1378 - Терминал 4752', metadata,
    Column('device_serial', String(100)),
    Column('device_imei', String(60)),
    Column('terminal_date', DateTime),
    Column('name', String(200)),
    Column('ca_name', String(255)),
    Column('sim_iccid', String(40)),
    Column('sim_tel_number', String(40))
)


class Contragent(Base):
    __tablename__ = 'Contragents'
    __table_args__ = {'comment': 'Таблица для хранения информации о контрагентах по тз'}

    ca_id = Column(Integer, primary_key=True)
    ca_holding_id = Column(ForeignKey('holdings.holding_id'), index=True, comment='ID холдинга')
    ca_name = Column(VARCHAR(255), comment='НаименованиеПартнёра')
    ca_shortname = Column(VARCHAR(250), comment='НаименованиеПолноеПартнёра')
    ca_inn = Column(VARCHAR(60), comment='ИНН')
    ca_kpp = Column(VARCHAR(60), comment='КПП')
    ca_bill_account_num = Column(VARCHAR(60), comment='Расчетный счет ????????')
    ca_bill_account_bank_name = Column(VARCHAR(60), comment='Наименование банка ????')
    ca_bill_account_ogrn = Column(VARCHAR(60), comment='ОГРН ????????')
    ca_edo_connect = Column(TINYINT(1), comment='Обмен ЭДО ??????')
    ca_field_of_activity = Column(VARCHAR(260), comment='НаправлениеБизнесаКонтрагента')
    ca_type = Column(VARCHAR(60), comment='ЮрФизЛицоПартёр')
    unique_onec_id = Column(VARCHAR(100), comment='УникальныйИдентификаторПарнёра')
    registration_date = Column(Date, comment='Дата регистрации в 1С')
    key_manager = Column(VARCHAR(200), comment='Основной менеджер ')
    actual_address = Column(VARCHAR(300), comment='Фактический адрес ')
    registered_office = Column(VARCHAR(300), comment='Юридический адрес ')
    phone = Column(VARCHAR(200), comment='Телефон ')
    ca_uid_contragent = Column(VARCHAR(100), comment='УникальныйИдентификаторКонтрагента')
    ca_name_contragent = Column(VARCHAR(255), comment='НаименованиеКонтрагента')
    service_manager = Column(VARCHAR(100), comment='Имя прикреплённого менеджера тех поддержки')
    ok_desk_id = Column(Integer, comment='id в ОК деске')
    ca_tarif = Column(VARCHAR(20), comment='Тариф Клиента')
    customer_training = Column(TINYINT, comment='Обучен ли клиент по Сервисам.')

    ca_holding = relationship('Holding')


class AuthPermission(Base):
    __tablename__ = 'auth_permission'
    __table_args__ = (
        Index('auth_permission_content_type_id_codename_01ab375a_uniq', 'content_type_id', 'codename', unique=True),
        {'comment': 'Таблица разрешений для пользователей ЦМС'}
    )

    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR(255), nullable=False, comment='Название разрешения для пользователя ЦМС')
    content_type_id = Column(ForeignKey('django_content_type.id'), nullable=False, comment='Возможность выполнять действия в ЦМС')
    codename = Column(VARCHAR(100), nullable=False)

    content_type = relationship('DjangoContentType')


class AuthUserGroup(Base):
    __tablename__ = 'auth_user_groups'
    __table_args__ = (
        Index('auth_user_groups_user_id_group_id_94350c0c_uniq', 'user_id', 'group_id', unique=True),
        {'comment': 'Таблица связи пользователей с группами в системе аутентификации ЦМС'}
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(ForeignKey('auth_user.id'), nullable=False, comment='связь с пользователем ЦМС')
    group_id = Column(ForeignKey('auth_group.id'), nullable=False, index=True, comment='связь с группой пользователей ЦМС')

    group = relationship('AuthGroup')
    user = relationship('AuthUser')


class DevicesBrand(Base):
    __tablename__ = 'devices_brands'
    __table_args__ = {'comment': 'Таблица для хранения информации о моделях устройств'}

    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR(200))
    devices_vendor_id = Column(ForeignKey('devices_vendor.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Id Вендора терминалов')

    devices_vendor = relationship('DevicesVendor')


class DevicesLoggerCommand(Base):
    __tablename__ = 'devices_logger_commands'
    __table_args__ = {'comment': 'Таблица для хранения журнала команд, отправленных на устройства через ЦМС не по ТЗ'}

    id = Column(Integer, primary_key=True)
    command_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время отправки команды ')
    command_resresponse = Column(VARCHAR(200), nullable=False, comment='Ответ на команду')
    command_send = Column(VARCHAR(200), nullable=False, comment='Команда')
    programmer = Column(ForeignKey('auth_user.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Кто отправил команду')
    terminal_imei = Column(VARCHAR(50), nullable=False, comment='imei терминала')

    auth_user = relationship('AuthUser')


class DjangoAdminLog(Base):
    __tablename__ = 'django_admin_log'
    __table_args__ = (
        CheckConstraint('(`action_flag` >= 0)'),
        {'comment': 'Таблица для хранения журнала действий администратора ЦМС'}
    )

    id = Column(Integer, primary_key=True)
    action_time = Column(DATETIME(fsp=6), nullable=False, comment='Время операции')
    object_id = Column(LONGTEXT, comment='id объекта Бд было произведено действие')
    object_repr = Column(VARCHAR(200), nullable=False, comment='что было изменено')
    action_flag = Column(SMALLINT, nullable=False, comment='какое действие было выполнено')
    change_message = Column(LONGTEXT, nullable=False, comment='на что изменено')
    content_type_id = Column(ForeignKey('django_content_type.id'), index=True, comment='в какой таблице были изменения')
    user_id = Column(ForeignKey('auth_user.id'), nullable=False, index=True, comment='кто из пользователей ЦМС внёс изменения')

    content_type = relationship('DjangoContentType')
    user = relationship('AuthUser')


class InfoServObjectsGrz(Base):
    __tablename__ = 'info_serv_objects_grz'
    __table_args__ = {'comment': 'Таблица для сервисам по штрафам с СТС и ГРЗ'}

    id_grz = Column(Integer, primary_key=True)
    grz = Column(VARCHAR(50), nullable=False, comment='Госномер')
    sts = Column(VARCHAR(50), nullable=False, comment='СТС')
    monitoring_id = Column(VARCHAR(100), nullable=False, comment='\tID объекта в системе мониторинга')
    sys_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Система мониторинга')

    sys = relationship('MonitoringSystem')


class InfoServTarifLink(Base):
    __tablename__ = 'info_serv_tarif_link'
    __table_args__ = (
        Index('unique_tarif_service', 'tarif_id', 'serv_id', unique=True),
    )

    id = Column(Integer, primary_key=True)
    tarif_id = Column(ForeignKey('info_serv_tarifs.tarif_id'), nullable=False)
    serv_id = Column(ForeignKey('information_services.serv_id'), nullable=False, index=True)

    serv = relationship('InformationService')
    tarif = relationship('InfoServTarif')


class InspectTerminal(Base):
    __tablename__ = 'inspect_terminals'
    __table_args__ = {'comment': 'Таблица по обходу терминалов'}

    inspect_id = Column(Integer, primary_key=True, comment='ID Инспекции')
    type_term = Column(VARCHAR(50), comment='Тип терминала')
    imei = Column(VARCHAR(100), comment='IMEIТерминала')
    iccid = Column(VARCHAR(100), comment='ICCID СИМкарты')
    vehicleId = Column(VARCHAR(50), comment='ID Как в СМ')
    vehicle_name = Column(VARCHAR(50), comment='Имя Объекта')
    client_name = Column(VARCHAR(400), comment='Имя клиента как в 1С')
    client_id = Column(Integer, comment='ИД клиента из клиентов БД')
    iccid_in_db = Column(Integer, comment='Наличие Сим карты в нашей БД\\r\\n0-Клментская сим\\r\\n1-наша')
    if_change_imei = Column(Integer, comment='Будет ли изменён IMEI у сим\\r\\n0-нет\\r\\n1-да')
    old_sim_imei = Column(VARCHAR(100), comment='Если не сходится IMEI в СИМ заносится сюда ')
    inspect_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Времяинспекции')
    monitoring_system = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Система Мониторинга')

    monitoring_system1 = relationship('MonitoringSystem')


class Invoicing(Base):
    __tablename__ = 'invoicing'
    __table_args__ = {'comment': 'Таблица для хранения информации о счетах-фактурах по объекту вытащенный из другой БД postgres'}

    invoic_id = Column(Integer, primary_key=True)
    system_monitorig_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Связь к системе мониторинга из ПУКС')
    system_object_id = Column(VARCHAR(200), nullable=False, comment='ID в системе мониторинга из ПУКС')
    puks_tarif = Column(Integer, comment='Тариф из ПУКС')
    add_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='дата')

    system_monitorig = relationship('MonitoringSystem')


class SensorBrand(Base):
    __tablename__ = 'sensor_brands'
    __table_args__ = {'comment': 'Таблица моделей датчиков'}

    id = Column(Integer, primary_key=True, comment='ID Модели')
    name = Column(VARCHAR(200), nullable=False, comment='Название модели')
    sensor_vendor_id = Column(ForeignKey('sensor_vendor.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Связь к Фирме изготовителя')
    model_type = Column(TINYINT, comment='Тип датчика: \\r\\n1 ДУТ.\\r\\n2 Температуры.\\r\\n3 Наклона.\\r\\n4 Индикатор.')

    sensor_vendor = relationship('SensorVendor')


class LoginUser(Base):
    __tablename__ = 'Login_users'
    __table_args__ = {'comment': 'Таблица для хранения информации о пользователях систем мониторинга'}

    id = Column(Integer, primary_key=True)
    client_name = Column(VARCHAR(200), comment='Старая колонка, при ведении excel таблицы')
    login = Column(VARCHAR(60), comment='логин')
    email = Column(VARCHAR(60), comment='почта')
    password = Column(VARCHAR(60), comment='пароль')
    date_create = Column(Date, comment='дата создания')
    system_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Ключ к системе мониторинга')
    contragent_id = Column(ForeignKey('Contragents.ca_id', ondelete='SET NULL', onupdate='RESTRICT'), index=True, comment='ID контрагента')
    comment_field = Column(VARCHAR(270), comment='Поле с комментариями')
    ca_uid = Column(VARCHAR(100), comment='Уникальный id контрагента')
    account_status = Column(TINYINT, nullable=False, server_default=text("'1'"), comment='Состояние учётки 0-остановлена, 1-не подтверждена но активна, 2-подтверждена и активна 3 -тестовая\\r\\n4- Учётка для учёта ТС\\r\\n\\r\\n')
    is_billing = Column(TINYINT, comment='Билинговый ли аккаунт\\r\\n0-не Билинговый\\r\\n1 - Билинговый')
    onec_contracts_id = Column(Integer, comment='ID договора')
    id_login_in_sys = Column(VARCHAR(200), comment='Ид пользователя в системе')
    last_entry = Column(TIMESTAMP, comment='Дата последнего входа\\r\\nПользователя')
    login_enabling = Column(TINYINT, comment='0-не активен\\r\\n1-активен')

    contragent = relationship('Contragent')
    system = relationship('MonitoringSystem')


class AuthGroupPermission(Base):
    __tablename__ = 'auth_group_permissions'
    __table_args__ = (
        Index('auth_group_permissions_group_id_permission_id_0cd325b0_uniq', 'group_id', 'permission_id', unique=True),
        {'comment': 'Таблица связи групп пользователей ЦМС с разрешениями'}
    )

    id = Column(BigInteger, primary_key=True)
    group_id = Column(ForeignKey('auth_group.id'), nullable=False, comment='Связь с группой пользователей ЦМС')
    permission_id = Column(ForeignKey('auth_permission.id'), nullable=False, index=True, comment='Связь с разрешениями действий в ЦМС')

    group = relationship('AuthGroup')
    permission = relationship('AuthPermission')


class AuthUserUserPermission(Base):
    __tablename__ = 'auth_user_user_permissions'
    __table_args__ = (
        Index('auth_user_user_permissions_user_id_permission_id_14a6b632_uniq', 'user_id', 'permission_id', unique=True),
        {'comment': 'Таблица связи пользователей с разрешениями в системе аутентификации ЦМС'}
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(ForeignKey('auth_user.id'), nullable=False)
    permission_id = Column(ForeignKey('auth_permission.id'), nullable=False, index=True)

    permission = relationship('AuthPermission')
    user = relationship('AuthUser')


class CaContact(Base):
    __tablename__ = 'ca_contacts'
    __table_args__ = {'comment': 'Таблица для хранения контактной информации Клиентов по тз'}

    ca_contact_id = Column(Integer, primary_key=True)
    ca_id = Column(ForeignKey('Contragents.ca_id'), index=True, comment='связь с id компании')
    ca_contact_name = Column(VARCHAR(255), comment='Имя контактного лица')
    ca_contact_surname = Column(VARCHAR(255), comment='Фамилия контактного лица')
    ca_contact_middlename = Column(VARCHAR(255), comment='Отчество контактного лица')
    ca_contact_cell_num = Column(VARCHAR(255), unique=True, comment='Сотовый телефон контакт. лица')
    ca_contact_work_num = Column(VARCHAR(255), comment='Рабочий телефон к.л.')
    ca_contact_email = Column(VARCHAR(255), comment='Электр.почт. к.л')
    ca_contact_position = Column(VARCHAR(255), comment='Должность к.л.')

    ca = relationship('Contragent')


class CaContract(Base):
    __tablename__ = 'ca_contracts'
    __table_args__ = {'comment': 'Таблица для хранения информации о контрактах по тз'}

    contract_id = Column(Integer, primary_key=True)
    ca_id = Column(ForeignKey('Contragents.ca_id'), index=True, comment='ID контрагента')
    contract_type = Column(VARCHAR(50), comment='Тип договора\\r\\nя бы сделал choice')
    contract_num_prefix = Column(VARCHAR(50), comment='Префикс номера договора')
    contract_num = Column(VARCHAR(50), comment='Номер договора')
    contract_payment_term = Column(VARCHAR(50), comment='условия оплаты')
    contract_payment_period = Column(VARCHAR(50), comment='Период оплаты')
    contract_start_date = Column(Date, comment='Дата заключения договора')
    contract_expired_date = Column(Date, comment='Дата завершения договора')

    ca = relationship('Contragent')


class CaObject(Base):
    __tablename__ = 'ca_objects'
    __table_args__ = {'comment': 'Таблица для хранения информации об объектах из систем мониторинга'}

    id = Column(Integer, primary_key=True)
    sys_mon_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID системы мониторинга')
    sys_mon_object_id = Column(VARCHAR(50), comment='ID объекта в системе мониторинга. Единственное за что можно зацепиться')
    object_name = Column(VARCHAR(70), comment='Название объекта')
    object_status = Column(ForeignKey('object_statuses.status_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Статус объекта ссылается к статусам')
    object_add_date = Column(DateTime, comment='Дата добавления объекта')
    object_last_message = Column(DateTime, comment='Дата последнего сообщения')
    object_margin = Column(Integer, comment='Надбавка к базовой цене объекта')
    owner_contragent = Column(VARCHAR(200), comment='Хозяин контрагент, как в системе мониторинга.')
    owner_user = Column(VARCHAR(255), comment='Хозяин юзер. Логин пользователя в системе мониторинга')
    imei = Column(VARCHAR(100), comment='идентификатор терминала')
    updated = Column(DateTime, comment='Когда изменён')
    object_created = Column(DateTime, comment='Дата создания в системе мониторинга ')
    parent_id_sys = Column(VARCHAR(200), comment='Id клиента в системе мониторинга')
    contragent_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)
    ca_uid = Column(VARCHAR(100), comment='Уникальный id контрагента')
    ok_desk_id = Column(Integer, comment='ID объекта в ОК-деске')
    addition_status_id = Column(TINYINT, comment='ID статуса доп')

    contragent = relationship('Contragent')
    object_status1 = relationship('ObjectStatus')
    sys_mon = relationship('MonitoringSystem')


class ClientsInSystemMonitor(Base):
    __tablename__ = 'clients_in_system_monitor'
    __table_args__ = {'comment': 'Таблица для хранения информации об id клиентов и id родителей клиентов в СМ не по ТЗ'}

    id = Column(Integer, primary_key=True)
    id_in_system_monitor = Column(VARCHAR(200), comment='Id клиента в системе мониторинга')
    name_in_system_monitor = Column(VARCHAR(200), comment='Имя клиента в системе мониторинга ')
    owner_id_sys_mon = Column(VARCHAR(200), comment='Id хозяина в системе мониторинга')
    system_monitor_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Id системы мониторинга ')
    client_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='id клиента')

    client = relationship('Contragent')
    system_monitor = relationship('MonitoringSystem')


class Device(Base):
    __tablename__ = 'devices'
    __table_args__ = {'comment': 'Таблица для хранения информации об устройствах запрограммированных IT отделом не по тз'}

    device_id = Column(Integer, primary_key=True)
    device_serial = Column(VARCHAR(100), nullable=False, unique=True, comment='Серийный номер устройства')
    device_imei = Column(VARCHAR(60), unique=True, comment='IMEI устройства')
    client_name = Column(VARCHAR(300), comment='Имя клиента')
    terminal_date = Column(DateTime, comment='Дата программирования терминала')
    devices_brand_id = Column(ForeignKey('devices_brands.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID Модели устройства ')
    name_it = Column(VARCHAR(50), comment='Имя програмировавшего терминал не актуальна')
    sys_mon_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID системы мониторинга')
    contragent_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID контрагента')
    coment = Column(VARCHAR(270), comment='Коментарии')
    itprogrammer_id = Column(ForeignKey('auth_user.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ссылается к программистам')
    device_owner = Column(TINYINT, comment='Принадлежность терминала:\\r\\n--1 МЫ\\r\\n--0 Клиент')

    contragent = relationship('Contragent')
    devices_brand = relationship('DevicesBrand')
    itprogrammer = relationship('AuthUser')
    sys_mon = relationship('MonitoringSystem')


class DevicesCommand(Base):
    __tablename__ = 'devices_commands'
    __table_args__ = {'comment': 'Таблица для хранения информации о командах для устройств не по ТЗ'}

    id = Column(Integer, primary_key=True)
    command = Column(VARCHAR(100), comment='сама команда')
    device_brand = Column(ForeignKey('devices_brands.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Id брэнда терминала')
    method = Column(VARCHAR(10), comment='тип отправки команды\\r\\n0 - смс\\r\\n1 - интернет\\r\\n2 - любым')
    description = Column(VARCHAR(300), comment='описание действия команды')

    devices_brand = relationship('DevicesBrand')


class DiscountClientLink(Base):
    __tablename__ = 'discount_client_link'
    __table_args__ = {'comment': 'Связка клиент скидки для клиентов'}

    dis_cl_link_id = Column(Integer, primary_key=True, comment='ID связи')
    cl_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID клиента')
    dis_id = Column(ForeignKey('discount_client.dis_cl_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID скидки')
    sys_mon_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ИД системы мониторинга')

    cl = relationship('Contragent')
    dis = relationship('DiscountClient')
    sys_mon = relationship('MonitoringSystem')


class DiscountRnicLink(Base):
    __tablename__ = 'discount_rnic_link'

    link_id = Column(Integer, primary_key=True)
    cl_rnic_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, unique=True, comment='Ид клиента для скидки, надбавки рниц')
    dis_rnic_id = Column(ForeignKey('discount_client.dis_cl_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Скидка или надбавка у рница')

    cl_rnic = relationship('Contragent')
    dis_rnic = relationship('DiscountClient')


class DiscountVideoSim(Base):
    __tablename__ = 'discount_video_sim'
    __table_args__ = (
        Index('unique_client_discount', 'client_id', 'discount_id', unique=True),
        {'comment': 'Скидки на сим-карты видеорегистраторов для клиентов'}
    )

    link_id = Column(Integer, primary_key=True, comment='ID связи')
    client_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, comment='ID клиента (Contragents.ca_id)')
    discount_id = Column(ForeignKey('discount_client.dis_cl_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID скидки (discount_client.dis_cl_id)')

    client = relationship('Contragent')
    discount = relationship('DiscountClient')


class EquipmentWarehouse(Base):
    __tablename__ = 'equipment_warehouse'
    __table_args__ = {'comment': 'Таблица склада'}

    id_unit = Column(BigInteger, primary_key=True, comment='Идентификатор записи')
    add_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время регистрации добавления товара на склад')
    serial_number = Column(VARCHAR(200), nullable=False, unique=True, comment='Серийный номер')
    availability = Column(TINYINT(1), nullable=False, server_default=text("'1'"), comment='Наличие на складе\\r\\n0- нет в наличии\\r\\n1- в наличии')
    terminal_model_id = Column(ForeignKey('devices_brands.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Реляционный id device')
    sensor_id = Column(ForeignKey('sensor_brands.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Реляция id к датчикам')
    delivery_date = Column(DateTime, comment='Дата выдачи')
    client_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Клиент как в 1С')
    comment = Column(VARCHAR(300), comment='коментарий')
    whom_issued = Column(VARCHAR(300), nullable=False, comment='Кому выдан')
    affiliation = Column(TINYINT, nullable=False, comment='Принадлежность к подразделению:\\r\\n0-Сервис\\r\\n1- мониторинг')

    client = relationship('Contragent')
    sensor = relationship('SensorBrand')
    terminal_model = relationship('DevicesBrand')


class InfoReportsSub(Base):
    __tablename__ = 'info_reports_subs'
    __table_args__ = {'comment': 'Таблица, кто подписан на получение отчётов из систем монитор'}

    id_subs = Column(Integer, primary_key=True)
    contragent_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Ид контрагента на подписке')
    sys_mon_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID системы мониторинга\\r\\nс которой отсылать отчёты')
    report_name = Column(Integer, nullable=False, comment='Название отчёта')

    contragent = relationship('Contragent')
    sys_mon = relationship('MonitoringSystem')


class InfoServPayRemindLog(Base):
    __tablename__ = 'info_serv_pay_remind_log'
    __table_args__ = (
        Index('pay_remind_client_date_UQ', 'contragent_id', 'pay_date', unique=True),
        {'comment': 'Напоминания менеджерам об оплате сервисов'}
    )

    id = Column(Integer, primary_key=True)
    contragent_id = Column(ForeignKey('Contragents.ca_id'), nullable=False, comment='Клиент (Contragents.ca_id)')
    pay_date = Column(Date, nullable=False, comment='Дата очередной оплаты, о которой напомнили (число начала подписки)')
    mail_to = Column(VARCHAR(500), comment='Кому ушло письмо')
    mail_sent_at = Column(DateTime, comment='Когда ушло письмо. NULL - ещё не ушло')
    okdesk_issue_id = Column(Integer, comment='Номер заявки в ОКДЕСК. NULL - ещё не создана')
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    contragent = relationship('Contragent')


class InfoServReportSetting(Base):
    __tablename__ = 'info_serv_report_settings'
    __table_args__ = (
        Index('report_settings_client_object_UQ', 'contragent_id', 'object_id', unique=True),
        {'comment': 'Пороги отчётов по холостому ходу и безопасному вождению'}
    )

    id = Column(Integer, primary_key=True)
    contragent_id = Column(ForeignKey('Contragents.ca_id'), nullable=False, comment='Клиент (Contragents.ca_id)')
    object_id = Column(Integer, nullable=False, server_default=text("'0'"), comment='Объект (ca_objects.id); 0 - все объекты клиента')
    speed_allowed = Column(SmallInteger, nullable=False, server_default=text("'110'"), comment='Допустимая скорость, км/ч: выше - превышение')
    speed_critical = Column(SmallInteger, nullable=False, server_default=text("'130'"), comment='Критическая скорость, км/ч')
    overspeed_min_sec = Column(SmallInteger, nullable=False, server_default=text("'10'"), comment='Превышение короче, сек, не считается (выбросы GPS)')
    idle_alert_pct = Column(DECIMAL(5, 2), nullable=False, server_default=text("'20.00'"), comment='Доля холостого хода от работы двигателя, %, с которой ТС выделяется в отчёте')
    comment = Column(VARCHAR(255), comment='Кто и зачем поменял пороги')
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    contragent = relationship('Contragent')


class ObjectSensor(Base):
    __tablename__ = 'object_sensors'
    __table_args__ = {'comment': 'Датчик'}

    sensor_id = Column(Integer, primary_key=True)
    sensor_type = Column(TINYINT, nullable=False, comment='Тип датчика:\\r\\n1ДУТ, 2Температуры3наклона')
    sensor_model_id = Column(ForeignKey('sensor_brands.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Модель датчика к моделям')
    sensor_technology = Column(TINYINT, nullable=False, comment='Подтип датчика:\\r\\n1аналоговый,2цифровой,\\r\\n3частотный')
    sensor_connect_type = Column(VARCHAR(255), comment='Тип подключения')
    client_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Связь с id Клиента')
    sensor_serial = Column(VARCHAR(100), unique=True, comment='Серийный номер датчика')
    name_installer = Column(VARCHAR(150), comment='Имя монтажника')
    installer_id = Column(Integer, comment='Id монтажника')

    client = relationship('Contragent')
    sensor_model = relationship('SensorBrand')


class SenderLogger(Base):
    __tablename__ = 'sender_logger'
    __table_args__ = {'comment': 'Таблица с рассылками'}

    send_id = Column(Integer, primary_key=True)
    send_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Время события рассылки')
    send_mail = Column(VARCHAR(20), comment='Почта рассылки')
    send_client_id = Column(ForeignKey('Contragents.ca_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Ид клиента БД_2')
    send_client_id_okdesk = Column(Integer, comment='ID клиента ОКДЕСК')
    send_req_okdesk_id = Column(Integer, comment='ID заявки в окдеск')
    send_text = Column(LONGTEXT, comment='Текст рассылки')

    send_client = relationship('Contragent')


class ShtrafovnetCar(Base):
    __tablename__ = 'shtrafovnet_cars'
    __table_args__ = {'comment': 'Связь записи ГРЗ/СТС с карточкой ТС в API Штрафов.Нет'}

    id = Column(Integer, primary_key=True)
    grz_record_id = Column(ForeignKey('info_serv_objects_grz.id_grz'), nullable=False, unique=True)
    shtrafovnet_company_id = Column(Integer, nullable=False)
    shtrafovnet_car_id = Column(Integer, nullable=False)
    last_sent_grz = Column(String(20), nullable=False)
    last_sent_sts = Column(String(20), nullable=False)
    status = Column(Enum('ok', 'error'), nullable=False)
    last_error = Column(Text)
    synced_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    grz_record = relationship('InfoServObjectsGrz')


class ShtrafovnetCompany(Base):
    __tablename__ = 'shtrafovnet_companies'
    __table_args__ = {'comment': 'Связь клиента billing_web с компанией в API Штрафов.Нет'}

    id = Column(Integer, primary_key=True)
    client_id = Column(ForeignKey('Contragents.ca_id'), nullable=False, unique=True)
    shtrafovnet_company_id = Column(Integer, nullable=False, unique=True)
    inn_used = Column(String(20), nullable=False)
    status = Column(Enum('created', 'linked_existing', 'error'), nullable=False)
    last_error = Column(Text)
    created_by_user_id = Column(Integer)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    client = relationship('Contragent')


class TransferClient(Base):
    __tablename__ = 'transfer_client'

    trans_id = Column(Integer, primary_key=True, comment='Id перевода')
    client_id = Column(ForeignKey('Contragents.ca_id'), nullable=False, index=True, comment='Id клиента')
    tranfer_sys_mon_id = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Id системы мониторинга на которую нужен перевод.')
    start_trans = Column(DateTime, nullable=False, comment='Начало перевода')
    end_trans = Column(DateTime, nullable=False, comment='Окончание перевода')
    terminal_command = Column(String(200), nullable=False, comment='Команда терминала')
    command_type = Column(TINYINT, nullable=False, comment='Тип комманды через что отправлять: 0 - API, 1 - sms')
    device_model_id = Column(ForeignKey('devices_brands.id'), nullable=False, index=True, comment='Id модели терминала')
    current_sys_mon = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Текущая система мониторинга(с какой системы перевести)')

    client = relationship('Contragent')
    monitoring_system = relationship('MonitoringSystem', primaryjoin='TransferClient.current_sys_mon == MonitoringSystem.mon_sys_id')
    device_model = relationship('DevicesBrand')
    tranfer_sys_mon = relationship('MonitoringSystem', primaryjoin='TransferClient.tranfer_sys_mon_id == MonitoringSystem.mon_sys_id')


class DevicesDiagnostic(Base):
    __tablename__ = 'devices_diagnostics'
    __table_args__ = {'comment': 'Таблица для хранения информации о диагностике устройств не по тз'}

    id = Column(Integer, primary_key=True)
    device_id = Column(ForeignKey('devices.device_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Отношение к терминалам')
    programmer_id = Column(ForeignKey('auth_user.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Отношение к программистам')
    brought = Column(TINYINT, nullable=False, comment='Принесён:\\r\\n0-от клиента\\r\\n1-после ремонта')
    comment = Column(VARCHAR(300), nullable=False, comment='Коментарий')
    accept_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='Дата приёма')
    transfer_date = Column(DateTime, comment='Дата передачи')
    whom_tranfer = Column(TINYINT, comment='Куда отдан:\\r\\n0 - клиенту\\r\\n1 - в ремонт')
    USB_check = Column(TINYINT(1), comment='Чек проверка USB')
    PWR_check = Column(TINYINT(1), comment='Чек проверка основного питания')
    PWR_AKB_check = Column(TINYINT(1), comment='Чек проверка резервного питания')
    FIRMWARE_check = Column(TINYINT(1), comment='Чек проверка прошивки')
    SATS_check = Column(TINYINT(1), comment='Чек проверка спутников')
    GSM_check = Column(TINYINT(1), comment='Чек проверка GSM')
    ONLINE_check = Column(TINYINT(1), comment='Чек проверка online')
    P485_check = Column(TINYINT(1), comment='Чек проверка 485 порта')
    DIGIT_PORT_check = Column(TINYINT(1), comment='Чек проверка цифровых входов')
    ANALOG_PORT_check = Column(TINYINT(1), comment='Чек проверка аналоговых входов')
    GSM_antenna_check = Column(TINYINT(1), comment='Чек GSM антенна в комплекте')
    GPS_antenna_check = Column(TINYINT(1), comment='Чек GPS антенна в комплекте')
    CABEL_check = Column(TINYINT(1), comment='Чек разъем питания в комплекте')
    SIM_check = Column(TINYINT(1), comment='Чек сим в комплекте')
    USB_comment = Column(VARCHAR(60), comment='Комментарий к проверке USB')
    PWR_comment = Column(VARCHAR(60), comment='Комментарий к проверке основного питания')
    PWR_AKB_comment = Column(VARCHAR(60), comment='Комментарий к проверке резервного питания')
    FIRMWARE_comment = Column(VARCHAR(60), comment='Комментарий к проверке прошивки')
    SATS_comment = Column(VARCHAR(60), comment='Комментарий к проверке наличия связи со спутниками')
    GSM_comment = Column(VARCHAR(60), comment='Комментарий к проверке связи GSM')
    ONLINE_comment = Column(VARCHAR(60), comment='Комментарий к проверке онлайна в системе мониторинга')
    P485_comment = Column(VARCHAR(60), comment='Комментарий к проверке 485 порта')
    DIGIT_PORT_comment = Column(VARCHAR(60), comment='Комментарий к проверке цифровых портов')
    ANALOG_PORT_comment = Column(VARCHAR(60), comment='Комментарий к проверке аналоговых портов')
    SIM_comment = Column(VARCHAR(60), comment='Комментарий к SIM карте')
    Sim_iccid = Column(VARCHAR(30))

    device = relationship('Device')
    programmer = relationship('AuthUser')


class DiscountObjLink(Base):
    __tablename__ = 'discount_obj_link'

    dis_obj_link_id = Column(Integer, primary_key=True)
    obj_id = Column(ForeignKey('ca_objects.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID объекта')
    dis_id = Column(ForeignKey('discount_obj.dis_obj_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID скидки под объекты')

    dis = relationship('DiscountObj')
    obj = relationship('CaObject')


class GroupObjectRetran(Base):
    __tablename__ = 'group_object_retrans'
    __table_args__ = {'comment': 'Таблица для сведения объектов и ретрансляторов'}

    id_group = Column(Integer, primary_key=True, comment='Айдишник')
    obj_id = Column(ForeignKey('ca_objects.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Айдишник объекта')
    retr_id = Column(ForeignKey('object_retranslators.retranslator_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Айдишник ретранслятора')

    obj = relationship('CaObject')
    retr = relationship('ObjectRetranslator')


class InfoServObj(Base):
    __tablename__ = 'info_serv_obj'
    __table_args__ = {'comment': 'Объекты с информационными сервисами'}

    serv_obj_id = Column(Integer, primary_key=True, comment='ID подписки')
    serv_obj_sys_mon_id = Column(ForeignKey('ca_objects.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Внутренний ID объекта\\r\\nБазы данных из СМ')
    info_obj_serv_id = Column(ForeignKey('information_services.serv_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='ID ведёт сервисам')
    subscription_start = Column(DateTime, nullable=False, comment='Время начала подписки')
    subscription_end = Column(DateTime, comment='Время окончания подписки')
    tel_num_user = Column(VARCHAR(11), comment='Телефонный номер с которого созданна услуга')
    service_counter = Column(Integer, nullable=False, comment='СЧЁТЧИК услуг\\r\\n0- мгновенно\\r\\n1-раз в день\\r\\n2-раз в неделю\\r\\n3-раз в месяц')
    stealth_type = Column(TINYINT, nullable=False, comment='0 - автоматический\\r\\n1 - с проверкой')
    monitoring_sys = Column(ForeignKey('monitoring_system.mon_sys_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True, comment='Система мониторинга')
    sys_id_obj = Column(VARCHAR(100), nullable=False, comment='ID объекта в системе мониторинга')
    sys_login = Column(VARCHAR(100), nullable=False, comment='Логин пользователя от системы мониторинга')
    sys_password = Column(VARCHAR(100), nullable=False, comment='Пароль пользователя от СМ')
    send_meth = Column(TINYINT, server_default=text("'0'"), comment='Способ отправки 0 - ОКДЕСК\\r\\n1 - MAIL')
    grouping_sign = Column(TINYINT, nullable=False, server_default=text("'0'"), comment='Есть ли группировка')
    testing_status = Column(TINYINT, server_default=text("'0'"), comment='0 - ТЕСТ\\r\\n1 - Абонентка')
    subs_day_send = Column(Integer, server_default=text("'7'"), comment='За сколько дней оповещать об окончании подписки')
    info_serv_tarif_id = Column(ForeignKey('info_serv_tarifs.tarif_id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID тарифов')
    date_create = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='Дата создания записи в таблице')
    pay_remind_days = Column(TINYINT, comment='За сколько дней до очередной даты оплаты (число начала подписки каждый месяц) напоминать менеджеру. NULL - не напоминать')
    pay_remind_manager_id = Column(ForeignKey('auth_user.id', ondelete='SET NULL', onupdate='RESTRICT'), index=True, comment='Кому напоминать: auth_user.id менеджера по продажам')

    info_obj_serv = relationship('InformationService')
    info_serv_tarif = relationship('InfoServTarif')
    monitoring_system = relationship('MonitoringSystem')
    pay_remind_manager = relationship('AuthUser')
    serv_obj_sys_mon = relationship('CaObject')


class ObjectVehicle(Base):
    __tablename__ = 'object_vehicles'
    __table_args__ = {'comment': 'Таблица для хранения информации об объектах-транспортных средствах'}

    vehicle_id = Column(Integer, primary_key=True)
    vehicle_object_id = Column(ForeignKey('ca_objects.id'), index=True, comment='привязка к объекту')
    vehicle_ca_id = Column(ForeignKey('Contragents.ca_id'), index=True, comment='привязка к контрагенту')
    vehicle_vendor_name = Column(VARCHAR(255), comment='производитель тс')
    vehicle_vendor_model = Column(VARCHAR(255), comment='марка тс')
    vehicle_year_of_manufacture = Column(VARCHAR(255), comment='дата выпуска тс')
    vehicle_gos_nomer = Column(VARCHAR(25), nullable=False, unique=True, comment='госномер')
    vehicle_gos_nomer_region = Column(VARCHAR(255), comment='регион')
    vehicle_type = Column(VARCHAR(255), comment='тип тс')
    vehicle_vin = Column(VARCHAR(255), comment='вин')

    vehicle_ca = relationship('Contragent')
    vehicle_object = relationship('CaObject')


class ServiceSubscriptionLog(Base):
    __tablename__ = 'service_subscription_log'
    __table_args__ = {'comment': 'Лог изменений сервисных подписок'}

    log_id = Column(Integer, primary_key=True, comment='ID записи лога')
    user_id = Column(ForeignKey('auth_user.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True, comment='ID пользователя')
    username = Column(VARCHAR(150), nullable=False, comment='Имя пользователя')
    object_id = Column(ForeignKey('ca_objects.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True, comment='ID объекта')
    action = Column(VARCHAR(50), nullable=False, comment='Действие')
    changes = Column(TEXT, comment='Изменения в JSON')
    change_time = Column(DateTime, index=True, server_default=text("CURRENT_TIMESTAMP"), comment='Время изменения')

    object = relationship('CaObject')
    user = relationship('AuthUser')


class SimCard(Base):
    __tablename__ = 'sim_cards'

    sim_id = Column(Integer, primary_key=True)
    sim_iccid = Column(VARCHAR(40), unique=True, comment='ICCID')
    sim_tel_number = Column(VARCHAR(40), comment='телефонный номер сим')
    client_name = Column(VARCHAR(270), comment='Имя клиента')
    sim_cell_operator = Column(ForeignKey('Cell_operator.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='Сотовый оператор(надо по ID)')
    sim_owner = Column(TINYINT(1), comment="1, 'Мы'\\r\\n0, 'Клиент'")
    sim_device_id = Column(ForeignKey('devices.device_id'), index=True, comment='ID к девайсам(devices)')
    sim_date = Column(DateTime, comment='Дата регистрации сим')
    status = Column(Integer, comment='Активность симки:\\r\\n0-списана, 1-активна, 2-приостан, 3-первичная блокировка, 4-статус неизвестен,\\r\\n5 - Сезонная блокировка')
    terminal_imei = Column(VARCHAR(25), index=True, comment='IMEI терминала в который вставлена симка')
    contragent_id = Column(ForeignKey('Contragents.ca_id', ondelete='SET NULL', onupdate='SET NULL'), index=True, comment='ID контрагента')
    ca_uid = Column(VARCHAR(100), comment='Уникальный id контрагента')
    itprogrammer_id = Column(ForeignKey('auth_user.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True, comment='ID сотрудника програмировавшего терминал')
    block_start = Column(DateTime, comment='Начало блокировки')
    block_end = Column(DateTime, comment='Предварительный конец блокировки')
    operator_imei = Column(String(25, 'utf8mb3_unicode_ci'), index=True, comment='IMEI устройства по данным оператора')
    operator_device_name = Column(String(100, 'utf8mb3_unicode_ci'), comment='Модель устройства по данным оператора')
    operator_last_activity = Column(DateTime, index=True, comment='Последняя сетевая активность SIM по данным оператора')
    operator_apn = Column(String(100, 'utf8mb3_unicode_ci'), comment='APN последней сессии')
    operator_mcc_mnc = Column(String(10, 'utf8mb3_unicode_ci'), comment='Сеть последней сессии MCC+MNC, виден роуминг')
    operator_blockings = Column(String(255, 'utf8mb3_unicode_ci'), comment='Блокировки оператора через запятую')
    operator_rate_plan = Column(String(120, 'utf8mb3_unicode_ci'), comment='Тарифный план по данным оператора')
    operator_rate_plan_ends = Column(DateTime, comment='Когда заканчивается тариф')
    operator_sync_at = Column(DateTime, index=True, comment='Когда последний раз обновляли данные от оператора')
    sim_imsi = Column(String(20, 'utf8mb3_unicode_ci'), index=True, comment='IMSI SIM-карты по данным оператора')
    mts_telematics_100mb = Column(TINYINT(1), comment="Телематика. Пакет 100 МБ")
    operator_block_code = Column(String(10, 'utf8mb3_unicode_ci'), comment='Код типа блокировки у оператора (МТС: BL0005, BL0008)')
    operator_last_ip = Column(String(45, 'utf8mb3_unicode_ci'), comment='Последний IP-адрес SIM по данным оператора')
    operator_lat = Column(DECIMAL(10, 6), comment='Широта по данным сотовой сети')
    operator_lon = Column(DECIMAL(10, 6), comment='Долгота по данным сотовой сети')
    operator_loc_range = Column(Integer, comment='Радиус неопределённости координат, метры')

    contragent = relationship('Contragent')
    itprogrammer = relationship('AuthUser')
    Cell_operator = relationship('CellOperator')
    sim_device = relationship('Device')


class SimImeiHistory(Base):
    __tablename__ = 'sim_imei_history'
    __table_args__ = {'comment': 'История смены IMEI терминала по данным операторов'}

    id = Column(Integer, primary_key=True)
    sim_id = Column(ForeignKey('sim_cards.sim_id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, index=True, comment='Ссылка на sim_cards.sim_id')
    sim_iccid = Column(String(40), index=True, comment='ICCID на момент записи')
    old_imei = Column(String(25), comment='Какой IMEI был')
    new_imei = Column(String(25), comment='Какой стал')
    device_name = Column(String(100), comment='Модель устройства по словам оператора')
    source = Column(String(20), nullable=False, comment='Кто сообщил: mts / beeline / tele2')
    noticed_at = Column(DateTime, nullable=False, index=True, server_default=text("CURRENT_TIMESTAMP"), comment='Когда заметили смену')

    sim = relationship('SimCard')
