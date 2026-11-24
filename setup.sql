-- =============================================================
-- setup.sql - ハンズオン共通の事前セットアップ
-- 前提: load.sql を実行済みであること
-- 業種を差し替える場合は、Step 3 のパス industries/manufacturing と Step 4 のテーブル定義を変更する
-- =============================================================

-- -----------------------------------------------
-- Step 1. クロスリージョン推論・ウェアハウス
-- -----------------------------------------------
USE ROLE ACCOUNTADMIN;

-- 東京リージョンで未提供のモデル・機能を使えるようにする
ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

-- Model RBAC が有効なアカウントでは、Cortex Search の埋め込みモデルに権限が要る
-- （2026-11-24 にトライアルで "Not authorized to access model" になったため付与する）
GRANT APPLICATION ROLE SNOWFLAKE."CORTEX-MODEL-ROLE-SNOWFLAKE-ARCTIC-EMBED-L-V2.0" TO ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS COWORK_HANDSON_WH
    WAREHOUSE_SIZE      = 'XSMALL'
    AUTO_SUSPEND        = 60
    AUTO_RESUME         = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT             = 'CoWork ハンズオン用ウェアハウス';
USE WAREHOUSE COWORK_HANDSON_WH;

-- -----------------------------------------------
-- Step 2. データベース・スキーマ・ステージ
-- -----------------------------------------------
CREATE OR REPLACE DATABASE COWORK_HANDSON_DB
    COMMENT = 'CoWork ハンズオン: 演習データ';
CREATE OR REPLACE SCHEMA COWORK_HANDSON_DB.ANALYTICS
    COMMENT = 'CoWork ハンズオン: 構造化データと文書';
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;

CREATE OR REPLACE STAGE data_stage
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    DIRECTORY  = (ENABLE = TRUE)
    COMMENT    = 'CSV 用ステージ';

-- AI_PARSE_DOCUMENT はサーバー側暗号化（SNOWFLAKE_SSE）のステージを推奨
CREATE OR REPLACE STAGE doc_stage
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
    DIRECTORY  = (ENABLE = TRUE)
    COMMENT    = '作業手順書・不具合報告書・設備マニュアルの PDF';

-- -----------------------------------------------
-- Step 3. Git リポジトリからステージへファイルをコピー
-- -----------------------------------------------
-- BEGIN GIT COPY（tests/verify_on_account.sh はこの範囲を PUT に置き換える）
COPY FILES INTO @data_stage
FROM @COWORK_HANDSON_GIT_DB.GIT.cowork_handson_git_repo/branches/main/
PATTERN = 'industries/manufacturing/data/.*[.]csv';

COPY FILES INTO @doc_stage
FROM @COWORK_HANDSON_GIT_DB.GIT.cowork_handson_git_repo/branches/main/industries/manufacturing/docs/;
-- END GIT COPY

ALTER STAGE data_stage REFRESH;
ALTER STAGE doc_stage REFRESH;

-- -----------------------------------------------
-- Step 4. テーブル作成とデータ投入
-- -----------------------------------------------
CREATE OR REPLACE FILE FORMAT csv_format
    TYPE                         = 'CSV'
    SKIP_HEADER                  = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    ENCODING                     = 'UTF8'
    COMMENT                      = 'ヘッダー付き UTF-8 CSV';

CREATE OR REPLACE TABLE plants (
    plant_id   VARCHAR COMMENT '工場ID',
    plant_name VARCHAR COMMENT '工場名',
    location   VARCHAR COMMENT '所在地'
) COMMENT = '工場マスタ';

CREATE OR REPLACE TABLE lines (
    line_id   VARCHAR COMMENT 'ラインID（L01〜L06）',
    plant_id  VARCHAR COMMENT '工場ID',
    line_name VARCHAR COMMENT 'ライン名',
    process   VARCHAR COMMENT '工程（プレス・溶接・射出成形・組立・塗装・検査）'
) COMMENT = '製造ラインマスタ';

CREATE OR REPLACE TABLE products (
    product_id    VARCHAR COMMENT '製品ID',
    product_name  VARCHAR COMMENT '製品名',
    category      VARCHAR COMMENT '製品カテゴリ',
    line_id       VARCHAR COMMENT '製造するラインID',
    unit_cost_jpy NUMBER  COMMENT '製造原価（円/個）'
) COMMENT = '製品マスタ';

