# Part 1 : Semantic View を CoCo で作る（30分）

## シナリオ

あなたは製造業の **生産技術・品質保証の担当者** です。
工場には生産実績・不良実績・設備停止記録が溜まっていますが、
「不良率」「計画達成率」などの指標の定義はそれぞれの担当者の Excel の中にしかありません。

この Part では、AI がデータの意味を理解できるように **Semantic View（セマンティックビュー）** を作ります。
Semantic View は、テーブルの意味、テーブル同士の関係、指標の計算式、同義語を定義するオブジェクトです。
CoWork はこの定義をもとに、自然言語の質問を SQL に変換します。

| テーブル | 内容 | 件数 |
|---|---|---|
| `plants` / `lines` / `products` / `equipment` | 工場・ライン・製品・設備のマスタ | 2 / 6 / 8 / 11 |
| `production` | 生産実績（日・シフト・製品単位） | 2,448 |
| `defects` | 不良実績（不良の種類別） | 6,932 |
| `downtime` | 設備停止記録 | 122 |

```sql
-- コンテキスト設定
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COWORK_HANDSON_WH;
USE SCHEMA COWORK_HANDSON_DB.ANALYTICS;
```

---
## 1. データを確認する

```sql
-- ライン別の生産数と不良数
SELECT
    l.line_id,
    l.line_name,
    SUM(p.produced_qty)              AS produced_qty,
    SUM(p.produced_qty - p.good_qty) AS defect_qty
FROM production AS p
JOIN lines AS l ON l.line_id = p.line_id
GROUP BY l.line_id, l.line_name
ORDER BY l.line_id;
```

```sql
-- 設備停止記録の例
SELECT * FROM downtime ORDER BY start_at LIMIT 10;
```

---
## 2. CoCo に Semantic View の作成を依頼する

1. Snowsight の左メニューから **Projects » Workspaces** を開く
2. 画面右側の **CoCo** のパネルを開く
3. 次の依頼文を貼り付けて送信する

```text
COWORK_HANDSON_DB.ANALYTICS の plants, lines, products, equipment, production, defects, downtime の
7 テーブルから、製造現場の分析に使うセマンティックビュー mfg_semantic_view を作成してください。

- 指標: 生産数、良品数、不良率（(生産数 - 良品数) / 生産数）、計画達成率（良品数 / 計画数）、停止回数、停止時間
- 同義語: 日本語の現場用語（例: 設備停止 = チョコ停、ダウンタイム）を付ける
- production から lines への結合経路は 1 本にする（products 経由の関係は作らない）
- 作成前に定義を見せて、確認を取ってから作成する
```

> CoCo の出力は受講者ごとに少しずつ違います。CoCo が提示した定義を読み、
> 指標の計算式と、テーブル同士の関係が正しいかを確認してから作成を承認してください。

> **CoCo で作成できなかった場合:** `industries/manufacturing/semantic_view_answer.sql` を開いて「すべて実行」すると、
> 正解例の Semantic View を作成できます。

---
## 3. Semantic Studio で定義を確認・修正する

Semantic Studio は、Workspaces で Semantic View を作成・編集する画面です。
Semantic View は YAML ファイル（`.sv.yaml`）として開き、CoCo との対話でもフォームでも編集できます。

1. 次のどちらかの方法で `MFG_SEMANTIC_VIEW` を開く
   - CoCo に「mfg_semantic_view を Semantic Studio で開いて」と依頼する
   - 左メニューの **AI & ML » Cortex Analyst** で一覧から選ぶ
2. 次の 3 点を確認する
   - **Relationships**: `production` と `lines` が `line_id` で結合されているか
   - **Metrics**: 不良率の式が `(生産数 - 良品数) / 生産数` になっているか
   - **Synonyms**: 「チョコ停」「不良率」などの現場用語が登録されているか
3. 足りない同義語を 1 つ手で追加する（例: `downtime` に「ライン停止」）
4. トップバーの **Deploy** を選び、差分を確認して Snowflake に反映する

> Snowflake のドキュメントは、同義語を AI に自動生成させず、現場の用語・略語・旧名称を人が登録することを勧めています。
> 自動生成した同義語は、回答の精度を下げることが多いためです。

> 新しい Semantic View は、Workspaces の **Add new » Semantic View** からも作れます。
> この操作で開くウィザード（Semantic View Autopilot）では、SQL クエリや Tableau・Power BI のファイルを元に定義を作れます。

---
## 4. 動作を確認する

```sql
-- L03（射出成形）の月次不良率。9 月以降に上がっていれば、定義は正しい
SELECT * FROM SEMANTIC_VIEW(
    mfg_semantic_view
    DIMENSIONS production.production_month, lines.line_id
    METRICS production.defect_rate
    WHERE lines.line_id = 'L03'
) ORDER BY production_month;
```

CoCo のパネルで、次の質問を日本語で試してください。CoCo は Semantic View を使って SQL を作ります。

- mfg_semantic_view を使って、9 月のライン別の不良率を教えて
- mfg_semantic_view を使って、チョコ停が多い設備のトップ 3 を教えて

> 不良率が 9 月に上がった **理由** は、構造化データだけでは分かりません。
> 理由は不具合報告書（PDF）に書かれています。Part 2 では、この PDF を検索できるようにします。
