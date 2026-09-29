# -*- coding: utf-8 -*-
"""
BERTopic 主题识别。

对 data/processed/topic_docs.csv 中的伪文档做主题聚类，
输出主题-关键词表与可视化 HTML。

输出：
  data/processed/bertopic_topics.csv     主题详情（关键词、词频、代表文档）
  data/processed/bertopic_assignment.csv 文档-主题映射
  data/processed/bertopic_visual.html    交互式可视化
"""
import os
import sys
from pathlib import Path

import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# 模型走国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from sentence_transformers import SentenceTransformer

DATA = Path(r"D:\users\PyCharmProgram\carbon\data\processed")
DOCS = DATA / "topic_docs.csv"
OUT_TOPICS = DATA / "bertopic_topics.csv"
OUT_ASSIGN = DATA / "bertopic_assignment.csv"
OUT_VIZ = DATA / "bertopic_visual.html"

N_TOPICS = 30          # 主题数上限（太少信息不足，太多不易解读）


def main():
    df = pd.read_csv(DOCS, encoding="utf-8-sig")
    df["doc"] = df["doc"].fillna("")
    docs = df["doc"].tolist()
    print(f"载入 {len(docs)} 篇文档，平均词数 "
          f"{sum(len(d.split()) for d in docs)//len(docs)}")

    print("加载嵌入模型 all-MiniLM-L6-v2 ...", flush=True)
    embed = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu")

    # UMAP：更小的 n_neighbors 保留局部结构，让相似主题抱团
    from umap import UMAP
    umap = UMAP(n_neighbors=10, n_components=5,
                min_dist=0.0, metric="cosine", random_state=42)

    # 用关键词增强表征，提取的主题词更可读
    rep = KeyBERTInspired(top_n_words=10)

    # 去掉纯数字/单字符噪声词
    vec = CountVectorizer(
        stop_words="english",
        min_df=5,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{2,}\b",
    )

    # HDBSCAN：更细的簇，减少离群
    cluster = HDBSCAN(
        min_cluster_size=15,
        min_samples=3,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

    print("开始 BERTopic 聚类（这一步较慢，请耐心）...", flush=True)
    topic_model = BERTopic(
        embedding_model=embed,
        umap_model=umap,
        representation_model=rep,
        vectorizer_model=vec,
        hdbscan_model=cluster,
        nr_topics=N_TOPICS,
        language="english",
        calculate_probabilities=False,
        verbose=True,
    )
    topics, _ = topic_model.fit_transform(docs)

    # ---------------- 主题详情表 ----------------
    info = topic_model.get_topic_info()
    print(f"\n识别出 {len(info) - 1} 个主题（-1 为离群）")
    print(info[["Topic", "Count", "Name"]].to_string(index=False))

    rows = []
    for tid in sorted(topic_model.get_topics().keys()):
        if tid == -1:
            continue
        words = topic_model.get_topic(tid)
        kw = ";".join(w for w, _ in words[:15])
        c = int((info.loc[info["Topic"] == tid, "Count"].iloc[0])
                if tid in info["Topic"].values else 0)
        rows.append({
            "topic_id": tid,
            "topic_name": info.loc[info["Topic"] == tid, "Name"].iloc[0]
                          if tid in info["Topic"].values else f"Topic_{tid}",
            "doc_count": c,
            "keywords": kw,
        })
    topics_df = pd.DataFrame(rows).sort_values("doc_count", ascending=False)
    topics_df.to_csv(OUT_TOPICS, index=False, encoding="utf-8-sig")
    print(f"\n主题表已导出: {OUT_TOPICS}")

    # ---------------- 文档-主题映射 ----------------
    assign = df[["date", "source", "url", "themes"]].copy()
    assign["doc"] = df["doc"]
    assign["topic"] = topics
    assign.to_csv(OUT_ASSIGN, index=False, encoding="utf-8-sig")
    print(f"文档映射已导出: {OUT_ASSIGN}")

    # ---------------- 可视化 ----------------
    try:
        fig = topic_model.visualize_topics()
        fig.write_html(str(OUT_VIZ))
        print(f"可视化已导出: {OUT_VIZ}")
    except Exception as e:
        print(f"可视化导出失败（不影响数据）: {e}")

    # 保存模型，后续可直接复用
    try:
        topic_model.save(
            str(DATA / "bertopic_model"),
            serialization="safetensors",
            save_embedding_model=False)
        print("模型已保存: data/processed/bertopic_model")
    except Exception as e:
        print(f"模型保存失败: {e}")


if __name__ == "__main__":
    main()
