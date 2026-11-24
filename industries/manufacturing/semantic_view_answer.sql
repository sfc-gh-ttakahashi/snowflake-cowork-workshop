-- =============================================================
-- semantic_view_answer.sql - Part 1 の正解例
-- CoCo で作成できなかった場合、または Part 2 以降に追いつく場合に実行する
-- =============================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COWORK_HANDSON_WH;
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;

CREATE OR REPLACE SEMANTIC VIEW mfg_semantic_view
  TABLES (
    plants AS COWORK_HANDSON_DB.ANALYTICS.PLANTS
      PRIMARY KEY (plant_id)
      WITH SYNONYMS = ('工場', '拠点')
      COMMENT = '工場マスタ',
    lines AS COWORK_HANDSON_DB.ANALYTICS.LINES
      PRIMARY KEY (line_id)
      WITH SYNONYMS = ('ライン', '製造ライン', '工程')
      COMMENT = '製造ラインマスタ',
    products AS COWORK_HANDSON_DB.ANALYTICS.PRODUCTS
      PRIMARY KEY (product_id)
      WITH SYNONYMS = ('製品', '品目', '品番')
      COMMENT = '製品マスタ',
    equipment AS COWORK_HANDSON_DB.ANALYTICS.EQUIPMENT
      PRIMARY KEY (equipment_id)
      WITH SYNONYMS = ('設備', '機械', '装置')
      COMMENT = '設備マスタ',
    production AS COWORK_HANDSON_DB.ANALYTICS.PRODUCTION
      WITH SYNONYMS = ('生産実績', '出来高')
      COMMENT = '生産実績（日・シフト・製品単位）',
    defects AS COWORK_HANDSON_DB.ANALYTICS.DEFECTS
      WITH SYNONYMS = ('不良実績', '不具合', '品質不良')
      COMMENT = '不良実績（日・シフト・製品・不良種類単位）',
    downtime AS COWORK_HANDSON_DB.ANALYTICS.DOWNTIME
      PRIMARY KEY (downtime_id)
      WITH SYNONYMS = ('設備停止', 'チョコ停', 'ダウンタイム')
      COMMENT = '設備停止記録'
  )
  -- products (line_id) から lines への関係は定義しない。
  -- production から lines への経路が 2 本になり、ライン別の集計がエラーになるため
  RELATIONSHIPS (
    lines_to_plants      AS lines (plant_id)           REFERENCES plants,
    equipment_to_lines   AS equipment (line_id)        REFERENCES lines,
    production_to_lines  AS production (line_id)       REFERENCES lines,
    production_to_products AS production (product_id)  REFERENCES products,
    defects_to_lines     AS defects (line_id)          REFERENCES lines,
    defects_to_products  AS defects (product_id)       REFERENCES products,
    downtime_to_equipment AS downtime (equipment_id)   REFERENCES equipment
  )
  FACTS (
    production.planned_qty  AS planned_qty  COMMENT = '計画数',
    production.produced_qty AS produced_qty COMMENT = '生産数（不良を含む）',
    production.good_qty     AS good_qty     COMMENT = '良品数',
    production.scrap_qty    AS produced_qty - good_qty COMMENT = '不良数（生産数 - 良品数）',
    defects.defect_qty      AS defect_qty   COMMENT = '不良種類別の不良数',
    downtime.duration_min   AS duration_min COMMENT = '停止時間（分）'
  )
  DIMENSIONS (
    plants.plant_name    AS plant_name    WITH SYNONYMS = ('工場名') COMMENT = '工場名',
    lines.line_id        AS line_id       COMMENT = 'ラインID（L01〜L06）',
    lines.line_name      AS line_name     WITH SYNONYMS = ('ライン名') COMMENT = 'ライン名',
    lines.process        AS process       WITH SYNONYMS = ('工程名') COMMENT = '工程（プレス・溶接・射出成形・組立・塗装・検査）',
    products.product_name AS product_name WITH SYNONYMS = ('製品名', '品名') COMMENT = '製品名',
    products.category    AS category      COMMENT = '製品カテゴリ',
    equipment.equipment_id   AS equipment_id   COMMENT = '設備ID',
    equipment.equipment_name AS equipment_name WITH SYNONYMS = ('設備名') COMMENT = '設備名',
    production.production_date AS production_date WITH SYNONYMS = ('生産日', '日付') COMMENT = '生産日',
    production.production_month AS DATE_TRUNC('MONTH', production_date) WITH SYNONYMS = ('月', '生産月') COMMENT = '生産月',
    production.shift     AS shift         WITH SYNONYMS = ('勤務帯') COMMENT = 'シフト（日勤・夜勤）',
    -- ディメンション名は列名と揃える。別名にすると Cortex Analyst が元の列名で SQL を作り、エラーになる
    defects.production_date AS production_date WITH SYNONYMS = ('不良発生日') COMMENT = '不良が発生した生産日',
    defects.defect_month AS DATE_TRUNC('MONTH', production_date) COMMENT = '不良が発生した月',
    defects.defect_type  AS defect_type   WITH SYNONYMS = ('不良種類', '不良モード') COMMENT = '不良の種類',
    downtime.start_at    AS start_at      COMMENT = '停止開始日時',
    downtime.downtime_month AS DATE_TRUNC('MONTH', start_at) COMMENT = '停止が発生した月',
    downtime.reason_category AS reason_category WITH SYNONYMS = ('停止理由') COMMENT = '停止理由の分類（故障・段取替え・材料待ち・定期保全）',
    downtime.description AS description   COMMENT = '停止内容の記述'
  )
  METRICS (
    production.total_planned  AS SUM(production.planned_qty)  COMMENT = '計画数の合計',
    production.total_produced AS SUM(production.produced_qty) WITH SYNONYMS = ('生産量', '生産数') COMMENT = '生産数の合計',
    production.total_good     AS SUM(production.good_qty)     WITH SYNONYMS = ('良品数') COMMENT = '良品数の合計',
    production.defect_rate    AS SUM(production.scrap_qty) / NULLIF(SUM(production.produced_qty), 0)
      WITH SYNONYMS = ('不良率') COMMENT = '不良率 = 不良数 / 生産数（0〜1）',
    production.plan_achievement_rate AS SUM(production.good_qty) / NULLIF(SUM(production.planned_qty), 0)
      WITH SYNONYMS = ('計画達成率', '達成率') COMMENT = '計画達成率 = 良品数 / 計画数（0〜1）',
    defects.total_defects     AS SUM(defects.defect_qty)      COMMENT = '不良種類別の不良数の合計',
    downtime.downtime_count   AS COUNT(downtime.downtime_id)  WITH SYNONYMS = ('停止回数') COMMENT = '停止回数',
    downtime.total_downtime_min AS SUM(downtime.duration_min) WITH SYNONYMS = ('停止時間') COMMENT = '停止時間の合計（分）'
  )
  COMMENT = '製造業ハンズオン: 生産・品質・設備停止の分析用セマンティックビュー'
  AI_SQL_GENERATION '日本語で質問されることを前提とする。不良率と計画達成率は 0〜1 の比率なので、回答では百分率に直して示す。期間の指定がない場合は 2026-04-01〜2026-10-31 の全期間を対象にする。'
  AI_VERIFIED_QUERIES (
    monthly_defect_rate_by_line AS (
      QUESTION 'ライン別の月次不良率の推移を教えて'
      SQL 'SELECT DATE_TRUNC(''MONTH'', p.production_date) AS production_month, p.line_id,
             SUM(p.produced_qty - p.good_qty) / NULLIF(SUM(p.produced_qty), 0) AS defect_rate
           FROM __production AS p
           GROUP BY 1, 2
           ORDER BY 1, 2'
    )
  );

-- 動作確認: L03 の月次不良率（9 月以降に上がっていれば正しい）
SELECT * FROM SEMANTIC_VIEW(
    mfg_semantic_view
    DIMENSIONS production.production_month, lines.line_id
    METRICS production.defect_rate
    WHERE lines.line_id = 'L03'
) ORDER BY production_month;
