"""製造業の架空データ（CSV）と文書（PDF）を生成する。

業種を差し替えるときは、このスクリプトを複製して industries/<業種>/ に出力する。

    uv run python scripts/generate_data.py            # industries/manufacturing に出力
    uv run python scripts/generate_data.py <出力先>

演習の質問に答えが出るよう、次の傾向を意図的に入れている。
- L03（射出成形）は 2026-09 以降に不良率が上がり、ショートショットが最多になる
- EQ-L04-02（組立ロボット）は 2026-08 以降にサーボアラームによる停止が集中する
"""
from __future__ import annotations

import csv
import datetime as dt
import random
import sys
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SEED = 20261201
START = dt.date(2026, 4, 1)
END = dt.date(2026, 10, 31)
SHIFTS = ["日勤", "夜勤"]
FONT = "HeiseiKakuGo-W5"

PLANTS = [
    ("P01", "大阪第一工場", "大阪府堺市"),
    ("P02", "滋賀工場", "滋賀県栗東市"),
]
LINES = [
    ("L01", "P01", "プレス1号ライン", "プレス"),
    ("L02", "P01", "溶接1号ライン", "溶接"),
    ("L03", "P01", "射出成形1号ライン", "射出成形"),
    ("L04", "P01", "組立1号ライン", "組立"),
    ("L05", "P02", "塗装1号ライン", "塗装"),
    ("L06", "P02", "最終検査ライン", "検査"),
]
PRODUCTS = [
    ("PR001", "ブラケットA", "金属部品", "L01", 320),
    ("PR002", "ブラケットB", "金属部品", "L01", 410),
    ("PR003", "フレーム溶接体", "金属部品", "L02", 1850),
    ("PR004", "樹脂カバーS", "樹脂部品", "L03", 140),
    ("PR005", "樹脂カバーL", "樹脂部品", "L03", 220),
    ("PR006", "制御ユニット", "組立品", "L04", 5200),
    ("PR007", "塗装パネル", "外装部品", "L05", 980),
    ("PR008", "完成品ユニット", "完成品", "L06", 12800),
]
EQUIPMENT = [
    ("EQ-L01-01", "L01", "300tプレス機", "AP-300", "2018-05-10"),
    ("EQ-L01-02", "L01", "材料送り装置", "FD-20", "2018-05-10"),
    ("EQ-L02-01", "L02", "溶接ロボット1", "WR-1200", "2020-03-02"),
    ("EQ-L02-02", "L02", "溶接ロボット2", "WR-1200", "2020-03-02"),
    ("EQ-L03-01", "L03", "射出成形機", "IM-450", "2019-09-20"),
    ("EQ-L03-02", "L03", "金型温度調節機", "TC-80", "2019-09-20"),
    ("EQ-L04-01", "L04", "部品供給フィーダー", "PF-10", "2021-07-15"),
    ("EQ-L04-02", "L04", "組立ロボット", "AR-700", "2021-07-15"),
    ("EQ-L05-01", "L05", "塗装ブース", "PB-3", "2017-11-01"),
    ("EQ-L05-02", "L05", "乾燥炉", "DO-5", "2017-11-01"),
    ("EQ-L06-01", "L06", "画像検査装置", "VI-2000", "2022-04-01"),
]
DEFECT_TYPES = {
    "プレス": ["バリ", "割れ", "寸法不良"],
    "溶接": ["溶接不良", "スパッタ付着", "寸法不良"],
    "射出成形": ["ショートショット", "ヒケ", "バリ", "ウェルドライン"],
    "組立": ["部品欠品", "締付不良", "配線不良"],
    "塗装": ["塗装ムラ", "異物混入", "タレ"],
    "検査": ["外観不良", "機能不良"],
}
BASE_DEFECT_RATE = {"L01": 0.012, "L02": 0.018, "L03": 0.015, "L04": 0.010, "L05": 0.022, "L06": 0.006}
PLANNED_QTY = {"L01": 1800, "L02": 400, "L03": 2400, "L04": 300, "L05": 500, "L06": 260}
DOWNTIME_REASONS = {
    "段取替え": ["品種切替のため段取替え", "金型交換"],
    "故障": ["モーター過負荷で停止", "センサー異常で停止", "エア圧低下で停止"],
    "材料待ち": ["前工程からの部品待ち", "材料の入荷遅れ"],
    "定期保全": ["月次点検", "消耗品交換"],
}


