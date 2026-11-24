-- search_answer.sql - Part 2 を一括で実行する（labs/part2_cortex_search.md から自動生成。直接編集しない）

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COWORK_HANDSON_WH;
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;

-- doc_stage にある PDF の一覧
SELECT relative_path, size, last_modified
FROM DIRECTORY(@doc_stage)
ORDER BY relative_path;

CREATE OR REPLACE TABLE parsed_docs
    COMMENT = 'PDF を AI_PARSE_DOCUMENT（LAYOUT）で解析した本文'
AS
SELECT
    relative_path AS file_name,
    AI_PARSE_DOCUMENT(
        TO_FILE('@doc_stage', relative_path),
        {'mode': 'LAYOUT'}
    ):content::VARCHAR AS content
FROM DIRECTORY(@doc_stage);

SELECT file_name, LEFT(content, 300) AS preview FROM parsed_docs ORDER BY file_name;

CREATE OR REPLACE TABLE doc_chunks_raw
    COMMENT = '解析した本文を 300 文字単位（重なり 50 文字）に分割したチャンク'
AS
SELECT
    d.file_name,
    c.index       AS chunk_no,
    c.value::VARCHAR AS chunk
FROM parsed_docs AS d,
    LATERAL FLATTEN(
        input => SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(d.content, 'markdown', 300, 50)
    ) AS c;

SELECT file_name, COUNT(*) AS chunks FROM doc_chunks_raw GROUP BY file_name ORDER BY file_name;

CREATE OR REPLACE TABLE doc_attributes
    COMMENT = 'AI_EXTRACT で文書の本文から抽出した属性'
AS
SELECT
    file_name,
    r:response:doc_type::VARCHAR     AS doc_type,
    r:response:line_id::VARCHAR      AS line_id,
    r:response:equipment_id::VARCHAR AS equipment_id,
    -- LAYOUT モードの解析結果は見出しに # が付くため取り除く
    REGEXP_REPLACE(r:response:title::VARCHAR, '^#+\\s*', '') AS title
FROM (
    SELECT
        file_name,
        AI_EXTRACT(
            text => content,
            responseFormat => {
                'doc_type': '文書種別は何ですか？作業手順書・不具合報告書・設備マニュアルのいずれかで答えてください',
                'line_id': '対象ラインのID（L01 のような形式）は何ですか？',
                'equipment_id': '対象設備のID（EQ-L03-01 のような形式）は何ですか？',
                'title': '文書のタイトルは何ですか？'
            }
        ) AS r
    FROM parsed_docs
);

-- 文書台帳（documents テーブル）と照合する。一致しない行があれば、その文書の本文を確認する
SELECT
    a.file_name,
    a.doc_type, d.doc_type AS expected_doc_type,
    a.line_id, d.line_id AS expected_line_id,
    a.equipment_id, d.equipment_id AS expected_equipment_id,
    (a.doc_type = d.doc_type AND a.line_id = d.line_id AND a.equipment_id = d.equipment_id) AS matched
FROM doc_attributes AS a
JOIN documents AS d ON d.file_name = a.file_name
ORDER BY a.file_name;

CREATE OR REPLACE TABLE doc_chunks
    COMMENT = 'Cortex Search の検索対象（チャンクと属性）'
AS
SELECT
    c.file_name,
    c.chunk_no,
    a.title,
    a.doc_type,
    a.line_id,
    a.equipment_id,
    -- 先頭にタイトルを付けると、チャンク単体でも何の文書か分かる
    '【' || a.title || '】' || CHR(10) || c.chunk AS chunk
FROM doc_chunks_raw AS c
JOIN doc_attributes AS a ON a.file_name = c.file_name;

CREATE OR REPLACE CORTEX SEARCH SERVICE mfg_doc_search
    ON chunk
    ATTRIBUTES doc_type, line_id, equipment_id
    WAREHOUSE = COWORK_HANDSON_WH
    TARGET_LAG = '1 day'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    COMMENT = '作業手順書・不具合報告書・設備マニュアルの検索'
AS
SELECT chunk, file_name, chunk_no, title, doc_type, line_id, equipment_id
FROM doc_chunks;

-- 自然文で検索する
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH',
        '{"query": "ショートショットが増えた原因", "columns": ["title", "chunk"], "limit": 3}'
    )
):results AS results;

-- 属性で絞り込む（不具合報告書だけを対象にする）
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH',
        '{"query": "ロボットが止まる", "columns": ["title", "doc_type", "chunk"],
          "filter": {"@eq": {"doc_type": "不具合報告書"}}, "limit": 3}'
    )
):results AS results;
