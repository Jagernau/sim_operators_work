-- =====================================================================
--  Вторая миграция: поля, которые операторы реально отдают.
--  Состав проверен по выгрузке живых API от 30.10.2026.
--  Накатывать после 001_operator_data.sql.
-- =====================================================================

-- IMSI приходит и от МТС (productCharacteristic), и от Билайна (sim.imsi).
-- Жёстко привязан к симке, удобен для сверки с личным кабинетом.
ALTER TABLE sim_cards
  ADD COLUMN sim_imsi VARCHAR(20) NULL COMMENT 'IMSI SIM-карты по данным оператора';

-- Код типа блокировки МТС: BL0005 — добровольная, BL0008 — первоначальная.
-- Храним код, а не название: название оператор может изменить.
ALTER TABLE sim_cards
  ADD COLUMN operator_block_code VARCHAR(10) NULL COMMENT 'Код типа блокировки у оператора (МТС: BL0005, BL0008)';

-- Последний IP, который оператор выдал симке (Билайн sim.last_ip).
ALTER TABLE sim_cards
  ADD COLUMN operator_last_ip VARCHAR(45) NULL COMMENT 'Последний IP-адрес SIM по данным оператора';

-- Координаты по сотовой сети. Билайн отдаёт их прямо в списке SIM,
-- в cell_location, вместе с радиусом неопределённости в метрах.
ALTER TABLE sim_cards
  ADD COLUMN operator_lat DECIMAL(10, 6) NULL COMMENT 'Широта по данным сотовой сети',
  ADD COLUMN operator_lon DECIMAL(10, 6) NULL COMMENT 'Долгота по данным сотовой сети',
  ADD COLUMN operator_loc_range INT NULL COMMENT 'Радиус неопределённости координат, метры';

CREATE INDEX idx_sim_imsi ON sim_cards (sim_imsi);

-- =====================================================================
--  Где симка физически не там, где объект в мониторинге
-- =====================================================================

CREATE OR REPLACE VIEW v_sim_gde_stoit AS
SELECT
    sc.sim_iccid,
    sc.sim_tel_number,
    co.name AS operator,
    sc.terminal_imei            AS imei_u_nas,
    sc.operator_imei            AS imei_u_operatora,
    sc.operator_device_name     AS model_ustroystva,
    sc.operator_last_activity,
    sc.operator_lat,
    sc.operator_lon,
    sc.operator_loc_range       AS tochnost_metrov,
    sc.operator_apn,
    sc.operator_last_ip,
    ca.ca_name,
    sc.client_name
FROM sim_cards sc
LEFT JOIN Cell_operator co ON co.id = sc.sim_cell_operator
LEFT JOIN Contragents  ca ON ca.ca_id = sc.contragent_id
WHERE sc.operator_lat IS NOT NULL
ORDER BY sc.operator_last_activity DESC;

-- =====================================================================
--  Сводка: что оператор вообще про нас знает
-- =====================================================================

CREATE OR REPLACE VIEW v_sim_polnota_dannyh AS
SELECT
    co.name AS operator,
    COUNT(*)                                        AS vsego_sim,
    SUM(sc.operator_imei IS NOT NULL)               AS s_imei_operatora,
    SUM(sc.terminal_imei IS NOT NULL
        AND sc.terminal_imei <> '')                 AS s_imei_nashim,
    SUM(sc.terminal_imei IS NOT NULL
        AND sc.operator_imei IS NOT NULL
        AND sc.terminal_imei <> sc.operator_imei)   AS rashozhdeniy,
    SUM(sc.sim_imsi IS NOT NULL)                    AS s_imsi,
    SUM(sc.operator_last_activity IS NOT NULL)      AS s_aktivnostyu,
    SUM(sc.operator_lat IS NOT NULL)                AS s_koordinatami,
    MAX(sc.operator_sync_at)                        AS poslednyaya_sverka
FROM sim_cards sc
LEFT JOIN Cell_operator co ON co.id = sc.sim_cell_operator
GROUP BY co.name
ORDER BY vsego_sim DESC;
