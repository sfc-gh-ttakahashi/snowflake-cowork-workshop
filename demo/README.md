# 講師デモ: コンテキストレイヤーと AI ガバナンス（25分）

受講者のトライアルでは実行しません。講師のデモアカウントで画面を見せます。
ハンズオンで作った Semantic View と Cortex Search が「コンテキストレイヤー」の部品であること、
それを組織全体で管理・統制する機能があることを示すのが目的です。

| 時間 | デモ | 受講者に伝えること |
|---|---|---|
| 10分 | Business Ontology | 業務用語・指標・エンティティの関係を、テーブルより上の層で定義できる |
| 7分 | Cortex Sense | テーブル・用語・過去のクエリをまとめて検索でき、Agent が根拠として使える。誤りは利用者がフィードバックできる |
| 8分 | Cortex AI Gateway | どのモデルを誰が使えるか、利用状況とコストを 1 か所で統制できる |

---

## 1. Business Ontology（10分）

講師が別途用意します。

## 2. Cortex Sense（7分）

講師が別途用意します。

## 3. Cortex AI Gateway（8分）

参照: [Cortex AI Gateway](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-ai-gateway)

1. Snowsight の左メニューで **AI Gateway** を開き、画面の構成を見せる
2. 現在の設定を SQL で表示する

   ```sql
   SHOW AI GATEWAYS;
   DESCRIBE AI GATEWAY SNOWFLAKE;
   ```

3. 仕様（specification）の主な項目を説明する
   - `models`: 公開するモデルの一覧。`'*'` はアカウントで使える全モデル
   - `logging.enabled`: リクエストのトレースを記録するか
   - `logging.capture_payload.request_response`: プロンプトと応答の本文を記録するか（有効にすると記録が機密情報になる）
4. 権限で利用者を絞れることを示す

   ```sql
   GRANT USAGE ON AI GATEWAY SNOWFLAKE TO ROLE <利用させるロール>;
   GRANT MONITOR ON AI GATEWAY SNOWFLAKE TO ROLE <コスト管理者のロール>;
   ```

5. **AI & ML » AI Gateway » MCP & Tools** を開き、CoCo や外部の AI クライアントから使える MCP サーバー（GitHub、Slack など）を
   管理者が許可制で配布できることを見せる（Preview。管理できるのは ACCOUNTADMIN のみ）

> `ALTER AI GATEWAY ... FROM SPECIFICATION` は仕様の全体を置き換えます。デモで変更する場合は、
> 先に `DESCRIBE AI GATEWAY` の結果を控え、終わったら元に戻してください。

話の流れ:

- 製造業の顧客は「どの AI に何のデータを渡してよいか」を気にする。AI Gateway はその統制点になる
- SCSK が提供できる価値: AI 利用ポリシーの設計、モデルの許可リストとログ設定、コスト配賦の設計
