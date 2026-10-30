# Обновление 2 — по итогам выгрузки живых API (30.10.2026)

Ставить после первого обновления. Порядок важен: шаг 2 требует колонок из шага 1.

## 1. Миграция

`migrations/002_operator_fields.sql` — выполнить в DBeaver на `suntel`.

Добавляет в `sim_cards`: `sim_imsi`, `operator_block_code`, `operator_last_ip`,
`operator_lat`, `operator_lon`, `operator_loc_range`, индекс по IMSI и две вьюхи —
`v_sim_gde_stoit` и `v_sim_polnota_dannyh`.

Проверено на копии вашего дампа: 001 и 002 накатываются подряд без ошибок,
итого 14 вьюх в базе.

## 2. Перегенерировать модели

    env/bin/python database/generate_models.py

В `models.SimCard` должны появиться шесть новых колонок. Если sqlacodegen
споткнётся, добавьте вручную (не забудьте `DECIMAL` в импорты из sqlalchemy):

    sim_imsi = Column(VARCHAR(20), comment='IMSI SIM-карты по данным оператора')
    operator_block_code = Column(VARCHAR(10), comment='Код типа блокировки у оператора')
    operator_last_ip = Column(VARCHAR(45), comment='Последний IP-адрес SIM')
    operator_lat = Column(DECIMAL(10, 6), comment='Широта по данным сотовой сети')
    operator_lon = Column(DECIMAL(10, 6), comment='Долгота по данным сотовой сети')
    operator_loc_range = Column(Integer, comment='Радиус неопределённости координат, метры')

## 3. Заменить файлы

    beeline_entry.py
    clear_mts_entry.py
    data_collector/beeline_collector.py
    database/crud.py
    pytest.ini
    tests/mocks.py
    tests/test_beeline.py
    tests/test_mts.py

## 4. Настройки

`BILINE_PAGE_SIZE` больше ни на что не влияет — живой API поле `perpage`
игнорирует и всегда отдаёт по 30 записей. Строку можно удалить из `.env`.

`BILINE_DETECT_DEVICE` оставьте выключенным (`0`). IMEI теперь приходит прямо
в списке; detect_device нужен только ради более подробного названия модели
(«SIMCOM Wireless Solutions Co Ltd SIM800C» вместо «SIMCOM SIM800») и стоит
одного запроса на симку.

`BILINE_RATE_PER_MIN` можно поднять до 600: лимит 60/мин у Билайна только
на `/oauth/token`, на рабочих методах — 600/мин.

## 5. Проверка

    env/bin/python -m pytest          # должно быть 156 passed
    env/bin/python main.py --now beeline
    env/bin/python main.py --now mts

После прогона Билайна:

```sql
SELECT * FROM v_sim_polnota_dannyh;
```

У оператора «Билайн» должно стать около 1295 SIM, из них примерно три четверти
с `operator_imei` (у списанных устройства нет), и у всех — `sim_imsi`.

Затем сверка:

```sql
SELECT sverka_s_nashimi, COUNT(*) FROM v_sim_imei_check
WHERE operator = 'Билайн' GROUP BY sverka_s_nashimi;
```

Строки «РАСХОЖДЕНИЕ» — это симки, которые физически стоят не в том терминале,
что записан у нас. Ради них всё и затевалось.

## Что изменилось в коде

**`beeline_entry.py`** — разбор списка переписан под живую структуру. Из
вложенного `sim` берутся `imei`, `device_name`, `last_activity_dt`, `apn`,
`imsi`, `last_ip`; координаты — из `cell_location`, причём нулевые значения
трактуются как «неизвестно», а не как точка в Гвинейском заливе. Пустые строки,
которые Билайн шлёт вместо `null`, приводятся к NULL. Добор IMEI через
detect_device превратился в уточнение модели и по умолчанию не работает.

**`clear_mts_entry.py`** — обход начинается с `pageNum=1` (ноль возвращает ту же
первую страницу, то есть первая сотня обрабатывалась дважды). Блокировки
определяются по коду `externalID` (BL0005 — добровольная, BL0008 —
первоначальная) с откатом на название, если код незнакомый. Время блокировки
сохраняется целиком вместо обнуления до полуночи, `endDateTime` пишется в
`block_end`, заглушка `0001-01-01` — как NULL. IMSI и ICCID достаются из
`productCharacteristic` по имени поля, а не по индексу.

**`database/crud.py`** — умеет писать новые поля; изменение IMSI и `block_end`
попадает в `global_logging`.

**Тесты** — моки переписаны по живым ответам: Билайн отдаёт по 30 записей
независимо от `perpage`, МТС считает страницы с единицы, блокировки приходят с
кодами. Добавлены тесты на IMEI из списка, координаты, IMSI, пустые строки и на
то, что detect_device не дёргается без необходимости. Было 139 тестов, стало 156.