def _dates() -> list[dt.date]:
    days = (END - START).days + 1
    return [START + dt.timedelta(days=i) for i in range(days) if (START + dt.timedelta(days=i)).weekday() < 5]


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _defect_rate(line_id: str, day: dt.date, rng: random.Random) -> float:
    rate = BASE_DEFECT_RATE[line_id] * rng.uniform(0.6, 1.4)
    if line_id == "L03" and day >= dt.date(2026, 9, 1):
        rate *= 3.5
    return rate


def _pick_defect_type(process: str, line_id: str, day: dt.date, rng: random.Random) -> str:
    if line_id == "L03" and day >= dt.date(2026, 9, 1) and rng.random() < 0.7:
        return "ショートショット"
    return rng.choice(DEFECT_TYPES[process])


def build_production(rng: random.Random) -> tuple[list[list], list[list]]:
    """生産実績と不良実績の行を返す。不良数の合計は produced_qty - good_qty と一致する。"""
    process_of = {line[0]: line[3] for line in LINES}
    production: list[list] = []
    defects: list[list] = []
    for day in _dates():
        for shift in SHIFTS:
            for product_id, _, _, line_id, _ in PRODUCTS:
                n_products = sum(1 for p in PRODUCTS if p[3] == line_id)
                planned = PLANNED_QTY[line_id] // n_products
                produced = int(planned * rng.uniform(0.88, 1.02))
                defect_total = round(produced * _defect_rate(line_id, day, rng))
                production.append([day.isoformat(), shift, line_id, product_id, planned, produced, produced - defect_total])
                counts: dict[str, int] = {}
                for _ in range(defect_total):
                    t = _pick_defect_type(process_of[line_id], line_id, day, rng)
                    counts[t] = counts.get(t, 0) + 1
                for t in sorted(counts):
                    defects.append([day.isoformat(), shift, line_id, product_id, t, counts[t]])
    return production, defects


def build_downtime(rng: random.Random) -> list[list]:
    rows: list[list] = []
    seq = 1
    for day in _dates():
        for eq_id, *_ in EQUIPMENT:
            events: list[str] = []
            if rng.random() < 0.06:
                events.append(rng.choice(list(DOWNTIME_REASONS)))
            if eq_id == "EQ-L04-02" and day >= dt.date(2026, 8, 1) and rng.random() < 0.35:
                events.append("サーボ")
            for kind in events:
                start = dt.datetime.combine(day, dt.time(8)) + dt.timedelta(minutes=rng.randrange(0, 960))
                if kind == "サーボ":
                    category, desc, minutes = "故障", "サーボアラーム（AL.25）で停止。リセット後に再開", rng.randint(15, 70)
                else:
                    category, desc = kind, rng.choice(DOWNTIME_REASONS[kind])
                    minutes = rng.randint(10, 120)
                rows.append([f"DT{seq:05d}", eq_id, start.isoformat(sep=" "), minutes, category, desc])
                seq += 1
    return rows


# ---------------------------------------------------------------- PDF

def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName=FONT, fontSize=10.5, leading=16)
    return {
        "title": ParagraphStyle("title", parent=base, fontSize=18, leading=26, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base, fontSize=13, leading=20, spaceBefore=10, spaceAfter=4),
        "body": base,
        "meta": ParagraphStyle("meta", parent=base, fontSize=9, textColor=colors.grey),
    }


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    t = Table(rows, colWidths=[w * mm for w in widths])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT, 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEBF7")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _render(path: Path, title: str, meta: str, sections: list) -> None:
    s = _styles()
    story = [Paragraph(title, s["title"]), Paragraph(meta, s["meta"]), Spacer(1, 6 * mm)]
    for item in sections:
        if item == "PAGE":
            story.append(PageBreak())
        elif isinstance(item, tuple) and item[0] == "h2":
            story.append(Paragraph(item[1], s["h2"]))
        elif isinstance(item, tuple) and item[0] == "table":
            story.append(_table(item[1], item[2]))
            story.append(Spacer(1, 3 * mm))
        else:
            story.append(Paragraph(item, s["body"]))
    SimpleDocTemplate(str(path), pagesize=A4, title=title, author="架空株式会社 製造本部").build(story)


