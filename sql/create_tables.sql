-- ============================================================
-- ccstock: A 股日行情数据表
-- 数据来源：mootdx（通达信行情接口）
-- 使用方式：mysql -u root -p < sql/create_tables.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS ccstock
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ccstock;

CREATE TABLE IF NOT EXISTS stock_daily (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT '自增主键',
    stock_code      VARCHAR(10)     NOT NULL                        COMMENT 'A 股代码，如 601869',
    trade_date      DATE            NOT NULL                        COMMENT '交易日',
    open_price      DECIMAL(12,2)   NOT NULL                        COMMENT '开盘价',
    high_price      DECIMAL(12,2)   NOT NULL                        COMMENT '最高价',
    low_price       DECIMAL(12,2)   NOT NULL                        COMMENT '最低价',
    close_price     DECIMAL(12,2)   NOT NULL                        COMMENT '收盘价',
    volume          BIGINT          NOT NULL                        COMMENT '成交量（股）',
    amount          DECIMAL(20,2)   NOT NULL                        COMMENT '成交额（元）',
    pre_close       DECIMAL(12,2)   DEFAULT NULL                    COMMENT '昨收价（前一交易日收盘价）',
    chg_amt         DECIMAL(12,2)   DEFAULT NULL                    COMMENT '涨跌额（收盘-昨收）',
    chg_pct         DECIMAL(8,4)    DEFAULT NULL                    COMMENT '涨跌幅（涨跌额/昨收*100）',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    UNIQUE KEY uk_stock_date (stock_code, trade_date) COMMENT '同一只股票同一天只能有一条记录',
    KEY idx_stock_code (stock_code) COMMENT '股票代码索引，用于按代码筛选',
    KEY idx_trade_date (trade_date) COMMENT '交易日索引，用于按日期范围筛选'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='A 股日线行情数据（来自通达信）';

