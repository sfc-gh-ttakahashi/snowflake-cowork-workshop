# AGENTS.md

Snowflake CoWork ハンズオンの資材。受講者は Snowsight の Git ワークスペースでこのリポジトリを開く。

## 編集の規則

- Notebook（`part*.ipynb`）は直接編集しない。`labs/part*.md` を編集し、`uv run python scripts/build_notebooks.py` で生成する
- `industries/manufacturing/search_answer.sql` も生成物。`labs/part2_cortex_search.md` を編集する
- `industries/manufacturing/data/` と `docs/` は `scripts/generate_data.py` の出力。手で編集しない
- 演習の質問の答え（L03 の不良率上昇、EQ-L04-02 の停止集中）はデータ生成に組み込んである。傾向を変えたら `questions.md` の「答えの目安」も直す
- PDF のファイル名は ASCII にする（日本語名は `documents.csv` の `title` に入れる）

## 確認

- `uv run pytest` を通す
- SQL を変更したら `bash tests/verify_on_account.sh <接続名> ...` でアカウント上で通し実行する
- Semantic View のディメンション名は、元の列名と揃える（別名にすると Cortex Analyst が元の列名で SQL を作り、エラーになった）
- `production` から `lines` への結合経路は 1 本にする（`products` 経由の関係を足すと、ライン別の集計がエラーになる）
- 埋め込みモデルを変えたら、setup.sql の `CORTEX-MODEL-ROLE-*` の付与も変える（Model RBAC が有効なトライアルでは、付与がないと Cortex Search の作成が失敗する）
