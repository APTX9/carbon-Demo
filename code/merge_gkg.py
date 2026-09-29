# -*- coding: utf-8 -*-
"""
合并 GKG 按天筛选结果为单一数据集。

把 data/gkg/YYYYMMDD.csv（含全部字段）合并并提取关键信息，
导出为 Excel 友好的 CSV。
"""
import csv
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
GKG_DIR = PROJECT_ROOT / "data" / "gkg"
OUT_DIR = PROJECT_ROOT / "data" / "processed"

FIELDS = ["DATE", "NUMARTS", "THEMES", "LOCATIONS", "ORGANIZATIONS",
          "TONE", "SOURCES", "SOURCEURLS"]


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    files = sorted(GKG_DIR.glob("*.csv"))
    if not files:
        print("没有找到 data/gkg/*.csv，请先运行 gkg_scraper.py")
        return

    print(f"合并 {len(files)} 个文件...", flush=True)
    rows = []
    for i, f in enumerate(files):
        with open(f, encoding="utf-8") as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = next(reader, None)
            if not header:
                continue
            idx = {name: i for i, name in enumerate(header) if name in FIELDS}
            for row in reader:
                rows.append({name: row[pos] if pos < len(row) else ""
                             for name, pos in idx.items()})
        if (i + 1) % 200 == 0:
            print(f"  已处理 {i+1}/{len(files)} 个文件", flush=True)

    df = pd.DataFrame(rows)
    print(f"总行数: {len(df)}")

    # TONE 字段是逗号分隔的 6 个数值，提取平均情感
    def avg_tone(t):
        try:
            vals = [float(x) for x in str(t).split(",")[:6]]
            return round(sum(vals) / len(vals), 2) if vals else None
        except ValueError:
            return None

    df["TONE_AVG"] = df["TONE"].apply(avg_tone)
    df["DATE"] = df["DATE"].astype(str).str[:8]
    df["DATE"] = pd.to_datetime(df["DATE"], format="%Y%m%d",
                                errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.sort_values("DATE").reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = OUT_DIR / "gkg_news_2015_2025.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"\n已导出: {out_csv}")
    print(f"日期范围: {df['DATE'].min()} ~ {df['DATE'].max()}")
    print(f"来源媒体数: {df['SOURCES'].nunique()}")
    print(f"\n按年份统计:")
    print(df.groupby(df["DATE"].str[:4]).size().to_string())


if __name__ == "__main__":
    main()
