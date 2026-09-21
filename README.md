# ⛏️ 露天矿关键生产指标分析看板

基于 **Python + Streamlit + Plotly + Pandas** 构建的露天矿生产指标
一体化分析平台，覆盖 **产量、设备效率、损失贫化、爆破效果、采矿成本**
五大核心主题，数据为内置脚本生成的带真实业务规律的模拟数据。

## ✨ 功能特性

- **⛏️ 产量分析**：日/月/年多维度采剥总量趋势、计划产量对比、
  计划完成率可视化、时间筛选与 年→月→日 数据下钻；
- **🚛 设备效率**：电铲装车效率（秒/车）、矿车运输效率（趟/班），
  自动识别并高亮最低效 TOP5 设备，输出分级检修建议；
- **🧪 损失贫化**：损失率/贫化率趋势、实际品位 vs 地质模型品位对比、
  异常自动标记与原因/处置记录区；
- **🧨 爆破效果**：炸药单耗与块度合格率散点图、最佳单耗区间高亮、
  Pearson 相关性分析与二次拟合趋势预测；
- **📊 成本分析**：单位成本（元/吨）穿孔/爆破/铲装/运输四项拆解、
  同比与环比分析、超计划/环比突增预警与优化建议；
- **🏔️ 运行总览**：8 项核心 KPI + 关键图表，一屏掌握矿山态势；
- 响应式布局、交互式 Plotly 图表、CSV 一键导出、统一异常提示。

## 🚀 快速开始

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.data_generation        # 首次运行：生成模拟 CSV 数据
streamlit run app.py                  # 启动后浏览器访问 http://localhost:8501
```

详细步骤见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)，
操作手册见 [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)。

## 🧪 自检

```bash
python tests/smoke_test.py           # 无头方式渲染全部模块并检查异常
```

## 📁 目录结构

```text
app.py                  应用入口（侧边栏导航、全局时间筛选、异常兜底）
src/
├── data_generation.py  模拟数据生成（季节性、设备老化、异常注入等）
├── components/         overview/production/equipment/loss_dilution/
│                       blasting/cost 六大模块
└── utils/              数据加载（缓存）、图表样式、KPI 等通用组件
data/                   6 份 CSV 数据文件（脚本生成）
tests/smoke_test.py     冒烟测试
docs/                   部署说明与功能使用说明
```

## 🛠️ 技术栈

Python 3.10+ · Streamlit（Web 框架）· Plotly（交互可视化）·
Pandas / NumPy（数据处理）· ruff（PEP8 规范）。

> ⚠️ 本项目数据均为模拟数据，仅用于看板功能演示，不代表任何真实矿山。
