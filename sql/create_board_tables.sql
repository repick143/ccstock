-- ============================================================
-- ccstock: 行业 & 概念板块数据表
-- 数据来源：akshare（同花顺板块分类，_ths 系列接口）
-- 使用方式：mysql -u root -p ccstock < sql/create_board_tables.sql
-- ============================================================

USE ccstock;

-- -----------------------------------------------------------
-- 行业板块表（来自同花顺行业分类）
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS board_industry (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    code            VARCHAR(20)     NOT NULL                        COMMENT "行业板块代码，如 881121（来自 akshare stock_board_industry_name_ths）",
    name            VARCHAR(100)    NOT NULL                        COMMENT "行业板块名称，如 半导体（来自 akshare stock_board_industry_name_ths）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_board_ind_code (code) COMMENT "行业板块代码唯一",
    KEY idx_board_ind_name (name) COMMENT "行业板块名称索引"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股行业板块分类（同花顺）";


-- -----------------------------------------------------------
-- 概念板块表（来自同花顺概念分类）
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS board_concept (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    code            VARCHAR(20)     NOT NULL                        COMMENT "概念板块代码，如 309121（来自 akshare stock_board_concept_name_ths）",
    name            VARCHAR(200)    NOT NULL                        COMMENT "概念板块名称，如 AI PC（来自 akshare stock_board_concept_name_ths）",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_board_conc_code (code) COMMENT "概念板块代码唯一",
    KEY idx_board_conc_name (name) COMMENT "概念板块名称索引"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股概念板块分类（同花顺）";
