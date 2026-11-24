# Part 3 : Cortex Agent を作り CoWork で使う（25分）

## シナリオ

Part 1 で作った Semantic View（構造化データ）と、Part 2 で作った Cortex Search（文書）を
1 つの Agent にまとめ、CoWork から質問できるようにします。

| ツール | 種類 | 答えられること |
|---|---|---|
| `production_analyst` | Cortex Analyst（Semantic View） | 不良率・生産数・停止時間などの数値 |
| `document_search` | Cortex Search | 不具合の原因・対策、作業手順、設備の保守方法 |
| `code_execution` | コード実行 | HTML レポートの作成、グラフの加工 |

```sql
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COWORK_HANDSON_WH;
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;
```

---
## 1. Agent を作成する

```sql
CREATE OR REPLACE AGENT mfg_agent
    COMMENT = '製造業ハンズオン: 生産・品質・設備のデータと現場文書に答えるエージェント'
    PROFILE = '{"display_name": "製造現場アシスタント"}'
FROM SPECIFICATION
$$
models:
  orchestration: auto

instructions:
  response: |
    日本語で回答してください。数値の比較や推移は、できるだけグラフで示してください。
    不良率と計画達成率は百分率で示してください。
    文書を根拠にした場合は、文書のタイトルを明記してください。
  orchestration: |
    数値（生産数・不良率・計画達成率・停止回数・停止時間）の質問には production_analyst を使ってください。
    原因・対策・手順・保守方法の質問には document_search を使ってください。
    「なぜ」「原因は」を含む質問では、まず production_analyst で数値の変化を確かめ、
    次に document_search で該当するライン・設備の不具合報告書を探してください。
    HTML レポートの作成を頼まれた場合は code_execution を使ってください。
  sample_questions:
    - question: "ライン別の月次不良率の推移をグラフで見せて"
    - question: "9月に L03 の不良率が上がった原因は？"
    - question: "組立ロボットのサーボアラームの対処方法は？"

tools:
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "production_analyst"
      description: "工場・ライン・製品・設備ごとの生産実績、不良実績、設備停止記録を集計する"
  - tool_spec:
      type: "cortex_search"
      name: "document_search"
      description: "作業手順書・不具合報告書・設備マニュアルの本文を検索する"
  - tool_spec:
      type: "code_execution"
      name: "code_execution"

tool_resources:
  production_analyst:
    semantic_view: "COWORK_HANDSON_DB.ANALYTICS.MFG_SEMANTIC_VIEW"
    execution_environment:
      type: "warehouse"
      warehouse: "COWORK_HANDSON_WH"
  document_search:
    search_service: "COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH"
    max_results: 5
    title_column: "title"
    id_column: "file_name"
    columns_and_descriptions:
      chunk:
        description: "文書の本文の一部"
        type: "string"
        searchable: true
        filterable: false
      doc_type:
        description: "文書種別。値は 作業手順書・不具合報告書・設備マニュアル のいずれか"
        type: "string"
        searchable: false
        filterable: true
      line_id:
        description: "対象ラインID（L01〜L06）"
        type: "string"
        searchable: false
        filterable: true
      equipment_id:
        description: "対象設備ID（例: EQ-L03-02）"
        type: "string"
        searchable: false
        filterable: true
  code_execution: {}
$$;
```

---
## 2. CoWork に Agent を追加する

CoWork に表示する Agent は、アカウントに 1 つある CoWork オブジェクトに登録します。

```sql
-- CoWork オブジェクトがなければ作成する（すでにあれば何もしない）
CREATE SNOWFLAKE INTELLIGENCE IF NOT EXISTS SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT;
```

```sql
ALTER SNOWFLAKE INTELLIGENCE SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT
    ADD AGENT COWORK_HANDSON_DB.ANALYTICS.mfg_agent;
```

---
## 3. CoWork で動作を確認する

1. Snowsight の左メニューから **AI & ML » CoWork** を開く（別タブで開きます）
2. Agent の選択欄で **製造現場アシスタント** を選ぶ
3. 次の 3 つを順に質問する

| 質問 | 確認すること |
|---|---|
| ライン別の月次不良率の推移をグラフで見せて | Agent が `production_analyst` を使い、折れ線グラフを表示する。L03 の 9 月以降の上昇が見える |
| 9月に L03 の不良率が上がった原因は？ | Agent が数値を確認したあとに `document_search` を使い、NCR-2026-0912（金型温度調節機のヒーター劣化）を引用する |
| 組立ロボットのサーボアラームの対処方法は？ | Agent が作業手順書と保守マニュアルを引用する |

> 回答の下にある **思考過程（Thinking）** を開くと、Agent がどのツールをどの順で使ったかを確認できます。
> 期待どおりのツールが使われない場合は、Agent の `instructions.orchestration` を見直します。

Part 4 では、この Agent を使って自由に分析し、HTML レポートとダッシュボードを作ります。