CREATE OR REPLACE TABLE equipment (
    equipment_id   VARCHAR COMMENT '設備ID',
    line_id        VARCHAR COMMENT 'ラインID',
    equipment_name VARCHAR COMMENT '設備名',
    model          VARCHAR COMMENT '型式',
    installed_date DATE    COMMENT '導入日'
) COMMENT = '設備マスタ';

CREATE OR REPLACE TABLE production (
    production_date DATE    COMMENT '生産日（平日のみ）',
    shift           VARCHAR COMMENT 'シフト（日勤・夜勤）',
    line_id         VARCHAR COMMENT 'ラインID',
    product_id      VARCHAR COMMENT '製品ID',
    planned_qty     NUMBER  COMMENT '計画数',
    produced_qty    NUMBER  COMMENT '生産数（不良を含む）',
    good_qty        NUMBER  COMMENT '良品数'
) COMMENT = '生産実績（日・シフト・製品単位）';

CREATE OR REPLACE TABLE defects (
    production_date DATE    COMMENT '生産日',
    shift           VARCHAR COMMENT 'シフト',
    line_id         VARCHAR COMMENT 'ラインID',
    product_id      VARCHAR COMMENT '製品ID',
    defect_type     VARCHAR COMMENT '不良の種類（ショートショット・ヒケ・バリなど）',
    defect_qty      NUMBER  COMMENT '不良数'
) COMMENT = '不良実績（日・シフト・製品・不良種類単位）';

CREATE OR REPLACE TABLE downtime (
    downtime_id     VARCHAR       COMMENT '停止ID',
    equipment_id    VARCHAR       COMMENT '設備ID',
    start_at        TIMESTAMP_NTZ COMMENT '停止開始日時',
    duration_min    NUMBER        COMMENT '停止時間（分）',
    reason_category VARCHAR       COMMENT '停止理由の分類（故障・段取替え・材料待ち・定期保全）',
    description     VARCHAR       COMMENT '停止内容の記述'
) COMMENT = '設備停止記録';

CREATE OR REPLACE TABLE documents (
    file_name    VARCHAR COMMENT 'PDF のファイル名（doc_stage 上のパス）',
    doc_type     VARCHAR COMMENT '文書種別（作業手順書・不具合報告書・設備マニュアル）',
    title        VARCHAR COMMENT '文書タイトル',
    line_id      VARCHAR COMMENT '対象ラインID',
    equipment_id VARCHAR COMMENT '対象設備ID',
    issued_date  DATE    COMMENT '発行日'
) COMMENT = '文書台帳（Part 2 で AI_EXTRACT の結果と照合する正解データ）';

COPY INTO plants     FROM @data_stage/industries/manufacturing/data/plants.csv     FILE_FORMAT = csv_format;
COPY INTO lines      FROM @data_stage/industries/manufacturing/data/lines.csv      FILE_FORMAT = csv_format;
COPY INTO products   FROM @data_stage/industries/manufacturing/data/products.csv   FILE_FORMAT = csv_format;
COPY INTO equipment  FROM @data_stage/industries/manufacturing/data/equipment.csv  FILE_FORMAT = csv_format;
COPY INTO production FROM @data_stage/industries/manufacturing/data/production.csv FILE_FORMAT = csv_format;
COPY INTO defects    FROM @data_stage/industries/manufacturing/data/defects.csv    FILE_FORMAT = csv_format;
COPY INTO downtime   FROM @data_stage/industries/manufacturing/data/downtime.csv   FILE_FORMAT = csv_format;
COPY INTO documents  FROM @data_stage/industries/manufacturing/data/documents.csv  FILE_FORMAT = csv_format;

-- -----------------------------------------------
-- Step 5. 確認（件数が 0 のテーブルがなければ成功）
-- -----------------------------------------------
SELECT 'plants' AS table_name, COUNT(*) AS row_count FROM plants
UNION ALL SELECT 'lines', COUNT(*) FROM lines
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'equipment', COUNT(*) FROM equipment
UNION ALL SELECT 'production', COUNT(*) FROM production
UNION ALL SELECT 'defects', COUNT(*) FROM defects
UNION ALL SELECT 'downtime', COUNT(*) FROM downtime
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'doc_stage (PDF)', COUNT(*) FROM DIRECTORY(@doc_stage);
