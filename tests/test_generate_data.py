"""generate_data.py のテスト。

演習の質問（不良率の上昇、特定設備の停止の偏り）に答えられるデータになっているかを確認する。
"""
from __future__ import annotations

import csv
import datetime as dt
from collections import Counter
from pathlib import Path

import pytest

import generate_data

CSV_FILES = {
    "plants.csv": ["plant_id", "plant_name", "location"],
    "lines.csv": ["line_id", "plant_id", "line_name", "process"],
    "products.csv": ["product_id", "product_name", "category", "line_id", "unit_cost_jpy"],
    "equipment.csv": ["equipment_id", "line_id", "equipment_name", "model", "installed_date"],
    "production.csv": [
        "production_date", "shift", "line_id", "product_id",
        "planned_qty", "produced_qty", "good_qty",
    ],
    "defects.csv": ["production_date", "shift", "line_id", "product_id", "defect_type", "defect_qty"],
    "downtime.csv": [
        "downtime_id", "equipment_id", "start_at", "duration_min", "reason_category", "description",
    ],
    "documents.csv": ["file_name", "doc_type", "title", "line_id", "equipment_id", "issued_date"],
}


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("manufacturing")
    generate_data.generate(path)
    return path


def read_rows(out_dir: Path, name: str) -> list[dict[str, str]]:
    with (out_dir / "data" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("name,header", CSV_FILES.items())
def test_csv_has_expected_header(out_dir, name, header):
    with (out_dir / "data" / name).open(encoding="utf-8") as f:
        assert next(csv.reader(f)) == header


def test_good_qty_never_exceeds_produced_qty(out_dir):
    rows = read_rows(out_dir, "production.csv")
    assert rows
    assert all(int(r["good_qty"]) <= int(r["produced_qty"]) for r in rows)


def test_defect_qty_matches_production_loss(out_dir):
    loss = Counter()
    for r in read_rows(out_dir, "production.csv"):
        key = (r["production_date"], r["shift"], r["line_id"], r["product_id"])
        loss[key] = int(r["produced_qty"]) - int(r["good_qty"])
    defects = Counter()
    for r in read_rows(out_dir, "defects.csv"):
        key = (r["production_date"], r["shift"], r["line_id"], r["product_id"])
        defects[key] += int(r["defect_qty"])
    assert +loss == +defects


def _defect_rate(out_dir: Path, line_id: str, start: dt.date, end: dt.date) -> float:
    produced = defect = 0
    for r in read_rows(out_dir, "production.csv"):
        d = dt.date.fromisoformat(r["production_date"])
        if r["line_id"] == line_id and start <= d <= end:
            produced += int(r["produced_qty"])
            defect += int(r["produced_qty"]) - int(r["good_qty"])
    return defect / produced


def test_l03_defect_rate_rises_after_september(out_dir):
    before = _defect_rate(out_dir, "L03", dt.date(2026, 4, 1), dt.date(2026, 8, 31))
    after = _defect_rate(out_dir, "L03", dt.date(2026, 9, 1), dt.date(2026, 10, 31))
    assert after > before * 2


def test_l03_short_shot_dominates_after_september(out_dir):
    counter = Counter()
    for r in read_rows(out_dir, "defects.csv"):
        if r["line_id"] == "L03" and r["production_date"] >= "2026-09-01":
            counter[r["defect_type"]] += int(r["defect_qty"])
    assert counter.most_common(1)[0][0] == "ショートショット"


def test_servo_alarm_concentrates_on_l04_robot(out_dir):
    counter = Counter(
        r["equipment_id"]
        for r in read_rows(out_dir, "downtime.csv")
        if r["reason_category"] == "故障" and r["start_at"] >= "2026-08-01"
    )
    top, second = counter.most_common(2)
    assert top[0] == "EQ-L04-02"
    assert top[1] >= second[1] * 2


def test_every_document_is_a_pdf(out_dir):
    docs = read_rows(out_dir, "documents.csv")
    assert {d["doc_type"] for d in docs} == {"作業手順書", "不具合報告書", "設備マニュアル"}
    for d in docs:
        assert (out_dir / "docs" / d["file_name"]).read_bytes()[:5] == b"%PDF-"


def test_generation_is_deterministic(out_dir, tmp_path):
    generate_data.generate(tmp_path)
    for name in CSV_FILES:
        assert (tmp_path / "data" / name).read_bytes() == (out_dir / "data" / name).read_bytes()
