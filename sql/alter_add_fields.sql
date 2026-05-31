-- ============================================================
-- 为 stock_daily 表补充 pre_close / chg_amt / chg_pct 字段
-- 执行：mysql -u root -p < sql/alter_add_fields.sql
-- ========================================== ==================

USE ccstock;

ALTER TABLE stock_daily
    ADD COLUMN pre_close  DECIMAL(12,2) DEFAULT NULL COMMENT '昨收价（前一交易日收盘价）',
    ADD COLUMN chg_amt    DECIMAL(12,2) DEFAULT NULL COMMENT '涨跌额（收盘价 - 昨收价）',
    ADD COLUMN chg_pct    DECIMAL(8,4)  DEFAULT NULL COMMENT '涨跌幅（涨跌额 / 昨收价 * 100）',
    ADD INDEX idx_pre_close (pre_close) COMMENT '昨收价索引'
;
