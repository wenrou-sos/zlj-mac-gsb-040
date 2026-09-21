"""爆破效果模块。

功能：
* 炸药单耗（kg/t）与块度合格率关系散点图，二次拟合曲线；
* 自动识别并高亮最佳炸药单耗区间（合格率达到峰值的区间）；
* Pearson 相关性分析 + 二次趋势预测（给定单耗预测合格率）；
* 大块率、岩石坚固性系数的辅助分析。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.chart_style import (
    COLOR_ACCENT,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_TEAL,
    apply_style,
)
from src.utils.ui_components import (
    download_csv_button,
    kpi_row,
    section_title,
)

# 最佳单耗区间初始参考（可由数据拟合结果动态修正）
OPTIMAL_LOW, OPTIMAL_HIGH = 0.70, 0.95
PASS_TARGET = 88.0  # 块度合格率目标线（%）


def fit_quadratic(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, float]:
    """拟合一元二次曲线 合格率 ~ 炸药单耗。

    Returns
    -------
    tuple
        (二次多项式系数, 拟合曲线上的最优单耗, 决定系数 R²)
    """
    x = df["powder_factor_kgpt"].to_numpy()
    y = df["fragment_pass_rate_pct"].to_numpy()
    coef = np.polyfit(x, y, 2)
    pred = np.polyval(coef, x)
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    # 二次曲线顶点：-b/(2a)，a<0 时为最大值点
    best_x = -coef[1] / (2 * coef[0]) if coef[0] != 0 else x.mean()
    return coef, best_x, r2


def optimal_range(df: pd.DataFrame, best_x: float) -> tuple[float, float]:
    """基于分箱统计确定合格率最高的单耗区间。

    将单耗按 0.05 kg/t 分箱，取平均合格率不超过峰值 2 个百分点
    的连续箱区间作为最佳区间。
    """
    bins = np.arange(0.45, 1.40, 0.05)
    idx = np.digitize(df["powder_factor_kgpt"], bins) - 1
    stats = (
        df.assign(bin_idx=idx).groupby("bin_idx")["fragment_pass_rate_pct"].agg(["mean", "count"])
    )
    stats = stats[stats["count"] >= 3]
    if stats.empty:
        return OPTIMAL_LOW, OPTIMAL_HIGH
    peak = stats["mean"].max()
    good = stats[stats["mean"] >= peak - 2.0]
    if good.empty:
        return OPTIMAL_LOW, OPTIMAL_HIGH
    low = float(bins[good.index.min()])
    high = float(bins[good.index.max() + 1])
    # 向拟合最优点方向做适度收束，避免区间过宽
    return round(max(low, best_x - 0.15), 2), round(min(high, best_x + 0.15), 2)


def scatter_chart(
    df: pd.DataFrame, coef: np.ndarray, best_x: float, low: float, high: float
) -> go.Figure:
    """绘制单耗 vs 合格率散点图，含拟合曲线与最佳区间高亮。"""
    fig = go.Figure()

    # 最佳单耗区间高亮带
    fig.add_vrect(
        x0=low,
        x1=high,
        fillcolor=COLOR_SUCCESS,
        opacity=0.12,
        line_width=0,
        annotation_text=f"最佳单耗区间 {low}~{high} kg/t",
        annotation_position="top left",
    )

    colors = np.where(
        (df["powder_factor_kgpt"] >= low) & (df["powder_factor_kgpt"] <= high),
        COLOR_SUCCESS,
        COLOR_PRIMARY,
    )
    sizes = np.where(df["fragment_pass_rate_pct"] >= PASS_TARGET, 10, 9)
    fig.add_trace(
        go.Scatter(
            x=df["powder_factor_kgpt"],
            y=df["fragment_pass_rate_pct"],
            mode="markers",
            name="爆破记录",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.7,
                line=dict(width=0.5, color="white"),
            ),
            text=df["blast_id"],
            customdata=df["rock_hardness_f"],
            hovertemplate="%{text}<br>单耗：%{x:.3f} kg/t"
            "<br>合格率：%{y:.1f}%<br>岩石f值：%{customdata:.1f}"
            "<extra></extra>",
        )
    )

    # 二次拟合曲线
    x_line = np.linspace(df["powder_factor_kgpt"].min(), df["powder_factor_kgpt"].max(), 100)
    y_line = np.polyval(coef, x_line)
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="二次趋势拟合",
            line=dict(color=COLOR_ACCENT, width=3),
        )
    )

    # 最优点标记
    best_y = np.polyval(coef, best_x)
    fig.add_trace(
        go.Scatter(
            x=[best_x],
            y=[best_y],
            mode="markers+text",
            name="拟合最优点",
            marker=dict(size=16, color=COLOR_DANGER, symbol="star"),
            text=[f"最优 {best_x:.3f}"],
            textposition="top center",
            hovertemplate="最优单耗：%{x:.3f} kg/t<br>预测合格率：%{y:.1f}%<extra></extra>",
        )
    )

    fig.add_hline(
        y=PASS_TARGET,
        line_dash="dot",
        line_width=1,
        line_color=COLOR_TEAL,
        annotation_text=f"合格率目标 {PASS_TARGET}%",
    )
    fig.update_layout(
        title="炸药单耗与块度合格率关系（绿色区域为最佳单耗区间）",
        xaxis_title="炸药单耗（kg/t）",
        yaxis_title="块度合格率（%）",
    )
    return apply_style(fig, 440)


def boulder_chart(df: pd.DataFrame) -> go.Figure:
    """绘制单耗与大块率关系散点图。"""
    fig = go.Figure(
        go.Scatter(
            x=df["powder_factor_kgpt"],
            y=df["boulder_rate_pct"],
            mode="markers",
            name="大块率",
            marker=dict(
                size=9,
                color=COLOR_DANGER,
                opacity=0.6,
                line=dict(width=0.5, color="white"),
            ),
            text=df["blast_id"],
            hovertemplate="%{text}<br>单耗：%{x:.3f} kg/t<br>大块率：%{y:.1f}%<extra></extra>",
        )
    )
    # 线性趋势
    coef = np.polyfit(df["powder_factor_kgpt"], df["boulder_rate_pct"], 1)
    x_line = np.linspace(df["powder_factor_kgpt"].min(), df["powder_factor_kgpt"].max(), 50)
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=np.polyval(coef, x_line),
            mode="lines",
            name="线性趋势",
            line=dict(color=COLOR_PRIMARY, width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title="炸药单耗与大块率关系",
        xaxis_title="炸药单耗（kg/t）",
        yaxis_title="大块率（%）",
    )
    return apply_style(fig, 360)


def hardness_chart(df: pd.DataFrame) -> go.Figure:
    """绘制岩石坚固性系数 f 与实际使用单耗的箱线分布图（分箱）。"""
    cuts = pd.cut(df["rock_hardness_f"], bins=np.arange(4, 20, 2), precision=0)
    grouped = df.groupby(cuts, observed=True)
    fig = go.Figure()
    for interval, group in grouped:
        fig.add_trace(
            go.Box(
                y=group["powder_factor_kgpt"],
                name=f"f={interval}",
                marker_color=COLOR_TEAL,
                boxpoints="outliers",
                showlegend=False,
                hovertemplate="%{y:.3f} kg/t<extra></extra>",
            )
        )
    fig.update_layout(
        title="不同岩石坚固性系数下的炸药单耗分布",
        yaxis_title="炸药单耗（kg/t）",
        xaxis_title="f 值区间",
    )
    return apply_style(fig, 360)


def render(df_all: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """渲染爆破效果模块主界面。"""
    section_title(
        "爆破效果分析",
        "炸药单耗与块度合格率关系、最佳单耗区间识别及趋势预测",
        "🧨",
    )

    df = df_all[(df_all["date"] >= start) & (df_all["date"] <= end)].copy()
    if len(df) < 10:
        st.warning("当前范围内爆破记录过少（少于 10 条），无法可靠拟合。")
        return

    coef, best_x, r2 = fit_quadratic(df)
    low, high = optimal_range(df, best_x)
    in_range = df[(df["powder_factor_kgpt"] >= low) & (df["powder_factor_kgpt"] <= high)]
    pearson = float(df["powder_factor_kgpt"].corr(df["fragment_pass_rate_pct"]))
    pearson_boulder = float(df["powder_factor_kgpt"].corr(df["boulder_rate_pct"]))

    kpi_row(
        [
            {"label": "爆破记录数", "value": f"{len(df)} 次"},
            {
                "label": "平均炸药单耗",
                "value": f"{df['powder_factor_kgpt'].mean():.3f} kg/t",
            },
            {
                "label": "平均块度合格率",
                "value": f"{df['fragment_pass_rate_pct'].mean():.1f}%",
            },
            {
                "label": "推荐最佳单耗",
                "value": f"{best_x:.3f} kg/t",
                "color": COLOR_SUCCESS,
                "help": f"数据拟合最优区间：{low}~{high} kg/t",
            },
            {
                "label": "拟合优度 R²",
                "value": f"{r2:.3f}",
                "help": "二次拟合曲线对合格率变异的解释程度",
            },
        ],
        columns_per_row=5,
    )

    st.plotly_chart(scatter_chart(df, coef, best_x, low, high), width="stretch")

    # ---- 相关性分析 ----
    with st.container(border=True):
        st.markdown("#### 🔗 相关性分析与趋势预测")
        c1, c2 = st.columns([1, 1])
        c1.metric(
            "单耗 ~ 合格率 Pearson 相关系数",
            f"{pearson:+.3f}",
            help="整体线性相关受倒 U 形关系影响可能偏弱，请结合二次拟合 R² 与散点图判读。",
        )
        c1.caption(
            f"单耗 ~ 大块率 线性相关系数：**{pearson_boulder:+.3f}**；"
            f"二次拟合 **R² = {r2:.3f}**，"
            "表明单耗与合格率呈显著「先升后降」的倒 U 形关系："
            "装药不足则破碎不充分、大块率高；过度装药则浪费炸药、"
            "产生飞石与震动危害。"
        )
        selected = c2.slider(
            "选择拟采用的炸药单耗（kg/t），预测块度合格率：",
            min_value=float(df["powder_factor_kgpt"].min()),
            max_value=float(df["powder_factor_kgpt"].max()),
            value=float(round(best_x, 3)),
            step=0.005,
            key="blast_predict_slider",
        )
        predicted = float(np.polyval(coef, selected))
        in_opt = low <= selected <= high
        c2.metric(
            "预测块度合格率",
            f"{predicted:.1f}%",
            delta=("处于最佳区间" if in_opt else "偏离最佳区间"),
            delta_color="off",
        )
        if in_range.shape[0] >= 3:
            c2.caption(
                f"最佳区间（{low}~{high} kg/t）内实测平均合格率："
                f"**{in_range['fragment_pass_rate_pct'].mean():.1f}%**，"
                f"平均大块率：**{in_range['boulder_rate_pct'].mean():.1f}%**。"
            )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(boulder_chart(df), width="stretch")
    with c2:
        st.plotly_chart(hardness_chart(df), width="stretch")

    with st.expander("📋 查看爆破记录明细"):
        show = df.sort_values("date", ascending=False).copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(show, width="stretch", hide_index=True)
        download_csv_button(show, "爆破效果明细.csv")
