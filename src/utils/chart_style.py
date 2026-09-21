"""Plotly 图表统一样式与配色工具。

所有模块通过本模块创建图表，保证配色、字体、边距和悬停提示
风格统一，并适配深色/浅色主题下的可读性。
"""

from __future__ import annotations

import plotly.graph_objects as go

# --------------------------------------------------------------------------
# 看板配色（矿业主题：矿岩蓝灰 + 矿石琥珀 + 矿车青绿）
# --------------------------------------------------------------------------
COLOR_PRIMARY = "#1f3a5f"  # 深蓝（主色 / 矿石）
COLOR_ACCENT = "#f59e0b"  # 琥珀（强调 / 实际值）
COLOR_SUCCESS = "#10b981"  # 青绿（达标）
COLOR_DANGER = "#ef4444"  # 红色（异常/预警）
COLOR_WARNING = "#f59e0b"  # 橙色（警告）
COLOR_WASTE = "#6b7280"  # 灰色（岩石）
COLOR_PLAN = "#94a3b8"  # 浅灰蓝（计划）
COLOR_SECONDARY = "#3b82f6"  # 蓝色（次要序列）
COLOR_PURPLE = "#8b5cf6"  # 紫色
COLOR_TEAL = "#14b8a6"  # 蓝绿

# 分类设备序列色板
PALETTE = [
    "#1f3a5f",
    "#f59e0b",
    "#10b981",
    "#3b82f6",
    "#ef4444",
    "#8b5cf6",
    "#14b8a6",
    "#f97316",
    "#64748b",
    "#0ea5e9",
    "#84cc16",
    "#e11d48",
]

# 四项成本构成配色
COST_COLORS = {
    "drilling": "#3b82f6",
    "blasting": "#f59e0b",
    "loading": "#10b981",
    "haulage": "#8b5cf6",
}

PLOT_LAYOUT = dict(
    template="plotly_white",
    font=dict(
        family="PingFang SC, Microsoft YaHei, sans-serif",
        size=13,
        color="#1f2937",
    ),
    title=dict(x=0.01, xanchor="left", font=dict(size=16)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    margin=dict(l=50, r=24, t=70, b=40),
    hoverlabel=dict(font_size=12),
)


def apply_style(fig: go.Figure, height: int = 380) -> go.Figure:
    """对图表应用统一样式（布局、边距、交互按钮）。

    Parameters
    ----------
    fig:
        待美化的 Plotly 图表对象。
    height:
        图表高度（像素）。
    """
    fig.update_layout(**PLOT_LAYOUT, height=height)
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="#eef0f4",
        zeroline=False,
        linecolor="#d1d5db",
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="#eef0f4",
        zeroline=False,
        linecolor="#d1d5db",
    )
    fig.update_traces(hoverlabel=dict(bgcolor="white"))
    return fig


def status_color(value: float, good_high: bool, good: float, warn: float) -> str:
    """根据阈值返回状态颜色。

    Parameters
    ----------
    value:
        指标值。
    good_high:
        为 ``True`` 表示数值越高越好（如完成率、趟/班）；
        为 ``False`` 表示数值越低越好（如秒/车、单位成本）。
    good, warn:
        优秀线与警告线。
    """
    if good_high:
        if value >= good:
            return COLOR_SUCCESS
        if value >= warn:
            return COLOR_WARNING
        return COLOR_DANGER
    if value <= good:
        return COLOR_SUCCESS
    if value <= warn:
        return COLOR_WARNING
    return COLOR_DANGER
