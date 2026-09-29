# 新能源汽车 / 碳政策新闻抓取（2015-2025）

抓取 2015-2025 年新能源汽车企业风险相关新闻。

## 数据源说明

使用 **GDELT GKG 离线数据库**（直接下载按日打包的历史文件）。

**为什么不使用 GDELT DOC API：**
DOC API 官方文档明确限制 `startdatetime`/`enddatetime` **必须在最近 3 个月内**，
无法查询 2015-2025 的历史数据。离线 GKG 文件没有这个限制，且数据更丰富
（含组织、情感倾向 TONE）。

## 环境要求

Python 3.9+，依赖 `requests`、`pandas`：

```bash
pip install requests pandas
```

## 使用方法

```bash
# 全量抓取 2015-2025
python gkg_scraper.py

# 指定日期范围
python gkg_scraper.py --start 2020-01-01 --end 2025-12-31

# 断点续传（中断后从上次位置继续）
python gkg_scraper.py --resume

# 合并导出最终数据集
python merge_gkg.py
```

## 输出

```
data/gkg/YYYYMMDD.csv       按天的筛选结果（TSV）
data/processed/gkg_news_2015_2025.csv   合并后的最终数据集（Excel 友好）
data/state_gkg.json         断点续传状态
```

### 字段说明

| 字段 | 说明 |
|------|------|
| DATE | 新闻日期 |
| NUMARTS | 该组文章数 |
| THEMES | GDELT 主题标签 |
| ORGANIZATIONS | 涉及的企业/组织（如 tesla motors） |
| TONE / TONE_AVG | 情感倾向（负值=负面，风险评估关键指标） |
| SOURCES | 来源媒体 |
| SOURCEURLS | 新闻链接 |

## 关键词

新能源汽车：electric vehicle/car、tesla、byd、nio、rivian、battery、
lithium、energy storage、renewable energy、solar

碳政策：carbon tax/pricing/emission、climate policy、decarbonization、
net zero、paris agreement、greenhouse gas

## 注意事项

* 抓取约 4018 天数据，每天下载约 13MB（压缩后筛选保存），全程约 9 小时
* 中断后用 `--resume` 继续，已完成的日期不会重复处理
* 合并后的 CSV 约 200-300 万行，建议用 pandas 而非 Excel 打开
