ALTER TABLE sim_cards
    ADD COLUMN mts_telematics_100mb TINYINT(1) NULL DEFAULT NULL
    COMMENT 'Телематика. Пакет 100 МБ: 1 есть, 0 нет, NULL не проверено';
