# -*- coding: utf-8 -*-
"""
为BERTopic主题识别准备语料。

修复 噪声问题：
1. 收紧 URL 关键词：去掉 energy/power/green 等宽泛词，改用精确词组
2. 限制单一媒体占比（≤8%），避免地方媒体主导
3. 保留与绿色转型强相关的主题标签
"""
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

csv.field_size_limit(sys.maxsize)
GKG_DIR = Path(r"D:\users\PyCharmProgram\carbon\data\gkg")
OUT = Path(r"D:\users\PyCharmProgram\carbon\data\processed")
SAMPLE_TARGET = 50000
SEED = 42
MAX_PER_SOURCE = 2500          # 单一媒体最多占比

# 精确匹配的关键词（词组或带连字符的形式，避免宽泛词）
URL_KEYWORDS = [
    "electric-vehicle", "electric-vehicles", "electric-car", "electric-cars",
    "electric-vehicle-", "-electric-vehicle", "electricvehicle",
    "battery", "batteries", "lithium", "lithium-ion",
    "energy-storage", "energystorage",
    "solar-energy", "solar-power", "solar-panel", "solarenergy",
    "wind-energy", "wind-power", "windpower", "wind-turbine",
    "renewable-energy", "renewableenergy", "renewables",
    "carbon-tax", "carbon-price", "carbon-pricing", "carbon-emission",
    "carbon-footprint", "carbon-neutral", "carboncapture",
    "climate-change", "climatechange", "climate-policy",
    "decarbon", "net-zero", "netzero",
    "charging-station", "chargingstation", "chargepoint",
    "tesla", "byd", "rivian",
    "gigafactor", "fuel-cell", "fuelcell",
    "photovoltaic",
    "paris-agreement", "parisaccord", "cop21", "cop22",
    "greenhouse-gas", "greenhousegas",
    "clean-energy", "cleanenergy",
    "zero-emission", "zeroemission",
    "battery-fire", "battery-recycl", "battery-factory",
    "self-driving", "autonomous",
    "coal-power", "coalpower", "nuclear-power", "nuclearpower",
    "power-grid", "smart-grid", "smartgrid", "microgrid",
    "solarcity", "solaredge", "sunpower", "firstsolar", "sunrun",
    "chevy-bolt", "nissan-leaf", "powerwall",
]

# 明确排除的词（防止碰瓷）
EXCLUDE = [
    "battery dance", "battery park", "battery point",
    "union", "western-union", "credit-union",
    "green bay", "green-white", "green card", "greenwood",
    "power rangers", "power of", "powers", "empower",
    "energy drink", "energy bar",
    # 人名/地名碰瓷 nio-
    "antonio", "michail", "radio-nio", "polonio",
    # ev 子串碰瓷
    "twelve-v", "movie-v", "eviction", "evacuat", "evangel",
    "evanston", "seven-v", "love-v", "move-v",
    # battery 的法律含义（殴打罪）碰瓷
    "battery-of", "battery-charge", "battery-charge-dismissed",
    "domestic-battery", "battery-of-wife", "battery-case",
    "battery-conviction", "battery-assault", "assault-battery",
    "aggravated-battery", "battery-offense", "battery-sentence",
    "battery-misdemeanor", "battery-accusation", "battery-allegation",
    "battery-allegation", "battery-incident", "battery-park",
    "battery-dance", "battery-point", "battery-theft",
    "assault", "arraigned", "pleads", "indicted", "misdemeanor",
]

KEEP_THEMES = {
    "ENV_SOLAR", "ENV_WINDPOWER", "ENV_HYDRO", "ENV_GEOTHERMAL",
    "ENV_BIOFUEL", "ENV_NUCLEARPOWER", "ENV_CLIMATECHANGE",
    "ENV_CARBONCAPTURE", "ENV_GREEN", "ENV_COAL", "ENV_OIL",
    "ENV_NATURALGAS", "ENV_MINING", "ENV_METALS",
    "WB_525_RENEWABLE_ENERGY", "WB_528_SOLAR_ENERGY", "WB_529_WIND_ENERGY",
    "WB_527_HYDROPOWER", "WB_530_GEOTHERMAL_ENERGY", "WB_531_BIOMASS_ENERGY",
    "WB_532_BIOFUELS_ENERGY", "WB_567_CLIMATE_CHANGE",
    "WB_579_CLIMATE_CHANGE_MITIGATION", "WB_580_LOW_CARBON_DEVELOPMENT",
    "WB_533_ENERGY_EFFICIENCY", "WB_511_COAL_FIRED_POWER",
    "WB_509_NUCLEAR_ENERGY", "ECON_ELECTRICALGENERATION",
    "UNGP_CLIMATE_CHANGE_ACTION",
}

