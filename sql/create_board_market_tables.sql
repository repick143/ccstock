-- ============================================================
-- ccstock: 板块日行情 & 个股-板块映射表
-- 数据来源：
--   - stock_board_industry_index_ths() → 行业指数日行情（同花顺）
--   - stock_board_concept_index_ths() → 概念指数日行情（同花顺）
--   - stock_board_industry_cons_em()  → 个股-行业成分股映射（东方财富，需重试）
--   - stock_board_concept_cons_em()  → 个股-概念成分股映射（东方财富，需重试）
-- 使用方式：mysql -u root -p ccstock < sql/create_board_market_tables.sql
-- ============================================================

USE ccstock;

-- -----------------------------------------------------------
-- 行业日行情表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS industry_daily (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    board_code      VARCHAR(20)     NOT NULL                        COMMENT "行业板块代码，如 881121（对应 board_industry.code）",
    trade_date      DATE            NOT NULL                        COMMENT "交易日",
    open_price      DECIMAL(14,4)   NOT NULL                        COMMENT "开盘指数点位",
    high_price      DECIMAL(14,4)   NOT NULL                        COMMENT "最高指数点位",
    low_price       DECIMAL(14,4)   NOT NULL                        COMMENT "最低指数点位",
    close_price     DECIMAL(14,4)   NOT NULL                        COMMENT "收盘指数点位",
    volume          BIGINT          NOT NULL                        COMMENT "成交量（股）",
    amount          DECIMAL(22,2)   NOT NULL                        COMMENT "成交额（元）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_ind_daily (board_code, trade_date) COMMENT "同一板块同一天唯一",
    KEY idx_ind_code (board_code),
    KEY idx_ind_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股行业板块日行情（同花顺）";


-- -----------------------------------------------------------
-- 概念日行情表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS concept_daily (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    board_code      VARCHAR(20)     NOT NULL                        COMMENT "概念板块代码，如 309121（对应 board_concept.code）",
    trade_date      DATE            NOT NULL                        COMMENT "交易日",
    open_price      DECIMAL(14,4)   NOT NULL                        COMMENT "开盘指数点位",
    high_price      DECIMAL(14,4)   NOT NULL                        COMMENT "最高指数点位",
    low_price       DECIMAL(14,4)   NOT NULL                        COMMENT "最低指数点位",
    close_price     DECIMAL(14,4)   NOT NULL                        COMMENT "收盘指数点位",
    volume          BIGINT          NOT NULL                        COMMENT "成交量（股）",
    amount          DECIMAL(22,2)   NOT NULL                        COMMENT "成交额（元）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_conc_daily (board_code, trade_date) COMMENT "同一板块同一天唯一",
    KEY idx_conc_code (board_code),
    KEY idx_conc_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股概念板块日行情（同花顺）";


-- -----------------------------------------------------------
-- 个股-行业成分股映射表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_industry_map (
    stock_code      VARCHAR(10)     NOT NULL                        COMMENT "A 股代码，如 601869",
    industry_code   VARCHAR(20)     NOT NULL                        COMMENT "行业板块代码，如 881121（对应 board_industry.code）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",

    PRIMARY KEY (stock_code, industry_code) COMMENT "同只股票在同一行业唯一",
    KEY idx_map_ind_code (industry_code),
    KEY idx_map_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股个股-行业板块成分股映射（东方财富）";


-- -----------------------------------------------------------
-- 个股-概念成分股映射表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_concept_map (
    stock_code      VARCHAR(10)     NOT NULL                        COMMENT "A 股代码，如 601869",
    concept_code    VARCHAR(20)     NOT NULL                        COMMENT "概念板块代码，如 309121（对应 board_concept.code）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",

    PRIMARY KEY (stock_code, concept_code) COMMENT "同只股票在同一概念唯一",
    KEY idx_map_conc_code (concept_code),
    KEY idx_map_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股个股-概念板块成分股映射（东方财富）";
