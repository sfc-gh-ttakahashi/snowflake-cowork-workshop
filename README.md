# Snowflake CoWork ハンズオン

製造業の架空データを使い、Semantic View と Cortex Search を作って Snowflake CoWork から使う半日（4時間）のハンズオンです。
最初の実施は SCSK 製造チーム向け（2026年12月、大阪）です。業種のデータを差し替えれば、他の業種向けにも使えます。

## 対象者と前提

- 対象者: SI パートナーのエンジニア（Snowflake の基本操作の経験があること）
- 環境: 受講者ごとの Snowflake トライアルアカウント（Enterprise / AWS / Asia Pacific (Tokyo)）
- **AI 機能の有効化**: セルフサービスのトライアルは、クレジットカードを登録するまで AI 機能が無効です
  （[Trial accounts](https://docs.snowflake.com/en/user-guide/admin-trial-account)）。
  このハンズオンでは、AI 機能が有効なトライアルを作る専用の登録リンクを講師が配布します。受講者は通常の登録ページから作らないでください。

## タイムテーブル（240分）

| 区分 | 内容 | 資材 | 時間 |
|---|---|---|---|
| 準備 | トライアル作成・Git 連携・セットアップ | `load.sql` / `setup.sql` | 20分 |
| 座学 | Snowflake の AI の全体像、コンテキストレイヤーの意義 | スライド | 15分 |
| Part 1 | Semantic View を CoCo で作り、Semantic Studio で確認する | `part1_semantic_view.ipynb` | 30分 |
| Part 2 | PDF を解析・チャンク化し、Cortex Search Service を作る | `part2_cortex_search.ipynb` | 40分 |
| 休憩 | | | 10分 |
| Part 3 | Cortex Agent を作り、CoWork から使う | `part3_agent_cowork.ipynb` | 25分 |
| Part 4 | 自由操作: CoWork で分析し、HTML レポートとダッシュボードを作る | `part4_free_exercise.md` | 55分 |
| デモ | Business Ontology・Cortex Sense・Cortex AI Gateway（講師） | `demo/README.md` | 25分 |
| まとめ | 成果物の共有、質疑、アンケート | | 20分 |

## 受講者の手順

1. トライアルアカウントを作り、ACCOUNTADMIN ロールでログインする
2. Workspaces で新しい SQL ファイルを作り、[`load.sql`](load.sql) の内容を貼り付けて「すべて実行」する
3. Workspaces の **From Git repository** で、このリポジトリを開く（API Integration は `COWORK_HANDSON_GIT_INTEGRATION`）
4. `setup.sql` を開いて「すべて実行」する。最後の結果で、すべてのテーブルの件数が 0 でなければ成功
5. `part1_semantic_view.ipynb` から順に進める
6. 終わったら `cleanup.sql` を実行する（任意）

遅れた場合は、次の SQL を実行すると次の Part に追いつけます。

| 追いつく Part | 実行する SQL |
|---|---|
| Part 2 の前 | `industries/manufacturing/semantic_view_answer.sql` |
| Part 3 の前 | `industries/manufacturing/search_answer.sql` |

## 作成されるオブジェクト

| オブジェクト | 名前 |
|---|---|
| ウェアハウス | `COWORK_HANDSON_WH`（XSMALL） |
| データベース | `COWORK_HANDSON_DB`（演習データ）、`COWORK_HANDSON_GIT_DB`（Git 連携） |
| Semantic View | `COWORK_HANDSON_DB.ANALYTICS.MFG_SEMANTIC_VIEW` |
| Cortex Search Service | `COWORK_HANDSON_DB.ANALYTICS.MFG_DOC_SEARCH` |
| Cortex Agent | `COWORK_HANDSON_DB.ANALYTICS.MFG_AGENT`（CoWork 上の表示名は「製造現場アシスタント」） |

## リポジトリの構成

```text
load.sql / setup.sql / cleanup.sql
part1_semantic_view.ipynb        # labs/part1_semantic_view.md から生成
part2_cortex_search.ipynb        # labs/part2_cortex_search.md から生成
part3_agent_cowork.ipynb         # labs/part3_agent_cowork.md から生成
part4_free_exercise.md
labs/                            # Notebook の原稿（編集はこちらで行う）
industries/manufacturing/
  data/*.csv, docs/*.pdf         # scripts/generate_data.py で生成
  questions.md                   # CoWork で試す質問と答えの目安
  semantic_view_answer.sql       # Part 1 の正解例
  search_answer.sql              # Part 2 の一括実行（labs から生成）
demo/README.md                   # 講師デモの手順
scripts/                         # データと Notebook の生成スクリプト
tests/                           # 生成スクリプトのテストと、アカウントでの通し実行
```

## 講師・保守担当者向け

```bash
uv run pytest                                    # 生成スクリプトのテスト
uv run python scripts/generate_data.py           # CSV と PDF を再生成
uv run python scripts/build_notebooks.py         # labs/*.md から Notebook と search_answer.sql を再生成
bash tests/verify_on_account.sh <snow の接続名> \
  industries/manufacturing/semantic_view_answer.sql \
  labs/part2_cortex_search.md labs/part3_agent_cowork.md   # アカウントで通し実行（Git の代わりに PUT を使う）
```

### 他の業種に差し替える

1. `scripts/generate_data.py` を複製し、マスタ・傾向・文書の定義を書き換えて `industries/<業種>/` に出力する
2. `setup.sql` の Step 3（コピー元のパス）と Step 4（テーブル定義）を変更する
3. `industries/<業種>/semantic_view_answer.sql` と `questions.md` を作る
4. `labs/*.md` の業種固有の説明と依頼文を変更し、`build_notebooks.py` を実行する
5. `tests/verify_on_account.sh` で通し実行する
