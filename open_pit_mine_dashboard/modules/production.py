"""产量分析模块。

功能：
- 按日 / 月 / 年多维度展示采剥总量（矿石量 + 岩石量）趋势；
- 同步展示计划产量并计算计划完成率；
- 支持「年 -> 月 -> 日」的数据下钻分析。
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (COLOR_OK, COLOR_ORE, COLOR_PLAN, COLOR_ROCK,
                    COLOR_WARNING, COMPLETION_TARGET)
from utils import download_button, kpi_row, style_fig

#: 统计粒度 -> pandas 重采样频率
_FREQ_MAP = {"日": "D", "月": "MS", "年": "YS"}
#: 统计粒度 -> 横轴日期格式
_PERIOD_FMT = {"日": "%Y-%m-%d", "月": "%Y-%m", "年": "%Y"}


def _aggregate(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """按指定频率聚合产量与计划量，并计算计划完成率。

    参数:
        df: 每日产量数据。
        freq: pandas 重采样频率（D / MS / YS）。

    返回:
        聚合后的数据框，含 ``completion_rate`` 列（%）。
    """
    cols = ["ore_volume", "rock_volume", "total_volume", "plan_volume"]
    agg = df.set_index("date").resample(freq)[cols].sum().reset_index()
    agg["completion_rate"] = agg["total_volume"] / agg["plan_volume"] * 100
    return agg


def _trend_chart(agg: pd.DataFrame, gran: str) -> go.Figure:
    """绘制采剥总量堆叠柱状图，并叠加计划量虚线。"""
    x = agg["date"].dt.strftime(_PERIOD_FMT[gran])
    fig = go.Figure()
    fig.add_bar(x=x, y=agg["ore_volume"], name="矿石量",
                marker_color=COLOR_ORE)
    fig.add_bar(x=x, y=agg["rock_volume"], name="岩石量",
                marker_color=COLOR_ROCK)
    fig.add_scatter(x=x, y=agg["plan_volume"], name="计划量", mode="lines",
                    line=dict(color=COLOR_PLAN, dash="dash", width=2))
    fig.update_layout(barmode="stack", yaxis_title="产量（吨）",
                      xaxis_title="")
    return style_fig(fig, "采剥总量 vs 计划量")


def _completion_chart(agg: pd.DataFrame, gran: str) -> go.Figure:
    """绘制计划完成率柱状图，达标绿色、未达标红色。"""
    x = agg["date"].dt.strftime(_PERIOD_FMT[gran])
    colors = [COLOR_OK if r >= COMPLETION_TARGET else COLOR_WARNING
              for r in agg["completion_rate"]]
    fig = go.Figure()
    fig.add_bar(x=x, y=agg["completion_rate"].round(1), name="完成率",
                marker_color=colors)
    fig.add_hline(y=COMPLETION_TARGET, line_dash="dash",
                  line_color=COLOR_PLAN, annotation_text="目标 100%")
    y_min = max(0, agg["completion_rate"].min() - 15)
    y_max = max(120, agg["completion_rate"].max() + 10)
    fig.update_layout(yaxis_title="完成率（%）", xaxis_title="",
                      yaxis_range=[y_min, y_max], showlegend=False)
    return style_fig(fig, "计划完成率", height=340)


def _drill_down(df: pd.DataFrame) -> None:
    """数据下钻：选择年份与月份，逐级查看月度 / 每日明细。"""
    years = sorted(df["date"].dt.year.unique(), reverse=True)
    c1, c2 = st.columns(2)
    year = c1.selectbox("选择年份", years, key="drill_year")
    year_df = df[df["date"].dt.year == year]

    months = sorted(year_df["date"].dt.month.unique())
    month_sel = c2.selectbox("选择月份", ["全年"] + [f"{m}月" for m in months],
                             key="drill_month")
    if month_sel == "全年":
        agg, gran = _aggregate(year_df, "MS"), "月"
    else:
        month = int(month_sel.replace("月", ""))
        agg = _aggregate(year_df[year_df["date"].dt.month == month], "D")
        gran = "日"
    st.plotly_chart(_trend_chart(agg, gran), width="stretch")
    st.plotly_chart(_completion_chart(agg, gran), width="stretch")


def render(df: pd.DataFrame) -> None:
    """渲染产量分析模块。

    参数:
        df: 已按全局时间范围过滤后的每日产量数据。
    """
    st.subheader("⛏️ 产量分析")
    if df.empty:
        st.warning("所选时间范围内没有产量数据，请调整时间范围。")
        return

    gran = st.radio("统计粒度", list(_FREQ_MAP), index=1,
                    horizontal=True, key="prod_gran")
    agg = _aggregate(df, _FREQ_MAP[gran])
    if gran == "日" and len(agg) > 200:
        st.caption("💡 当前数据点较多，建议在侧边栏缩小时间范围以获得更清晰的视图。")

    total = agg["total_volume"].sum()
    ore = agg["ore_volume"].sum()
    plan = agg["plan_volume"].sum()
    strip_ratio = agg["rock_volume"].sum() / max(ore, 1)
    completion = total / plan * 100 if plan else 0.0
    kpi_row([
        ("采剥总量", f"{total / 1e4:,.1f} 万吨", None),
        ("矿石量", f"{ore / 1e4:,.1f} 万吨", None),
        ("剥采比", f"{strip_ratio:.2f}", None),
        ("计划完成率", f"{completion:.1f}%", f"{completion - 100:+.1f} pp"),
    ])

    st.plotly_chart(_trend_chart(agg, gran), width="stretch")
    st.plotly_chart(_completion_chart(agg, gran), width="stretch")

    with st.expander("🔍 数据下钻（年 → 月 → 日）"):
        _drill_down(df)

    with st.expander("📋 明细数据"):
        st.dataframe(agg, width="stretch", hide_index=True)
        download_button(agg, "production_detail.csv")