def _documents() -> list[dict]:
    """文書の定義。sections の要素は段落の文字列、("h2", 見出し)、("table", 行, 列幅mm)、"PAGE"。"""
    return [
        {
            "file_name": "SOP-L03-001.pdf", "doc_type": "作業手順書",
            "title": "射出成形1号ライン 作業手順書", "line_id": "L03", "equipment_id": "EQ-L03-01",
            "issued_date": "2025-04-01",
            "sections": [
                ("h2", "1. 目的と適用範囲"),
                "本書は射出成形1号ライン（L03）で樹脂カバーS・Lを成形する作業の手順を定める。",
                ("h2", "2. 始業前点検"),
                ("table", [["No", "点検項目", "基準", "異常時の対応"],
                           ["1", "金型温度", "設定値 ±3℃（樹脂カバーS: 60℃、L: 65℃）", "金型温度調節機の表示と熱電対を確認し、班長に報告"],
                           ["2", "樹脂乾燥", "80℃で4時間以上", "乾燥時間が不足する場合は成形を開始しない"],
                           ["3", "作動油温度", "40〜50℃", "保全課に連絡"]], [10, 35, 60, 65]),
                ("h2", "3. 成形条件"),
                ("table", [["項目", "樹脂カバーS", "樹脂カバーL"],
                           ["射出圧力", "85 MPa", "92 MPa"],
                           ["保圧時間", "6.0 秒", "7.5 秒"],
                           ["冷却時間", "18 秒", "22 秒"]], [50, 50, 50]),
                "PAGE",
                ("h2", "4. 不良発生時の一次対応"),
                "ショートショット（充填不足）が連続して3個以上発生した場合は、成形を止めて次の順に確認する。"
                "(1) 金型温度が設定値より低くないか。(2) 樹脂の乾燥が十分か。(3) 射出圧力が設定値どおりか。",
                "ヒケが発生した場合は保圧時間を0.5秒単位で延長し、改善しなければ班長に報告する。",
                ("h2", "5. 記録"),
                "不良の種類と個数は、シフトごとに生産管理システムへ入力する。",
            ],
        },
        {
            "file_name": "SOP-L04-001.pdf", "doc_type": "作業手順書",
            "title": "組立1号ライン 作業手順書", "line_id": "L04", "equipment_id": "EQ-L04-02",
            "issued_date": "2025-06-15",
            "sections": [
                ("h2", "1. 目的と適用範囲"),
                "本書は組立1号ライン（L04）で制御ユニットを組み立てる作業の手順を定める。",
                ("h2", "2. 組立ロボットの起動"),
                "安全柵の扉が閉じていることを確認し、操作盤の原点復帰ボタンを押す。原点復帰が完了するまでロボットの可動範囲に入らない。",
                ("h2", "3. アラーム発生時の対応"),
                ("table", [["アラーム", "内容", "作業者の対応"],
                           ["AL.12", "部品把持ミス", "フィーダーの部品姿勢を確認し、リセット"],
                           ["AL.25", "サーボ過負荷", "リセットは1回まで。再発したら保全課に連絡し、設備マニュアル 5章を参照"],
                           ["AL.31", "安全柵開放", "扉を閉じてリセット"]], [25, 45, 100]),
                ("h2", "4. 締付トルク"),
                "M4ねじは1.2N・m、M5ねじは2.0N・mで締め付ける。トルクドライバーは毎日始業前に校正記録を確認する。",
            ],
        },
        {
            "file_name": "SOP-L05-001.pdf", "doc_type": "作業手順書",
            "title": "塗装1号ライン 作業手順書", "line_id": "L05", "equipment_id": "EQ-L05-01",
            "issued_date": "2024-11-01",
            "sections": [
                ("h2", "1. 塗装前の確認"),
                "ブース内の温度は20〜28℃、湿度は75%以下であることを確認する。湿度が75%を超える場合は塗装を開始しない。",
                ("h2", "2. 塗装ムラの防止"),
                "スプレーガンとワークの距離は200mm、移動速度は毎秒300mmを目安とする。",
                ("h2", "3. 乾燥"),
                "乾燥炉は80℃で20分。乾燥炉から出したパネルは30分以上冷却してから検査工程に送る。",
            ],
        },
        {
            "file_name": "NCR-2026-0912.pdf", "doc_type": "不具合報告書",
            "title": "不具合報告書 NCR-2026-0912 樹脂カバーのショートショット多発", "line_id": "L03",
            "equipment_id": "EQ-L03-02", "issued_date": "2026-09-12",
            "sections": [
                ("h2", "1. 事象"),
                "2026年9月に入り、射出成形1号ライン（L03）の樹脂カバーS・Lでショートショットが多発している。"
                "不良率は8月までの約1.5%から、9月第2週に約5%まで上昇した。",
                ("h2", "2. 調査結果"),
                ("table", [["調査項目", "結果"],
                           ["射出圧力", "設定値どおり（異常なし）"],
                           ["樹脂乾燥", "乾燥時間4.5時間（異常なし）"],
                           ["金型温度", "設定60℃に対し実測52〜55℃。金型温度調節機 EQ-L03-02 のヒーター出力が低下"]], [45, 125]),
                ("h2", "3. 原因"),
                "金型温度調節機（EQ-L03-02、2019年導入）のヒーターが劣化し、金型温度が設定値まで上がらないことが原因と推定する。",
                ("h2", "4. 暫定対策と恒久対策"),
                "暫定対策: 始業前の金型温度確認を1日2回に増やし、55℃未満の場合は成形を開始しない。"
                "恒久対策: ヒーターユニットを交換する（部品手配中、納期は2026年11月中旬の予定）。",
            ],
        },
        {
            "file_name": "NCR-2026-0820.pdf", "doc_type": "不具合報告書",
            "title": "不具合報告書 NCR-2026-0820 組立ロボットのサーボアラーム頻発", "line_id": "L04",
            "equipment_id": "EQ-L04-02", "issued_date": "2026-08-20",
            "sections": [
                ("h2", "1. 事象"),
                "2026年8月以降、組立1号ライン（L04）の組立ロボット（EQ-L04-02）でサーボアラーム AL.25 が頻発し、ラインが停止している。",
                ("h2", "2. 調査結果"),
                "第3軸の減速機からの異音を確認した。グリス交換は前回から18か月実施されていない（推奨は12か月ごと）。",
                ("h2", "3. 対策"),
                "暫定対策: 第3軸の速度を80%に制限する。恒久対策: 減速機のオーバーホールを次回の長期休暇に実施する。",
                ("h2", "4. 影響"),
                "停止1回あたり15〜70分。制御ユニットの生産計画に対し、8月の達成率が約3ポイント低下した。",
            ],
        },
        {
            "file_name": "NCR-2026-0605.pdf", "doc_type": "不具合報告書",
            "title": "不具合報告書 NCR-2026-0605 梅雨時期の塗装ムラ", "line_id": "L05",
            "equipment_id": "EQ-L05-01", "issued_date": "2026-06-05",
            "sections": [
                ("h2", "1. 事象"),
                "6月上旬、塗装1号ライン（L05）で塗装パネルの塗装ムラが増加した。",
                ("h2", "2. 原因と対策"),
                "ブース内の湿度が80%を超えていたことが原因。除湿機を追加し、作業手順書に湿度75%以下の基準を明記した。",
            ],
        },
        {
            "file_name": "MAN-IM450.pdf", "doc_type": "設備マニュアル",
            "title": "射出成形機 IM-450 取扱説明書（抜粋）", "line_id": "L03", "equipment_id": "EQ-L03-01",
            "issued_date": "2019-09-01",
            "sections": [
                ("h2", "1. 仕様"),
                ("table", [["項目", "値"], ["型締力", "450 kN"], ["最大射出圧力", "180 MPa"], ["シリンダー温度範囲", "150〜350℃"]], [60, 80]),
                ("h2", "2. 定期点検"),
                ("table", [["周期", "点検内容"], ["毎日", "作動油温度、異音の有無"], ["月次", "ノズルの摩耗、ヒーターバンドの断線"],
                           ["年次", "作動油交換、スクリューの摩耗測定"]], [30, 110]),
                "PAGE",
                ("h2", "3. 成形不良と対策"),
                ("table", [["不良", "主な原因", "対策"],
                           ["ショートショット", "金型温度不足、射出圧力不足、樹脂の流動性低下", "金型温度と射出圧力を上げる。温調機の出力を点検する"],
                           ["ヒケ", "保圧不足、冷却不足", "保圧時間と冷却時間を延長する"],
                           ["バリ", "型締力不足、金型の摩耗", "型締力を確認し、金型を補修する"]], [30, 65, 75]),
            ],
        },
        {
            "file_name": "MAN-AR700.pdf", "doc_type": "設備マニュアル",
            "title": "組立ロボット AR-700 保守マニュアル（抜粋）", "line_id": "L04", "equipment_id": "EQ-L04-02",
            "issued_date": "2021-07-01",
            "sections": [
                ("h2", "1. 保守周期"),
                ("table", [["部位", "作業", "周期"], ["各軸減速機", "グリス交換", "12か月または運転4,000時間"],
                           ["ケーブル", "被覆の損傷確認", "6か月"], ["バッテリー", "交換", "24か月"]], [40, 50, 60]),
                "PAGE",
                ("h2", "5. アラーム一覧と処置"),
                ("table", [["コード", "名称", "主な原因", "処置"],
                           ["AL.12", "把持エラー", "部品姿勢の乱れ", "供給装置を調整"],
                           ["AL.25", "サーボ過負荷", "減速機の劣化、グリス切れ、負荷過大", "グリス交換履歴を確認。異音があれば減速機を点検"],
                           ["AL.40", "エンコーダ異常", "ケーブル断線", "ケーブルを交換"]], [20, 30, 55, 65]),
            ],
        },
    ]


