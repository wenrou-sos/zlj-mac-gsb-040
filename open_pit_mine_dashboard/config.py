"""全局配置：路径、页面信息、颜色主题与业务阈值常量。

所有阈值均可根据矿山实际管理标准调整，各功能模块在运行时
统一从本文件读取，便于集中维护。
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

PRODUCTION_CSV = DATA_DIR / "production_daily.csv"
SHOVEL_CSV = DATA_DIR / "shovel_efficiency.csv"
TRUCK_CSV = DATA_DIR / "truck_efficiency.csv"
LOSS_DILUTION_CSV = DATA_DIR / "loss_dilution.csv"
BLASTING_CSV = DATA_DIR / "blasting.csv"
COST_CSV = DATA_DIR / "cost_monthly.csv"

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
APP_TITLE = "露天矿关键生产指标分析看板"
APP_SUBTITLE = "Open-Pit Mine KPI Dashboard"
APP_ICON = "⛏️"

# ---------------------------------------------------------------------------
# 颜色主题（矿山工业风）
# ---------------------------------------------------------------------------
COLOR_ORE = "#E67E22"        # 矿石量 - 橙色
COLOR_ROCK = "#7F8C8D"       # 岩石量 - 灰色
COLOR_PLAN = "#27AE60"       # 计划量 - 绿色
COLOR_ACTUAL = "#2980B9"     # 实际值 - 蓝色
COLOR_MODEL = "#8E44AD"      # 模型值 - 紫色
COLOR_WARNING = "#E74C3C"    # 预警 - 红色
COLOR_OK = "#2ECC71"         # 达标 - 亮绿
COLOR_LOSS = "#C0392B"       # 损失率 - 深红
COLOR_DILUTION = "#D68910"   # 贫化率 - 土黄

#: 成本构成颜色映射
COST_COMPONENT_COLORS = {
    "穿孔": "#3498DB",
    "爆破": "#E74C3C",
    "铲装": "#F39C12",
    "运输": "#9B59B6",
}

#: 成本构成字段 -> 中文名称
COST_COMPONENTS = {
    "drilling_cost": "穿孔",
    "blasting_cost": "爆破",
    "loading_cost": "铲装",
    "transport_cost": "运输",
}

# ---------------------------------------------------------------------------
# 业务阈值（可按矿山实际管理标准调整）
# ---------------------------------------------------------------------------
SHOVEL_TIME_THRESHOLD = 140.0             # 电铲装车时间预警阈值（秒/车）
TRUCK_TRIPS_THRESHOLD = 9.0               # 矿车运输效率预警阈值（趟/班）
LOSS_RATE_THRESHOLD = 5.5                 # 损失率预警阈值（%）
DILUTION_RATE_THRESHOLD = 6.5             # 贫化率预警阈值（%）
GRADE_DIFF_THRESHOLD = 1.2                # 品位偏差异常阈值（百分点）
COMPLETION_TARGET = 100.0                 # 计划完成率目标（%）
OPTIMAL_CONSUMPTION_RANGE = (0.48, 0.62)  # 最佳炸药单耗区间（kg/m³）
COST_YOY_ALERT = 5.0                      # 成本同比涨幅预警线（%）
BOTTOM_N = 5                              # 低效设备标记数量
