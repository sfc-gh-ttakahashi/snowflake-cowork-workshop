# Part 2 : Cortex Search で文書を検索できるようにする（40分）

## シナリオ

工場には、作業手順書・不具合報告書・設備マニュアルが PDF で保管されています。
この Part では、PDF の本文を検索できるように **Cortex Search Service** を作ります。

処理の流れは次のとおりです。

| ステップ | 使う機能 | 出力 |
|---|---|---|
| 1. PDF を解析する | `AI_PARSE_DOCUMENT` | 文書ごとの本文（Markdown） |
| 2. 本文をチャンクに分ける | `SPLIT_TEXT_RECURSIVE_CHARACTER` | 検索の単位となる短い文章 |
| 3. 文書に属性を付ける | `AI_EXTRACT` | 文書種別・ライン・設備 |
| 4. 検索サービスを作る | `CREATE CORTEX SEARCH SERVICE` | ハイブリッド検索（ベクトル＋キーワード） |

```sql
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COWORK_HANDSON_WH;
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;
```

---
## 1. PDF を確認する

```sql
-- doc_stage にある PDF の一覧
SELECT relative_path, size, last_modified
FROM DIRECTORY(@doc_stage)
ORDER BY relative_path;
```

---
## 2. AI_PARSE_DOCUMENT で PDF を解析する

`LAYOUT` モードは、見出しや表の構造を Markdown として残します。

```sql
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
```

> 表が `| 調査項目 | 結果 |` の形で残っていることを確認してください。

---
## 3. 本文をチャンクに分ける

検索は文書全体ではなく、チャンク（短い文章）単位で行います。
`markdown` を指定すると、見出しの切れ目を優先して分割します。
今回の文書は短いので 300 文字にしています。実業務の文書では、数百〜千文字程度から試します。

```sql
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
```

---
## 4. AI_EXTRACT で文書に属性を付ける

検索結果を「不具合報告書だけ」「L03 の文書だけ」に絞り込めるよう、文書ごとに属性を抽出します。

```sql
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
```

---
## 5. Cortex Search Service を作る

`ATTRIBUTES` に指定した列で、検索結果を絞り込めるようになります。
埋め込みモデルには、日本語に対応した `snowflake-arctic-embed-l-v2.0` を使います。

```sql
CREATE OR REPLACE TABLE doc_chunks
    COMMENT = 'Cortex Search の検索対象（チャンクと属性）'
AS
WITH labeled AS (
    SELECT
        a.*,
        REPLACE(a.file_name, '.pdf', '') AS doc_no
    FROM doc_attributes AS a
)
SELECT
    c.file_name,
    c.chunk_no,
    l.doc_no,
    -- 引用に表示する見出し。文書番号・文書種別・タイトルを並べる（タイトルに含まれる文書番号は除く）
    l.doc_no || '（' || l.doc_type || '）' || TRIM(REPLACE(REPLACE(l.title, l.doc_no, ''), '不具合報告書', '')) AS doc_label,
    l.doc_type,
    l.line_id,
    l.equipment_id,
    -- 先頭に見出しを付けると、チャンク単体でも何の文書か分かる
    '【' || doc_label || '】' || CHR(10) || c.chunk AS chunk
FROM doc_chunks_raw AS c
JOIN labeled AS l ON l.file_name = c.file_name;

-- 見出しを確認する
SELECT DISTINCT doc_label FROM doc_chunks ORDER BY doc_label;

CREATE OR REPLACE CORTEX SEARCH SERVICE mfg_doc_search
    ON chunk
    ATTRIBUTES doc_type, line_id, equipment_id
    WAREHOUSE = COWORK_HANDSON_WH
    TARGET_LAG = '1 day'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    COMMENT = '作業手順書・不具合報告書・設備マニュアルの検索'
AS
SELECT chunk, file_name, chunk_no, doc_no, doc_label, doc_type, line_id, equipment_id
FROM doc_chunks;
```

> `file_name` は doc_stage 上の PDF のパスです。Part 3 で Agent に渡すと、CoWork の引用から元の PDF を開けるようになります。

---
## 6. 検索を試す

```sql
-- 自然文で検索する
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH',
        '{"query": "ショートショットが増えた原因", "columns": ["doc_label", "chunk"], "limit": 3}'
    )
):results AS results;
```

```sql
-- 属性で絞り込む（不具合報告書だけを対象にする）
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        'COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH',
        '{"query": "ロボットが止まる", "columns": ["doc_label", "doc_type", "chunk"],
          "filter": {"@eq": {"doc_type": "不具合報告書"}}, "limit": 3}'
    )
):results AS results;
```

> **間に合わなかった場合:** `industries/manufacturing/search_answer.sql` を「すべて実行」すると、
> この Part の手順 2〜5 を一括で実行できます。
