# -*- coding: utf-8 -*-
"""
绿色转型词典构建

基于数据中实际存在的GDELT主题标签体系，
将1016万篇报道归类到绿色转型子领域，并挖掘各领域的高频企业。

输出：
  data/processed/green_transition_lexicon.json
  data/processed/green_transition_lexicon.csv
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

csv.field_size_limit(sys.maxsize)
GKG_DIR = Path(r"D:\users\PyCharmProgram\carbon\data\gkg")
OUT_DIR = Path(r"D:\users\PyCharmProgram\carbon\data\processed")

# --------------------------------------------------------------------------
# 分类规则：使用数据中真实存在的 GDELT 主题标签
# --------------------------------------------------------------------------

CATEGORY_THEMES = {
    "新能源汽车与交通电动化": [
        "WB_135_TRANSPORT",
        "WB_164_MODES_OF_TRANSPORT",
        "WB_536_ENERGY_EFFICIENT_TRANSPORT",
        "ECON_ELECTRICALGENERATION",
    ],
    "电池与储能": [
        "ENV_METALS",
        "WB_507_ENERGY_AND_EXTRACTIVES",
        "WB_508_POWER_SYSTEMS",
        "WB_510_POWER_TRANSMISSION",
        "WB_517_ELECTRICITY_MARKET_DESIGN_AND_REGULATION",
        "WB_519_UTILITIES_GOVERNANCE_AND_PERFORMANCE",
        "WB_521_ENERGY_ACCESS",
    ],
    "清洁能源": [
        "ENV_SOLAR", "ENV_WINDPOWER", "ENV_HYDRO", "ENV_GEOTHERMAL",
        "ENV_BIOFUEL", "ENV_NUCLEARPOWER",
        "WB_525_RENEWABLE_ENERGY",
        "WB_526_RENEWABLE_ENERGY_POLICY_AND_REGULATION",
        "WB_527_HYDROPOWER", "WB_528_SOLAR_ENERGY", "WB_529_WIND_ENERGY",
        "WB_530_GEOTHERMAL_ENERGY", "WB_531_BIOMASS_ENERGY",
        "WB_532_BIOFUELS_ENERGY",
    ],
    "传统能源转型": [
        "ENV_COAL", "ENV_OIL", "ENV_NATURALGAS", "ENV_MINING",
        "WB_511_COAL_FIRED_POWER", "WB_512_GAS_FIRED_POWER",
        "WB_513_OIL_FIRED_POWER", "WB_539_OIL_AND_GAS_POLICY_STRATEGY_AND_INSTITUTIONS",
        "WB_545_NATIONAL_OIL_COMPANIES", "WB_548_PPP_IN_OIL_AND_GAS",
        "WB_549_OIL_AND_GAS_SYSTEMS", "WB_509_NUCLEAR_ENERGY",
    ],
    "碳减排与气候治理": [
        "ENV_CLIMATECHANGE", "ENV_CARBONCAPTURE", "ENV_GREEN",
        "WB_567_CLIMATE_CHANGE", "WB_568_CLIMATE_SERVICES",
        "WB_571_CLIMATE_SCIENCE", "WB_572_CLIMATE_RESILIENT_DEVELOPMENT",
        "WB_573_CLIMATE_RISK_MANAGEMENT", "WB_574_CLIMATE_CHANGE_ADAPTATION",
        "WB_579_CLIMATE_CHANGE_MITIGATION", "WB_580_LOW_CARBON_DEVELOPMENT",
        "WB_582_GREENHOUSE_GAS_ACCOUNTING",
        "UNGP_CLIMATE_CHANGE_ACTION",
        "WB_1100_SUSTAINABLE_GROWTH",
        "WB_533_ENERGY_EFFICIENCY",
        "WB_1949_CLIMATE_SMART_AGRICULTURE",
    ],
    "生态与环境治理": [
        "ENV_DEFORESTATION", "ENV_FORESTRY", "ENV_FISHERY", "ENV_OVERFISH",
        "ENV_POACHING", "ENV_SPECIESENDANGERED", "ENV_SPECIESEXTINCT",
        "ENV_WATERWAYS",
        "WB_566_ENVIRONMENT_AND_NATURAL_RESOURCES",
        "WB_590_ECOSYSTEMS", "WB_594_WETLANDS", "WB_595_DRYLANDS",
        "WB_596_COASTAL_AND_MARINE_ECOSYSTEMS",
        "WB_598_ENVIRONMENTAL_MANAGEMENT",
        "WB_588_CONSERVATION_FINANCE", "WB_589_ECOTOURISM",
        "WB_1777_FORESTS", "WATER_SECURITY",
        "UNGP_FORESTS_RIVERS_OCEANS",
    ],
}

# 中文标签 -> 对应领域（用于产出双语词典）
CATEGORY_CN_EN = {
    "新能源汽车与交通电动化": "New Energy Vehicles & Transport Electrification",
    "电池与储能": "Battery & Energy Storage",
    "清洁能源": "Clean Energy",
    "传统能源转型": "Fossil Energy Transition",
    "碳减排与气候治理": "Carbon Reduction & Climate Governance",
    "生态与环境治理": "Ecology & Environmental Governance",
}

# --------------------------------------------------------------------------
# 核心词条（人工整理的中英双语种子词表）
# 用于文本分析时识别绿色转型相关表述
# --------------------------------------------------------------------------
CORE_TERMS = {
    "新能源汽车与交通电动化": [
        ("electric vehicle", "电动汽车"), ("electric car", "电动轿车"),
        ("electric vehicles", "电动汽车"), ("EV", "电动车"),
        ("battery electric vehicle", "纯电动汽车"), ("BEV", "纯电动车"),
        ("plug-in hybrid", "插电式混合动力"), ("hybrid vehicle", "混合动力汽车"),
        ("new energy vehicle", "新能源汽车"), ("NEV", "新能源汽车"),
        ("vehicle electrification", "汽车电动化"), ("charging station", "充电站"),
        ("charging pile", "充电桩"), ("charging infrastructure", "充电基础设施"),
        ("tesla", "特斯拉"), ("byd", "比亚迪"), ("nio", "蔚来"),
        ("rivian", "里维安"), ("lucid motors", " lucid 汽车"),
        ("xpeng", "小鹏"), ("li auto", "理想汽车"),
        ("zero emission vehicle", "零排放汽车"), ("fuel cell vehicle", "燃料电池汽车"),
    ],
    "电池与储能": [
        ("lithium battery", "锂电池"), ("lithium-ion battery", "锂离子电池"),
        ("battery", "电池"), ("batteries", "电池组"),
        ("battery pack", "电池组"), ("battery cell", "电芯"),
        ("solid-state battery", "固态电池"), ("sodium-ion battery", "钠离子电池"),
        ("lithium iron phosphate", "磷酸铁锂"), ("ternary battery", "三元电池"),
        ("gigafactory", "超级工厂"), ("battery factory", "电池工厂"),
        ("battery manufacturing", "电池制造"), ("battery recycling", "电池回收"),
        ("energy storage", "储能"), ("energy storage system", "储能系统"),
        ("battery energy storage", "电池储能"), ("energy storage capacity", "储能容量"),
        ("rechargeable battery", "可充电电池"), ("battery life", "电池寿命"),
        ("battery safety", "电池安全"), ("battery fire", "电池起火"),
        ("lithium", "锂"), ("cobalt", "钴"), ("nickel", "镍"),
        ("graphite anode", "石墨负极"), ("cathode material", "正极材料"),
        ("electrolyte", "电解液"), ("separator", "隔膜"),
    ],
    "清洁能源": [
        ("renewable energy", "可再生能源"), ("clean energy", "清洁能源"),
        ("green energy", "绿色能源"), ("solar energy", "太阳能"),
        ("solar power", "光伏发电"), ("photovoltaic", "光伏"),
        ("solar panel", "太阳能板"), ("polysilicon", "多晶硅"),
        ("wind power", "风电"), ("wind energy", "风能"),
        ("wind turbine", "风力发电机"), ("onshore wind", "陆上风电"),
        ("offshore wind", "海上风电"), ("hydropower", "水电"),
        ("hydroelectric power", "水电"), ("geothermal energy", "地热能"),
        ("biomass energy", "生物质能"), ("biofuel", "生物燃料"),
        ("tidal energy", "潮汐能"), ("nuclear power", "核电"),
        ("distributed generation", "分布式发电"), ("microgrid", "微电网"),
        ("smart grid", "智能电网"), ("grid connection", "并网"),
        ("installed capacity", "装机容量"), ("levelized cost of energy", "度电成本"),
    ],
    "传统能源转型": [
        ("energy transition", "能源转型"), ("fossil fuel", "化石燃料"),
        ("coal", "煤炭"), ("coal-fired power", "燃煤发电"),
        ("oil", "石油"), ("crude oil", "原油"), ("natural gas", "天然气"),
        ("shale gas", "页岩气"), ("petroleum", "石油"),
        ("coal phase-out", "淘汰煤炭"), ("stranded asset", "搁浅资产"),
        ("divestment", "撤资"), ("carbon bubble", "碳泡沫"),
        ("peak oil", "石油峰值"), ("oil spill", "漏油事件"),
        ("energy security", "能源安全"), ("energy independence", "能源独立"),
        ("fuel economy", "燃油经济性"), ("energy efficiency", "能效"),
        ("retrofit", "改造升级"), ("carbon-intensive", "高碳"),
    ],
    "碳减排与气候治理": [
        ("carbon neutrality", "碳中和"), ("carbon neutral", "碳中和"),
        ("net zero", "净零排放"), ("net-zero", "净零"),
        ("carbon peak", "碳达峰"), ("decarbonization", "脱碳"),
        ("decarbonisation", "脱碳"), ("low-carbon", "低碳"),
        ("carbon emission", "碳排放"), ("carbon emissions", "碳排放"),
        ("carbon footprint", "碳足迹"), ("carbon tax", "碳税"),
        ("carbon pricing", "碳定价"), ("carbon trading", "碳交易"),
        ("carbon market", "碳市场"), ("carbon credit", "碳信用"),
        ("carbon offset", "碳抵消"), ("carbon allowance", "碳配额"),
        ("cap and trade", "总量管制与交易"), ("emissions trading system", "碳排放权交易体系"),
        ("ETS", "碳交易体系"), ("carbon capture", "碳捕集"),
        ("carbon capture and storage", "碳捕集与封存"), ("CCS", "碳捕集封存"),
        ("carbon sequestration", "碳汇"), ("greenhouse gas", "温室气体"),
        ("GHG", "温室气体"), ("CO2 emission", "二氧化碳排放"),
        ("emission reduction", "减排"), ("carbon intensity", "碳强度"),
        ("carbon disclosure", "碳披露"), ("carbon accounting", "碳核算"),
        ("climate change", "气候变化"), ("global warming", "全球变暖"),
        ("climate policy", "气候政策"), ("climate action", "气候行动"),
        ("climate target", "气候目标"), ("climate goal", "气候目标"),
        ("climate risk", "气候风险"), ("climate finance", "气候金融"),
        ("paris agreement", "巴黎协定"), ("paris accord", "巴黎协定"),
        ("nationally determined contribution", "国家自主贡献"),
        ("green deal", "绿色新政"), ("green transition", "绿色转型"),
        ("just transition", "公正转型"), ("sustainable development", "可持续发展"),
        ("ESG", "环境社会治理"), ("green finance", "绿色金融"),
        ("green bond", "绿色债券"), ("carbon pricing mechanism", "碳定价机制"),
    ],
    "生态与环境治理": [
        ("environmental protection", "环境保护"), ("pollution", "污染"),
        ("air pollution", "空气污染"), ("water pollution", "水污染"),
        ("soil pollution", "土壤污染"), ("smog", "雾霾"),
        ("PM2.5", "细颗粒物"), ("emission standard", "排放标准"),
        ("pollution control", "污染治理"), ("environmental regulation", "环境监管"),
        ("environmental law", "环保法律"), ("environmental compliance", "环保合规"),
        ("waste management", "废物管理"), ("hazardous waste", "危险废物"),
        ("recycling", "回收利用"), ("circular economy", "循环经济"),
        ("waste-to-energy", "垃圾发电"), ("sewage treatment", "污水处理"),
        ("desulfurization", "脱硫"), ("denitrification", "脱硝"),
        ("deforestation", "森林砍伐"), ("afforestation", "植树造林"),
        ("biodiversity", "生物多样性"), ("ecological restoration", "生态修复"),
        ("water conservation", "节水"), ("water treatment", "水处理"),
        ("plastic ban", "限塑令"), ("single-use plastic", "一次性塑料"),
        ("environmental impact assessment", "环境影响评价"),
        ("environmental violation", "环境违法"), ("environmental penalty", "环保处罚"),
    ],
}


def main():
    files = sorted(GKG_DIR.glob("*.csv"))
    print(f"处理 {len(files)} 个文件...", flush=True)

    # theme -> category 映射（直接基于标签名，无需正则）
    theme_cat = {}
    for cat, themes in CATEGORY_THEMES.items():
        for t in themes:
            theme_cat[t] = cat
    cat_theme_counts = {cat: Counter() for cat in CATEGORY_THEMES}

    org_in_green = defaultdict(Counter)   # category -> (org -> count)
    src_in_green = defaultdict(Counter)   # category -> (source -> count)
    all_green_orgs = Counter()
    total_rows = 0
    total_green_rows = 0

    # 核心词条频次统计：在 ORGANIZATIONS + SOURCEURLS 中检索
    # （GKG 无正文，但 URL 常含标题关键词，如 /electric-vehicle-xxx/）
    # 快速方案：把行文本归一化后分词，单词用集合查找，短语用首词过滤 + 子串查找
    core_en = [en for terms in CORE_TERMS.values() for en, _ in terms]

    def norm(s: str) -> str:
        """统一分隔符为单空格，用于把命中串映射回核心词"""
        return re.sub(r"[-_\s]+", " ", s.lower()).strip()

    # 归一化后的词条 -> （单词 / 短语）
    norm_terms = {norm(en) for en in core_en}
    core_single = {t for t in norm_terms if " " not in t}
    core_multi = [t for t in norm_terms if " " in t]
    multi_heads = {}
    for t in core_multi:
        multi_heads.setdefault(t.split(" ")[0], []).append(t)
    core_counts = Counter()  # 归一化词条 -> 命中篇数

    for i, f in enumerate(files):
        with open(f, encoding="utf-8") as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = next(reader, None)
            if not header:
                continue
            t_idx = header.index("THEMES")
            o_idx = header.index("ORGANIZATIONS")
            s_idx = header.index("SOURCES")
            u_idx = header.index("SOURCEURLS")
            for row in reader:
                total_rows += 1
                # 核心词条频次：在组织名 + URL 文本中匹配（每篇只计一次）
                blob = row[o_idx] + " " + row[u_idx]
                nb = blob.replace("-", " ").replace("_", " ").lower()
                words = set(nb.split())
                for t in core_single:
                    if t in words or (t + "s") in words:
                        core_counts[t] += 1
                for head, phrases in multi_heads.items():
                    if head in words:
                        for t in phrases:
                            if t in nb:
                                core_counts[t] += 1
                cats = set()
                for t in row[t_idx].split(";"):
                    c = theme_cat.get(t)
                    if c:
                        cats.add(c)
                        cat_theme_counts[c][t] += 1
                if not cats:
                    continue
                total_green_rows += 1
                orgs = [o.strip().lower() for o in
                        row[o_idx].split(";") if o.strip()]
                srcs = [s.strip().lower() for s in
                        row[s_idx].split(";") if s.strip()]
                for cat in cats:
                    org_in_green[cat].update(orgs)
                    src_in_green[cat].update(srcs)
                all_green_orgs.update(orgs)
        if (i + 1) % 200 == 0:
            print(f"  已处理 {i+1}/{len(files)} 文件，"
                  f"{total_rows} 篇报道", flush=True)

    # ---------------- 构建词典 ----------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lexicon = {
        "meta": {
            "source": "GDELT GKG 2015-01-01 ~ 2017-02-05 (767 天)",
            "total_articles": total_rows,
            "green_articles": total_green_rows,
            "green_ratio": round(total_green_rows / total_rows * 100, 2),
            "description": "绿色转型词典：新能源汽车/电池/清洁能源/碳政策/生态环境",
        },
        "categories": {},
    }

    # 需要过滤掉的非实体组织（政府机构、政党、媒体、通用词）
    STOP_ORGS = {
        "united states", "european union", "china", "russia", "japan",
        "india", "germany", "france", "united kingdom", "canada",
        "australia", "brazil", "white house", "supreme court",
        "united nations", "associated press", "reuters", "bloomberg",
        "google", "twitter", "facebook", "nasdaq", "group inc",
        "department of energy", "environmental protection agency",
        "world bank", "european space agency", "international monetary fund",
        "new york times", "washington post", "cnn", "bbc", "fox news",
        "wall street journal", "the guardian", "usa today", "nbc news",
        "cbs news", "abc news", "xinhua", "people daily", "china daily",
        # GDELT 误判为组织的通用词
        "renewable energy", "pacific partnership", "young", "junior",
        "sterling", "russian federation", "national assembly",
        "human rights watch", "amnesty international", "linkedin",
        "national oceanic", "york mercantile exchange", "common wealth",
        "greenpeace", "sierra club",
        # 第二轮补充：机构/政府/媒体误判
        "oval office", "foreign affairs", "national park service",
        "national transportation safety board", "venture exchange",
        "toronto stock exchange", "new york mercantile exchange",
        "york stock exchange", "zacks investment research",
        "propulsion laboratory", "agenda for sustainable development",
        "bloomberg new energy", "ipcc", "yahoo", "mcdonald",
    }

    # 非企业实体的特征词：出现在组织名里则判定为机构而非公司
    NON_CORP_KW = (
        "party", "ministry", "department", "commission", "council",
        "parliament", "congress", "senate", "court", "agency", "bureau",
        "institute", "university", "college", "bank", "news", "times",
        "press", "media", "television", "radio", "union", "foundation",
        "association", "society", "organization", "authority", "committee",
        "government", "administration", "presidency", "embassy", "military",
        "army", "police", "security council", "development goals",
        "civil liberties", "exchange commission", "central bank",
        "reserve", "labor party", "labour party", "republican", "democratic",
        "socialist", "national front", "green party", "liberal",
        "youtube", "instagram", "wikipedia", "nasdaq", "dow jones",
        "s&p", "moody", "fitch", "commonwealth", "african union",
        "european commission", "european parliament", "european council",
        "european central", "federal", "justice", "state media",
    )

    def is_company(name: str) -> bool:
        n = name.strip()
        if not n or len(n) < 3 or n in STOP_ORGS:
            return False
        if any(kw in n for kw in NON_CORP_KW):
            return False
        # 纯国家/城市名
        if n in {"united states", "european union", "china", "russia",
                 "japan", "india", "germany", "france", "united kingdom",
                 "canada", "australia", "brazil"}:
            return False
        return True

    def filter_orgs(counter, n):
        return [(o, c) for o, c in counter.most_common(n * 6)
                if is_company(o)][:n]

    for cat in CATEGORY_THEMES:
        top_themes = cat_theme_counts[cat].most_common(15)
        top_orgs = filter_orgs(org_in_green[cat], 40)
        top_srcs = src_in_green[cat].most_common(15)

        def term_count(en: str) -> int:
            """核心词频次：归一化后的命中篇数"""
            return core_counts.get(norm(en), 0)

        core_list = [
            {"en": en, "zh": zh, "count": term_count(en)}
            for en, zh in CORE_TERMS.get(cat, [])
        ]
        # 核心词按频次降序，便于查看哪些词最有信号
        core_list.sort(key=lambda x: -x["count"])

        lexicon["categories"][cat] = {
            "name_en": CATEGORY_CN_EN[cat],
            "core_terms": core_list,
            "themes": [{"term": t, "count": n} for t, n in top_themes],
            "organizations": [{"term": o, "count": n} for o, n in top_orgs],
            "sources": [{"term": s, "count": n} for s, n in top_srcs],
        }
        print(f"\n=== {cat} / {CATEGORY_CN_EN[cat]} ===")
        print(f"  核心词: {len(core_list)} 条")
        print(f"  主题: {[t for t, _ in top_themes[:5]]}")
        print(f"  企业: {[o for o, _ in top_orgs[:8]]}")

    top_all = filter_orgs(all_green_orgs, 100)
    lexicon["top_organizations"] = [{"term": o, "count": n} for o, n in top_all]
    print(f"\n=== 绿色转型总体高频企业 Top 20 ===")
    for o, n in top_all[:20]:
        print(f"  {o:<40} {n}")

    out_json = OUT_DIR / "green_transition_lexicon.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)

    # ---------------- 平铺版 CSV（Excel 友好）----------------
    out_csv = OUT_DIR / "green_transition_lexicon.csv"
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["领域", "领域英文", "类型", "词条", "词条中文", "词频"])
        for cat, data in lexicon["categories"].items():
            for item in data["core_terms"]:
                w.writerow([cat, data["name_en"], "核心词条",
                            item["en"], item["zh"], item["count"]])
            for item in data["themes"]:
                w.writerow([cat, data["name_en"], "主题标签", item["term"], "", item["count"]])
            for item in data["organizations"]:
                w.writerow([cat, data["name_en"], "企业组织", item["term"], "", item["count"]])
            for item in data["sources"]:
                w.writerow([cat, data["name_en"], "媒体来源", item["term"], "", item["count"]])
        for item in lexicon["top_organizations"]:
            w.writerow(["跨领域综合", "Cross-domain", "企业组织", item["term"], "", item["count"]])

    print(f"\n词典已导出:")
    print(f"  JSON: {out_json}")
    print(f"  CSV : {out_csv}")


if __name__ == "__main__":
    main()
