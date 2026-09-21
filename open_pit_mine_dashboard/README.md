# ⛏️ 露天矿关键生产指标分析看板

基于 **Streamlit + Plotly** 构建的露天矿生产指标可视化分析系统，覆盖
**产量、设备效率、损失贫化、爆破效果、成本** 五大核心业务模块，
为矿山生产管理提供一体化的数据决策支持。

## ✨ 功能特性

| 模块 | 核心功能 |
| ---- | -------- |
| 🏠 总览 | 核心 KPI 一览、产量与成本总体趋势 |
| ⛏️ 产量分析 | 日/月/年采剥总量趋势、计划完成率、年→月→日数据下钻 |
| 🚜 设备效率 | 电铲装车效率（秒/车）、矿车运输效率（趟/班）、低效设备 Top5 自动标记与检修建议 |
| 📉 损失贫化 | 损失率/贫化率趋势、实际 vs 模型品位对比、异常自动标记与原因分析 |
| 💥 爆破效果 | 单耗-合格率散点分析、最佳单耗区间高亮、相关性分析与合格率预测 |
| 💰 成本分析 | 单位成本四项构成拆解、同比/环比分析、成本异常预警与优化建议 |

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成模拟数据（首次运行）
python data_generator.py

# 3. 启动应用
streamlit run app.py
```

浏览器访问 <http://localhost:8501> 即可使用。

## 📁 项目结构

```
open_pit_mine_dashboard/
├── app.py                  # 应用入口（页面框架、路由、全局筛选）
├── config.py               # 全局配置（路径、颜色主题、业务阈值）
├── data_generator.py       # 模拟数据生成脚本
├── data_loader.py          # 数据加载与缓存
├── utils.py                # 通用工具（图表样式、KPI 卡片、下载等）
├── modules/                # 功能模块包
│   ├── overview.py         # 总览
│   ├── production.py       # 产量分析
│   ├── equipment.py        # 设备效率
│   ├── loss_dilution.py    # 损失贫化
│   ├── blasting.py         # 爆破效果
│   └── cost.py             # 成本分析
├── data/                   # 模拟数据 CSV（由生成脚本产出）
├── docs/
│   ├── DEPLOYMENT.md       # 部署说明文档
│   └── USER_GUIDE.md       # 功能使用说明文档
├── requirements.txt        # Python 依赖清单
└── .streamlit/config.toml  # Streamlit 主题配置
```

## 📊 数据说明

`data/` 目录下 6 个 CSV 文件由 `data_generator.py` 模拟生成
（固定随机种子，可复现），数据区间 2024-01-01 ~ 2026-09-19：

| 文件 | 内容 | 粒度 |
| ---- | ---- | ---- |
| `production_daily.csv` | 矿石量、岩石量、计划量 | 日 |
| `shovel_efficiency.csv` | 电铲装车时间、装车数 | 班次 |
| `truck_efficiency.csv` | 矿车趟数、循环时间 | 班次 |
| `loss_dilution.csv` | 损失率、贫化率、实际/模型品位 | 日 |
| `blasting.csv` | 炸药单耗、块度合格率、岩性等 | 爆区 |
| `cost_monthly.csv` | 穿孔/爆破/铲装/运输四项成本 | 月 |

## 📖 文档

- [部署说明文档](docs/DEPLOYMENT.md)
- [功能使用说明文档](docs/USER_GUIDE.md)

## 🛠️ 技术栈

- Python 3.10+
- Streamlit —— Web 应用框架
- Plotly —— 交互式数据可视化
- Pandas / NumPy —— 数据处理
