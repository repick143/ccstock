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
    code            VARCHAR(200)    NOT NULL                        COMMENT "概念板块代码；来源有原始代码则用原始代码，否则用来源内概念名称",
    name            VARCHAR(200)    NOT NULL                        COMMENT "概念板块名称，如 AI PC（来自 akshare stock_board_concept_name_ths）",
    source          VARCHAR(50)     NOT NULL DEFAULT "ths" COMMENT "数据来源，如 ths / eastmoney / mootdx",
    source_code     VARCHAR(200)    DEFAULT NULL                    COMMENT "来源侧原始概念代码或名称",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_board_conc_source_code (source, code) COMMENT "同一来源内概念代码唯一",
    KEY idx_board_conc_name (name) COMMENT "概念板块名称索引",
    KEY idx_board_conc_source (source) COMMENT "概念来源索引"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股概念板块分类（同花顺）";


-- -----------------------------------------------------------
-- 板块-个股成分映射表
-- -----------------------------------------------------------

CREATE TABLE IF NOT EXISTS board_stock_map (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY     COMMENT "自增主键",
    board_type      VARCHAR(20)     NOT NULL                        COMMENT "板块类型：industry / concept",
    board_code      VARCHAR(20)     DEFAULT NULL                    COMMENT "板块代码，来源可用时写入",
    board_name      VARCHAR(200)    NOT NULL                        COMMENT "板块名称",
    stock_code      VARCHAR(10)     NOT NULL                        COMMENT "A 股代码，如 601869",
    stock_name      VARCHAR(50)     DEFAULT NULL                    COMMENT "股票简称",
    source          VARCHAR(20)     NOT NULL                        COMMENT "数据来源，如 akshare_em / mootdx",
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间",
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT "记录更新时间",

    UNIQUE KEY uk_board_stock (board_type, board_name, stock_code) COMMENT "同一板块和股票只保留一条映射",
    KEY idx_board_stock_code (stock_code) COMMENT "股票代码索引",
    KEY idx_board_type_name (board_type, board_name) COMMENT "板块类型和名称索引"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT="A 股行业/概念板块与个股成分映射";
