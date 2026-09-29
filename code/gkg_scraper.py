# -*- coding: utf-8 -*-
"""
GDELT GKG 离线新闻抓取脚本（2015-2025）。

数据源：https://data.gdeltproject.org/gkg/YYYYMMDD.gkg.csv.zip

用法：
    python gkg_scraper.py                          # 全量 2015-2025
    python gkg_scraper.py --resume                 # 断点续传
"""
import argparse
import csv
import logging
import os
import sys
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import requests

# GKG 的 THEMES/LOCATIONS 字段可能超过 csv 默认的 128KB 上限，必须放大
csv.field_size_limit(sys.maxsize)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
GKG_DIR = DATA_DIR / "gkg"           # 每天的筛选结果（csv）
ZIP_DIR = DATA_DIR / "gkg_zips"      # 下载的原始 zip
STATE_FILE = DATA_DIR / "state_gkg.json"
LOG_DIR = PROJECT_ROOT / "logs"

BASE_URL = "https://data.gdeltproject.org/gkg/{ymd}.gkg.csv.zip"

# 关键词：在 THEMES / ORGANIZATIONS / SOURCEURLS 中匹配
KEYWORDS = [
    # 新能源汽车
    "electric vehicle", "electric vehicles",
    "electric car", "electric cars",
    "tesla", "byd", "nio", "rivian",
    "battery", "batteries",
    "lithium", "lithium-ion",
    "energy storage",
    "renewable energy",
    "solar", "photovoltaic",
    # 碳政策
    "carbon tax", "carbon pricing",
    "carbon emission", "carbon emissions",
    "climate policy",
    "decarbonization", "decarbonisation",
    "net zero", "net-zero",
    "paris agreement",
    "greenhouse gas",
]

# 关键词在哪些字段中匹配（0-based 列号）
COL_THEMES = 3
COL_ORGS = 6
COL_SOURCES = 9
COL_URLS = 10
SEARCH_COLS = [COL_THEMES, COL_ORGS, COL_SOURCES, COL_URLS]

REQUEST_TIMEOUT = 120


def setup_logging() -> logging.Logger:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("gkg_scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%H:%M:%S")
    fh = logging.FileHandler(
        LOG_DIR / f"gkg_{datetime.now():%Y%m%d_%H%M%S}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def daterange(start: datetime, end: datetime):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def matches(row: list, kws: list) -> bool:
    """检查一行是否命中任一关键词（大小写不敏感）"""
    for col in SEARCH_COLS:
        if col >= len(row):
            continue
        text = row[col].lower()
        for kw in kws:
            if kw in text:
                return True
    return False


def download_day(day: datetime, logger: logging.Logger) -> str | None:
    # 下载并解压一天的 gkg，返回内部 csv 文件名；失败返回 None
    ymd = day.strftime("%Y%m%d")
    url = BASE_URL.format(ymd=ymd)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.warning(f"[{ymd}] 网络异常: {e}")
        return None
    if r.status_code != 200:
        logger.warning(f"[{ymd}] HTTP {r.status_code}")
        return None
    try:
        with zipfile.ZipFile(BytesIO(r.content)) as z:
            return z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, OSError) as e:
        logger.warning(f"[{ymd}] 解压失败: {e}")
        return None


def process_day(day: datetime, kws: list, logger: logging.Logger) -> int:
    # 处理一天的数据，筛选命中关键词的行，返回命中条数；失败返回 -1
    ymd = day.strftime("%Y%m%d")
    content = download_day(day, logger)
    if content is None:
        return -1

    try:
        reader = csv.reader(content.splitlines(), delimiter="\t")
        header = next(reader, None)
        if not header:
            return -1

        out_lines = ["\t".join(header)]
        hit = 0
        for row in reader:
            if matches(row, kws):
                out_lines.append("\t".join(row))
                hit += 1

        out_file = GKG_DIR / f"{ymd}.csv"
        with open(out_file, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(out_lines))
        return hit
    except (csv.Error, OSError) as e:
        logger.warning(f"[{ymd}] 解析失败: {e}")
        return -1


def main():
    ap = argparse.ArgumentParser(description="GDELT GKG 离线新闻抓取 2015-2025")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    logger = setup_logging()
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    GKG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    import json
    done = set()
    if STATE_FILE.exists():
        done = set(json.load(open(STATE_FILE, encoding="utf-8")).get("done", []))

    total_days = (end - start).days + 1
    logger.info(f"时间范围: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}，共 {total_days} 天")
    logger.info(f"关键词: {KEYWORDS}")

    processed = 0
    hits = 0
    failed = []
    for day in daterange(start, end):
        ymd = day.strftime("%Y%m%d")
        if args.resume and ymd in done:
            continue
        hit = process_day(day, KEYWORDS, logger)
        if hit < 0:
            failed.append(ymd)
            continue
        done.add(ymd)
        json.dump({"done": sorted(done)}, open(STATE_FILE, "w", encoding="utf-8"))
        processed += 1
        hits += hit
        if processed % 10 == 0 or hit > 0:
            logger.info(f"[{ymd}] 累计 {processed}/{total_days} 天，"
                        f"命中 {hit} 条（总 {hits}）")

    if failed:
        logger.warning(f"失败 {len(failed)} 天: {failed[:20]}")
    logger.info(f"完成：{processed} 天，共 {hits} 条命中")


if __name__ == "__main__":
    main()
