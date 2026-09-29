# -*- coding: utf-8 -*-
# 汇总 BERTopic 主题识别结果，输出中文解读报告
import sys
from pathlib import Path

import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

DATA = Path(r"D:\users\PyCharmProgram\carbon\data\processed")
topics = pd.read_csv(DATA / "bertopic_topics.csv", encoding="utf-8-sig")
assign = pd.read_csv(DATA / "bertopic_assignment.csv", encoding="utf-8-sig")

total = len(assign)
outlier = (assign["topic"] == -1).sum()
print(f"文档总数: {total}，离群: {outlier} ({outlier/total*100:.1f}%)")
print(f"有效主题: {len(topics)} 个\n")

# 人工解读的主题名（英文关键词 -> 中文）
INTERPRET = {
    0: ("可再生能源/太阳能", "太阳能发电、可再生能源政策与市场"),
    1: ("特斯拉企业与产品", "Tesla 公司动态、车型、股价"),
    2: ("气候变化议题", "气候变化、环境政策讨论"),
    3: ("自动驾驶与事故", "Autopilot 自动驾驶、事故与监管"),
    4: ("锂矿与上游材料", "锂、金属开采、原材料供应"),
    5: ("三星电池召回", "三星电池起火/召回事件"),
    6: ("电池产业与市场", "电池制造、技术、工厂、市场动态"),
    7: ("消费电子电池", "手机/笔电电池续航"),
    9: ("锂电池技术", "锂离子/聚合物电池技术"),
    10: ("自动驾驶/出行", "自动驾驶、共享出行"),
    13: ("电动汽车", "电动车整车产品"),
    14: ("电池工厂与产能", "电池生产基地、产能建设"),
    15: ("汽车召回", "整车召回事件"),
    16: ("资本市场", "证券、评级、上市公司"),
    24: ("传统车企转型", "丰田/三菱/克莱斯勒电动化"),
    27: ("储能与电网", "电网储能、电池成本"),
    8: ("法律/犯罪噪声", "battery 法律含义"),
    11: ("法律/犯罪噪声", "battery 法律含义"),
    21: ("法律/犯罪噪声", "监狱/判决"),
    26: ("法律/犯罪噪声", "battery 法律含义"),
    22: ("诉讼与法院", "法院诉讼"),
    20: ("科研噪声", "锂的科研发现"),
    18: ("地缘政治噪声", "韩国军事"),
    19: ("政治噪声", "商务部/委员会"),
    12: ("航空噪声", "机场/航班"),
    17: ("芯片与自动驾驶", "英伟达/AI 芯片"),
    25: ("电池组硬件", "电池组/配件"),
    28: ("监管与特斯拉", "监管机构与特斯拉"),
}

rows = []
for _, r in topics.iterrows():
    tid = int(r["topic_id"])
    name, desc = INTERPRET.get(tid, ("待解读", f"topic_{tid}"))
    rows.append({
        "主题ID": tid,
        "中文主题": name,
        "主题说明": desc,
        "文档数": int(r["doc_count"]),
        "占比%": round(int(r["doc_count"]) / total * 100, 2),
        "关键词": r["keywords"],
    })
df = pd.DataFrame(rows).sort_values("文档数", ascending=False)
df.to_csv(DATA / "bertopic_topics_cn.csv", index=False, encoding="utf-8-sig")

print(f"{'主题':<18}{'文档数':>7}{'占比':>8}  关键词")
print("-" * 100)
for _, r in df.iterrows():
    if r["中文主题"] == "待解读":
        continue
    print(f"{r['中文主题']:<18}{r['文档数']:>7}{r['占比%']:>7}%  "
          f"{str(r['关键词'])[:60]}")

noise = df[df["中文主题"].str.contains("噪声")]
print(f"\n噪声主题文档: {noise['文档数'].sum()} 篇 "
      f"({noise['文档数'].sum()/total*100:.1f}%)")
print(f"\n报告已导出: {DATA / 'bertopic_topics_cn.csv'}")