TLD = re.compile(r"\.(com|org|net|edu|gov|co|io|uk|au|ca|de|fr|jp|cn|in)$")
TRAIL_ID = re.compile(r"[-_]\d{3,}$")
PURE_ID = re.compile(r"^[\d\-a-f]{8,}$", re.I)

NOISE = {
    "article", "articles", "news", "story", "post", "page", "html",
    "htm", "php", "index", "home", "main", "says", "new", "us", "uk",
    "eu", "img", "photo", "video", "watch", "read", "more", "share",
    "ap", "reuters", "associated", "press", "twitter", "facebook",
    "google", "youtube", "instagram", "wikipedia",
}


def url_to_title(url: str) -> str:
    path = url.split("//", 1)[-1].split("/", 1)[-1]
    path = path.rsplit(".", 1)[0]
    segs = [s for s in path.split("/") if s]
    if not segs:
        return ""
    words = []
    for seg in segs[-2:]:
        seg = seg.replace("-", " ").replace("_", " ").replace("+", " ")
        for w in seg.split():
            w = w.strip(".,")
            if len(w) < 3 or w.isdigit() or w.lower() in NOISE:
                continue
            if TRAIL_ID.search(w) or PURE_ID.match(w):
                continue
            words.append(w.lower())
    return " ".join(words[:15])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    seen_urls = set()
    per_source = defaultdict(int)
    rows_out = []
    green_seen = 0
    files = sorted(GKG_DIR.glob("*.csv"))

    # 把关键词编译成词边界正则：只匹配被非字母字符包围的完整词
    # 用一个 alternation 正则一次匹配所有关键词，避免逐个扫描
    alt = "|".join(re.escape(kw) for kw in URL_KEYWORDS)
    kw_re = re.compile(r"(?<![a-z0-9])(?:" + alt + r")(?![a-z0-9])")
    excl_alt = "|".join(re.escape(x) for x in EXCLUDE)
    excl_re = re.compile(excl_alt)

    print(f"扫描 {len(files)} 个文件，精确关键词筛选...", flush=True)

    for i, f in enumerate(files):
        with open(f, encoding="utf-8") as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = next(reader, None)
            if not header:
                continue
            t_i, o_i = header.index("THEMES"), header.index("ORGANIZATIONS")
            s_i, u_i = header.index("SOURCES"), header.index("SOURCEURLS")
            for row in reader:
                url = row[u_i].lower()
                if not kw_re.search(url):
                    continue
                if excl_re.search(url):
                    continue
                title = url_to_title(row[u_i])
                if len(title.split()) < 3:
                    continue
                if url in seen_urls:
                    continue
                src = TLD.sub("", row[s_i].split(";")[0]).lower()
                if per_source.get(src, 0) >= MAX_PER_SOURCE:
                    continue
                seen_urls.add(url)
                per_source[src] += 1
                green_seen += 1
                if len(rows_out) < SAMPLE_TARGET:
                    rows_out.append((row, src))
                else:
                    j = rng.randint(0, green_seen - 1)
                    if j < SAMPLE_TARGET:
                        rows_out[j] = (row, src)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(files)}，命中 {green_seen}，"
                  f"采样 {len(rows_out)}", flush=True)

    rng.shuffle(rows_out)
    print(f"命中 {green_seen} 篇，采样 {len(rows_out)} 篇，"
          f"媒体数 {len(per_source)}")

    out_file = OUT / "topic_docs.csv"
    with open(out_file, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["doc", "date", "source", "url", "orgs", "themes"])
        for row, src in rows_out:
            title = url_to_title(row[u_i])
            kept = [t.replace("_", " ") for t in row[t_i].split(";")
                    if t in KEEP_THEMES]
            orgs = row[o_i].replace(";", " ").lower()
            doc = " ".join(filter(None, [title] + kept[:5] + [orgs[:60]]))
            w.writerow([doc.strip()[:400], row[0], src,
                        row[u_i][:250], orgs[:200], row[t_i][:300]])
    print(f"已导出: {out_file}")


if __name__ == "__main__":
    main()
