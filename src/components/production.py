"""产量分析模块。

功能：
* 按日 / 月 / 年多维度展示采剥总量（矿石量 + 岩石量）趋势；
* 同步展示计划产量，计算并可视化计划完成率；
* 支持周期切换、时间范围筛选与 年→月→日 下钻；
* 矿石/岩石结构分析及原始数据导出。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.chart_style import (
    COLOR_ACCENT,
    COLOR_DANGER,
    COLOR_PLAN,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WASTE,
    apply_style,
)
from src.utils.ui_components import (
    download_csv_button,
    format_wan_tonnes,
    kpi_row,
    section_title,
)

# 周期 -> pandas 重采样规则
PERIOD_RULE = {"日": "D", "月": "MS", "年": "YS"}


def aggregate(df_daily: pd.DataFrame, period: str) -> pd.DataFrame:
    """将生产日报聚合为指定周期数据。

    产量字段求和，完成率按「实际总量 / 计划总量」重新计算，
    剥采比按区间总量重新计算。
    """
    rule = PERIOD_RULE[period]
    grouped = (
        df_daily.resample(rule, on="date")
        .agg(
            ore_plan_t=("ore_plan_t", "sum"),
            waste_plan_t=("waste_plan_t", "sum"),
            total_plan_t=("total_plan_t", "sum"),
            ore_actual_t=("ore_actual_t", "sum"),
            waste_actual_t=("waste_actual_t", "sum"),
            total_actual_t=("total_actual_t", "sum"),
        )
        .reset_index()
    )
    grouped["completion_rate"] = (
        grouped["total_actual_t"] / grouped["total_plan_t"] * 100.0
    ).round(2)
    grouped["stripping_ratio"] = (grouped["waste_actual_t"] / grouped["ore_actual_t"]).round(3)
    return grouped


def trend_chart(df: pd.DataFrame, period: str) -> go.Figure:
    """绘制采剥总量实际 vs 计划趋势图（双系列柱状+折线组合）。"""
    fig = go.Figure()
    x = df["date"]
    fig.add_trace(
        go.Bar(
            x=x,
            y=df["total_actual_t"] / 10000,
            name="实际采剥总量",
            marker_color=COLOR_PRIMARY,
            hovertemplate="%{x|%Y-%m-%d}<br>实际：%{y:.1f} 万吨<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=x,
            y=df["ore_actual_t"] / 10000,
            name="其中：矿石量",
            marker_color=COLOR_ACCENT,
            opacity=0.85,
            hovertemplate="矿石：%{y:.1f} 万吨<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=df["total_plan_t"] / 10000,
            name="计划采剥总量",
            mode="lines+markers",
            line=dict(color=COLOR_PLAN, width=2, dash="dash"),
            hovertemplate="计划：%{y:.1f} 万吨<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"采剥总量趋势（按{period}）",
        barmode="overlay",
        bargap=0.25,
        yaxis_title="采剥量（万吨）",
    )
    return apply_style(fig, 400)


def completion_chart(df: pd.DataFrame, period: str) -> go.Figure:
    """绘制计划完成率柱状图，并以 100% 为基准线着色。"""
    colors = [
        COLOR_SUCCESS if v >= 100 else COLOR_ACCENT if v >= 90 else COLOR_DANGER
        for v in df["completion_rate"]
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["completion_rate"],
            marker_color=colors,
            name="计划完成率",
            hovertemplate="%{x|%Y-%m-%d}<br>完成率：%{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(
        y=100,
        line_color=COLOR_DANGER,
        line_width=1.5,
        line_dash="dot",
        annotation_text="计划线 100%",
        annotation_position="top left",
    )
    fig.update_layout(
        title=f"计划完成率（按{period}）",
        yaxis_title="完成率（%）",
        yaxis=dict(range=[60, 125]),
    )
    return apply_style(fig, 380)


def structure_chart(df: pd.DataFrame, period: str) -> go.Figure:
    """绘制矿石/岩石结构占比堆叠柱状图。"""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["ore_actual_t"] / 10000,
            name="矿石量",
            marker_color=COLOR_ACCENT,
            hovertemplate="矿石：%{y:.1f} 万吨<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["waste_actual_t"] / 10000,
            name="岩石量",
            marker_color=COLOR_WASTE,
            hovertemplate="岩石：%{y:.1f} 万吨<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"矿石 / 岩石采剥结构（按{period}）",
        barmode="stack",
        yaxis_title="采剥量（万吨）",
    )
    return apply_style(fig, 380)


def render_drilldown(df_daily: pd.DataFrame, period: str) -> None:
    """渲染数据下钻区域：选择年/月后查看下级周期明细。"""
    with st.expander("🔎 数据下钻（年 → 月 → 日）", expanded=False):
        if period == "年":
            years = sorted(df_daily["date"].dt.year.unique())
            year = st.selectbox("选择年份", years, key="prod_drill_year")
            monthly = aggregate(df_daily[df_daily["date"].dt.year == year], "月")
            st.caption(f"{year} 年月度明细")
            st.plotly_chart(trend_chart(monthly, "月"), width="stretch")
            month = st.selectbox(
                "继续下钻：选择月份",
                monthly["date"].dt.strftime("%Y-%m"),
                key="prod_drill_month",
            )
            mask = df_daily["date"].dt.strftime("%Y-%m") == month
            daily = df_daily[mask]
            st.caption(f"{month} 日度明细")
            st.plotly_chart(trend_chart(daily, "日"), width="stretch")
        elif period == "月":
            months = sorted(df_daily["date"].dt.strftime("%Y-%m").unique())
            month = st.selectbox("选择月份", months, key="prod_drill_m2d")
            daily = df_daily[df_daily["date"].dt.strftime("%Y-%m") == month]
            st.caption(f"{month} 日度明细")
            st.plotly_chart(trend_chart(daily, "日"), width="stretch")
        else:
            st.info("当前已是「日」粒度，无需继续下钻。")


def render(prod_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """渲染产量分析模块主界面。

    Parameters
    ----------
    prod_df:
        生产日报全量数据。
    start, end:
        全局时间筛选范围。
    """
    section_title("产量分析", "采剥总量趋势、计划完成率与矿岩结构分析", "⛏️")

    # 全局时间过滤
    mask = (prod_df["date"] >= start) & (prod_df["date"] <= end)
    df_daily = prod_df.loc[mask].copy()
    if df_daily.empty:
        st.warning("当前时间范围内没有产量数据，请调整筛选条件。")
        return

    # 周期选择
    period = st.radio(
        "统计周期",
        ["日", "月", "年"],
        horizontal=True,
        key="prod_period",
        help="切换日/月/年聚合粒度；月、年会对区间内数据自动汇总。",
    )
    df = aggregate(df_daily, period)

    # ---- KPI 指标 ----
    total_actual = df["total_actual_t"].sum()
    total_plan = df["total_plan_t"].sum()
    rate = total_actual / total_plan * 100.0 if total_plan else 0.0
    ore_total = df["ore_actual_t"].sum()
    waste_total = df["waste_actual_t"].sum()
    avg_ratio = waste_total / ore_total if ore_total else 0.0
    best = df.loc[df["completion_rate"].idxmax()]
    kpi_row(
        [
            {
                "label": "实际采剥总量",
                "value": format_wan_tonnes(total_actual),
                "help": "统计周期内矿石量与岩石量之和",
            },
            {"label": "计划采剥总量", "value": format_wan_tonnes(total_plan)},
            {
                "label": "累计计划完成率",
                "value": f"{rate:.1f}%",
                "delta": f"{rate - 100:+.1f} pp",
                "color": COLOR_SUCCESS if rate >= 100 else COLOR_ACCENT,
            },
            {
                "label": "综合剥采比",
                "value": f"{avg_ratio:.2f} t/t",
                "help": "岩石量 / 矿石量",
            },
            {
                "label": f"最高完成{period}",
                "value": best["date"].strftime("%Y-%m" if period != "日" else "%Y-%m-%d"),
                "delta": f"{best['completion_rate']:.1f}%",
            },
        ],
        columns_per_row=5,
    )

    tab_trend, tab_rate, tab_struct = st.tabs(["📈 总量趋势", "✅ 计划完成率", "🪨 矿岩结构"])
    with tab_trend:
        st.plotly_chart(trend_chart(df, period), width="stretch")
    with tab_rate:
        st.plotly_chart(completion_chart(df, period), width="stretch")
        under = df[df["completion_rate"] < 90.0]
        if not under.empty:
            st.warning(
                f"共有 {len(under)} 个{period}周期完成率低于 90%，"
                "建议结合设备效率与天气记录排查原因。"
            )
    with tab_struct:
        st.plotly_chart(structure_chart(df, period), width="stretch")

    render_drilldown(df_daily, period)

    # 明细数据与导出
    with st.expander("📋 查看明细数据"):
        show = df.copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(show, width="stretch", hide_index=True)
        download_csv_button(show, f"产量分析_{period}明细.csv")
