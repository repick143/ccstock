-- ============================================================
-- ccstock: 个股基础信息表
-- 数据来源：
--   - stock_info_a_code_name() → 股票代码+名称（批量，快速）
--   - stock_financial_abstract_ths() → 财务指标（逐只，较慢）
-- 使用方式：mysql -u root -p ccstock < sql/create_stock_info_tables.sql
-- ============================================================

USE ccstock;

CREATE TABLE IF NOT EXISTS stock_info (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    stock_code      VARCHAR(10)     NOT NULL                        COMMENT "A 股代码，如 601869",
    stock_name      VARCHAR(50)     DEFAULT NULL                    COMMENT "股票简称，如 长飞光纤",
    eps             DECIMAL(12,4)   DEFAULT NULL                    COMMENT "基本每股收益（来自 stock_financial_abstract_ths）",
    bvps            DECIMAL(12,4)   DEFAULT NULL                    COMMENT "每股净资产（来自 stock_financial_abstract_ths）",
    roe             DECIMAL(12,4)   DEFAULT NULL                    COMMENT "净资产收益率%%（来自 stock_financial_abstract_ths）",
    net_profit      DECIMAL(20,4)   DEFAULT NULL                    COMMENT "净利润，单位万元（来自 stock_financial_abstract_ths）",
    revenue         DECIMAL(20,4)   DEFAULT NULL                    COMMENT "营业总收入，单位万元（来自 stock_financial_abstract_ths）",
    gross_margin    DECIMAL(12,4)   DEFAULT NULL                    COMMENT "销售毛利率%%（来自 stock_financial_abstract_ths）",
    net_margin      DECIMAL(12,4)   DEFAULT NULL                    COMMENT "销售净利率%%（来自 stock_financial_abstract_ths）",
    debt_ratio      DECIMAL(12,4)   DEFAULT NULL                    COMMENT "资产负债率%%（来自 stock_financial_abstract_ths）",
    report_period   DATE            DEFAULT NULL                    COMMENT "财务数据报告期（来自 stock_financial_abstract_ths）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_stock_code (stock_code) COMMENT "股票代码唯一",
    KEY idx_stock_name (stock_name) COMMENT "股票名称索引"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股个股基础信息（代码+名称+财务指标）";
