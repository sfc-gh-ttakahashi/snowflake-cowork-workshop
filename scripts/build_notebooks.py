"""labs/*.md から Snowsight Workspaces 用の Notebook（.ipynb）を生成する。

    uv run python scripts/build_notebooks.py

```sql と ```python のコードブロックはコードセル、それ以外は Markdown セルになる。
SQL セルは参考ハンズオンと同じ `%%sql -r <変数名>` 形式にする。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FENCE = re.compile(r"^```(sql|python)\n(.*?)^```\n?", re.MULTILINE | re.DOTALL)


def _lines(text: str) -> list[str]:
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def _markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {"codeCollapsed": True, "collapsed": False}, "source": _lines(text)}


def _code(language: str, body: str, name: str) -> dict:
    metadata: dict = {"language": language, "name": name, "title": name}
    if language == "sql":
        metadata["resultVariableName"] = name
        body = f"%%sql -r {name}\n{body}"
    return {"cell_type": "code", "execution_count": None, "metadata": metadata, "outputs": [], "source": _lines(body)}


def to_notebook(source: str, prefix: str) -> dict:
    """Markdown 原稿を nbformat 4 の dict に変換する。prefix は SQL 結果変数名の接頭辞。"""
    cells: list[dict] = []
    pos = 0
    n = 0
    for m in FENCE.finditer(source):
        text = source[pos:m.start()].strip()
        if text:
            cells.append(_markdown(text))
        n += 1
        cells.append(_code(m.group(1), m.group(2).rstrip("\n"), f"{prefix}_{n}"))
        pos = m.end()
    tail = source[pos:].strip()
    if tail:
        cells.append(_markdown(tail))
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Jupyter Notebook", "name": "jupyter"},
                     "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def sql_blocks(source: str) -> str:
    """Markdown 原稿から ```sql ブロックだけを順につなげて返す。"""
    return "\n\n".join(m.group(2).rstrip("\n") for m in FENCE.finditer(source) if m.group(1) == "sql") + "\n"


# 遅れた受講者が一括実行する SQL。原稿から生成し、手で複製しない
CATCH_UP = {
    "part2_cortex_search.md": (
        "industries/manufacturing/search_answer.sql",
        "-- search_answer.sql - Part 2 を一括で実行する（labs/part2_cortex_search.md から自動生成。直接編集しない）\n\n",
    ),
}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    for src in sorted((root / "labs").glob("part*.md")):
        prefix = src.stem.split("_")[0]
        text = src.read_text(encoding="utf-8")
        nb = to_notebook(text, prefix=prefix)
        dest = root / f"{src.stem}.ipynb"
        dest.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{src.relative_to(root)} -> {dest.relative_to(root)}")
        if src.name in CATCH_UP:
            path, header = CATCH_UP[src.name]
            (root / path).write_text(header + sql_blocks(text), encoding="utf-8")
            print(f"{src.relative_to(root)} -> {path}")


if __name__ == "__main__":
    main()