def build_pdfs(docs_dir: Path) -> list[list]:
    rl_config.invariant = 1  # PDF に作成日時や乱数 ID を埋め込まない
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    docs_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in _documents():
        meta = f"文書種別: {d['doc_type']}　対象ライン: {d['line_id']}　対象設備: {d['equipment_id']}　発行日: {d['issued_date']}"
        _render(docs_dir / d["file_name"], d["title"], meta, d["sections"])
        rows.append([d["file_name"], d["doc_type"], d["title"], d["line_id"], d["equipment_id"], d["issued_date"]])
    return rows


def generate(out_dir: Path) -> None:
    """out_dir/data に CSV、out_dir/docs に PDF を出力する。同じ入力なら同じ CSV を出力する。"""
    rng = random.Random(SEED)
    data = out_dir / "data"
    _write_csv(data / "plants.csv", ["plant_id", "plant_name", "location"], [list(p) for p in PLANTS])
    _write_csv(data / "lines.csv", ["line_id", "plant_id", "line_name", "process"], [list(x) for x in LINES])
    _write_csv(data / "products.csv", ["product_id", "product_name", "category", "line_id", "unit_cost_jpy"],
               [list(p) for p in PRODUCTS])
    _write_csv(data / "equipment.csv", ["equipment_id", "line_id", "equipment_name", "model", "installed_date"],
               [list(e) for e in EQUIPMENT])
    production, defects = build_production(rng)
    _write_csv(data / "production.csv",
               ["production_date", "shift", "line_id", "product_id", "planned_qty", "produced_qty", "good_qty"], production)
    _write_csv(data / "defects.csv",
               ["production_date", "shift", "line_id", "product_id", "defect_type", "defect_qty"], defects)
    _write_csv(data / "downtime.csv",
               ["downtime_id", "equipment_id", "start_at", "duration_min", "reason_category", "description"],
               build_downtime(rng))
    _write_csv(data / "documents.csv",
               ["file_name", "doc_type", "title", "line_id", "equipment_id", "issued_date"], build_pdfs(out_dir / "docs"))


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else root / "industries" / "manufacturing")
