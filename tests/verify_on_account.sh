#!/usr/bin/env bash
# setup.sql と各 Part の SQL を、指定した接続のアカウントで通しで実行する。
# GitHub に push する前でも確認できるよう、Git からのコピーはローカルファイルの PUT に置き換える。
#
#   bash tests/verify_on_account.sh <snow の接続名> [SQL ファイル ...]
#
# SQL ファイルを省略すると setup.sql だけを実行する。
set -euo pipefail

conn="${1:?接続名を指定してください}"
shift
root="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

run_sql() {
  env -u SNOWFLAKE_HOST -u SNOWFLAKE_ACCOUNT \
      -u SNOWFLAKE_CONNECTIONS_SNOWHOUSE_OAUTH_TOKEN -u SNOWFLAKE_CONNECTIONS_SNOWHOUSE_OAUTH_AUTHENTICATOR \
      snow sql -c "$conn" -f "$1"
}

data="$root/industries/manufacturing/data"
docs="$root/industries/manufacturing/docs"
{
  echo "-- PUT で置き換えたファイル"
  for f in "$data"/*.csv; do
    echo "PUT 'file://$f' @data_stage/industries/manufacturing/data/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE;"
  done
  for f in "$docs"/*.pdf; do
    echo "PUT 'file://$f' @doc_stage/ AUTO_COMPRESS = FALSE OVERWRITE = TRUE;"
  done
} > "$work/put.sql"

awk -v put="$work/put.sql" '
  /^-- BEGIN GIT COPY/ { while ((getline line < put) > 0) print line; skip = 1; next }
  /^-- END GIT COPY/   { skip = 0; next }
  !skip
' "$root/setup.sql" > "$work/setup.sql"

echo "== setup.sql"
run_sql "$work/setup.sql"

for f in "$@"; do
  echo "== $f"
  case "$f" in
    *.md)
      # labs/*.md は ```sql ブロックだけを取り出して実行する
      awk '/^```sql$/ { on = 1; next } /^```$/ { on = 0; next } on' "$root/$f" > "$work/lab.sql"
      run_sql "$work/lab.sql"
      ;;
    *) run_sql "$root/$f" ;;
  esac
done
