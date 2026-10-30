ALTER TABLE sim_cards
  ADD COLUMN operator_imei           VARCHAR(25)  NULL COMMENT 'IMEI устройства по данным оператора',
  ADD COLUMN operator_device_name    VARCHAR(100) NULL COMMENT 'Модель устройства по данным оператора',
  ADD COLUMN operator_last_activity  DATETIME     NULL COMMENT 'Последняя сетевая активность SIM по данным оператора',
  ADD COLUMN operator_apn            VARCHAR(100) NULL COMMENT 'APN последней сессии',
  ADD COLUMN operator_mcc_mnc        VARCHAR(10)  NULL COMMENT 'Сеть последней сессии MCC+MNC, виден роуминг',
  ADD COLUMN operator_blockings      VARCHAR(255) NULL COMMENT 'Блокировки оператора через запятую',
  ADD COLUMN operator_rate_plan      VARCHAR(120) NULL COMMENT 'Тарифный план по данным оператора',
  ADD COLUMN operator_rate_plan_ends DATETIME     NULL COMMENT 'Когда заканчивается тариф',
  ADD COLUMN operator_sync_at        DATETIME     NULL COMMENT 'Когда последний раз обновляли данные от оператора';

CREATE INDEX idx_sim_terminal_imei    ON sim_cards (terminal_imei);
CREATE INDEX idx_sim_operator_imei    ON sim_cards (operator_imei);
CREATE INDEX idx_sim_operator_sync    ON sim_cards (operator_sync_at);
CREATE INDEX idx_sim_operator_activity ON sim_cards (operator_last_activity);

CREATE TABLE sim_imei_history (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  sim_id      INT          NOT NULL COMMENT 'Ссылка на sim_cards.sim_id',
  sim_iccid   VARCHAR(40)      NULL COMMENT 'ICCID на момент записи',
  old_imei    VARCHAR(25)      NULL COMMENT 'Какой IMEI был',
  new_imei    VARCHAR(25)      NULL COMMENT 'Какой стал',
  device_name VARCHAR(100)     NULL COMMENT 'Модель устройства по словам оператора',
  source      VARCHAR(20)  NOT NULL COMMENT 'Кто сообщил: mts / beeline / tele2',
  noticed_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Когда заметили смену',
  KEY idx_hist_sim (sim_id),
  KEY idx_hist_iccid (sim_iccid),
  KEY idx_hist_time (noticed_at),
  CONSTRAINT fk_hist_sim FOREIGN KEY (sim_id) REFERENCES sim_cards (sim_id)
    ON DELETE CASCADE ON UPDATE RESTRICT
) COMMENT='История смены IMEI терминала по данным операторов';
CREATE OR REPLACE VIEW v_sim_imei_check AS
SELECT
    sc.sim_id, sc.sim_iccid, sc.sim_tel_number,
    co.name AS operator,
    sc.terminal_imei  AS imei_u_nas,
    sc.operator_imei  AS imei_u_operatora,
    sc.operator_device_name,
    sc.operator_last_activity,
    obj.obektov_s_etim_imei,
    obj.poslednee_soobshenie_monitoring,
    ca.ca_name, sc.client_name,
    CASE
        WHEN sc.operator_imei IS NULL                        THEN 'оператор IMEI не отдал'
        WHEN sc.terminal_imei IS NULL OR sc.terminal_imei='' THEN 'у нас IMEI не прописан'
        WHEN sc.terminal_imei = sc.operator_imei             THEN 'совпадает'
        ELSE 'РАСХОЖДЕНИЕ'
    END AS sverka_s_nashimi,
    CASE
        WHEN sc.operator_imei IS NULL              THEN 'нечего сверять'
        WHEN obj.obektov_s_etim_imei IS NULL       THEN 'в мониторинге объекта нет'
        WHEN obj.imei = sc.operator_imei           THEN 'совпадает'
        ELSE 'РАСХОЖДЕНИЕ'
    END AS sverka_s_monitoringom
FROM sim_cards sc
LEFT JOIN Cell_operator co ON co.id = sc.sim_cell_operator
LEFT JOIN Contragents  ca ON ca.ca_id = sc.contragent_id
LEFT JOIN (
    SELECT imei, COUNT(*) AS obektov_s_etim_imei,
           MAX(object_last_message) AS poslednee_soobshenie_monitoring
    FROM ca_objects WHERE imei IS NOT NULL AND imei <> '' GROUP BY imei
) obj ON obj.imei = sc.terminal_imei
WHERE sc.status IN (1,2,3);

-- =====================================================================
--  Активные симки, которые молчат дольше недели
-- =====================================================================
CREATE OR REPLACE VIEW v_sim_molchit AS
SELECT sc.sim_iccid, sc.sim_tel_number, co.name AS operator,
    sc.terminal_imei, sc.operator_imei, sc.operator_device_name,
    sc.operator_last_activity,
    TIMESTAMPDIFF(DAY, sc.operator_last_activity, NOW()) AS dney_molchit,
    ca.ca_name, sc.client_name
FROM sim_cards sc
LEFT JOIN Cell_operator co ON co.id = sc.sim_cell_operator
LEFT JOIN Contragents  ca ON ca.ca_id = sc.contragent_id
WHERE sc.status = 1 AND sc.operator_last_activity IS NOT NULL
  AND sc.operator_last_activity < NOW() - INTERVAL 7 DAY
ORDER BY sc.operator_last_activity;

-- =====================================================================
--  Мусор в terminal_imei: 283 записи на 30.10.2026
--  (204 шестизначных, 26 двенадцатизначных, тексты вроде «тестовая»)
-- =====================================================================
CREATE OR REPLACE VIEW v_sim_imei_musor AS
SELECT sim_id, sim_iccid, sim_tel_number, sim_cell_operator, terminal_imei, client_name,
    CASE
        WHEN terminal_imei NOT REGEXP '^[0-9]+$' THEN 'не число'
        WHEN LENGTH(terminal_imei) <> 15         THEN CONCAT('длина ', LENGTH(terminal_imei), ' вместо 15')
    END AS chto_ne_tak
FROM sim_cards
WHERE terminal_imei IS NOT NULL AND terminal_imei <> ''
  AND (terminal_imei NOT REGEXP '^[0-9]+$' OR LENGTH(terminal_imei) <> 15);
