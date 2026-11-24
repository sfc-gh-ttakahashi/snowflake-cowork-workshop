"""build_notebooks.py のテスト。"""
from __future__ import annotations

import json

import build_notebooks

SOURCE = """# Part 1

説明文

```sql
SELECT 1;
```

続きの説明

```sql
SELECT 2;
```
"""


def test_markdown_and_sql_become_separate_cells():
    nb = build_notebooks.to_notebook(SOURCE, prefix="p1")
    kinds = [c["cell_type"] for c in nb["cells"]]
    assert kinds == ["markdown", "code", "markdown", "code"]


def test_sql_cell_uses_snowsight_sql_magic_with_unique_result_names():
    nb = build_notebooks.to_notebook(SOURCE, prefix="p1")
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert "".join(code[0]["source"]).startswith("%%sql -r p1_1\nSELECT 1;")
    assert "".join(code[1]["source"]).startswith("%%sql -r p1_2\nSELECT 2;")
    assert code[0]["metadata"]["language"] == "sql"
    assert code[0]["metadata"]["resultVariableName"] == "p1_1"


def test_markdown_cell_keeps_text_without_fences():
    nb = build_notebooks.to_notebook(SOURCE, prefix="p1")
    assert "".join(nb["cells"][0]["source"]) == "# Part 1\n\n説明文"


def test_python_fence_becomes_python_cell():
    nb = build_notebooks.to_notebook("```python\nprint(1)\n```\n", prefix="p")
    cell = nb["cells"][0]
    assert cell["cell_type"] == "code"
    assert "".join(cell["source"]) == "print(1)"
    assert cell["metadata"]["language"] == "python"


def test_other_fences_stay_in_markdown():
    nb = build_notebooks.to_notebook("例\n\n```text\nCoCo への依頼文\n```\n", prefix="p")
    assert [c["cell_type"] for c in nb["cells"]] == ["markdown"]
    assert "```text" in "".join(nb["cells"][0]["source"])


def test_notebook_is_valid_nbformat4_json():
    nb = build_notebooks.to_notebook(SOURCE, prefix="p1")
    text = json.dumps(nb, ensure_ascii=False)
    assert json.loads(text)["nbformat"] == 4
    assert all("outputs" in c for c in nb["cells"] if c["cell_type"] == "code")


def test_sql_blocks_joins_only_sql_fences_in_order():
    source = SOURCE + "```python\nprint(1)\n```\n"
    assert build_notebooks.sql_blocks(source) == "SELECT 1;\n\nSELECT 2;\n"
