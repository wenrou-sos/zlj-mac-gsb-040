"""总览模块：核心 KPI 一览与总体趋势速览。"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (COLOR_ORE, COLOR_PLAN, COLOR_ROCK, COST_COMPONENTS)
from utils import filter_by_date, kpi_row, style_fig


def _production_mini(prod: pd.DataFrame) -> go.Figure:
    """绘制月度采剥总量迷你趋势图。"""
    cols = ["ore_volume", "rock_volume", "plan_volume"]
    agg = prod.set_index("date").resample("MS")[cols].sum().reset_index()
    x = agg["date"].dt.strftime("%Y-%m")
    fig = go.Figure()
    fig.add_bar(x=x, y=agg["ore_volume"], name="矿石量",
                marker_color=COLOR_ORE)
    fig.add_bar(x=x, y=agg["rock_volume"], name="岩石量",
                marker_color=COLOR_ROCK)
    fig.add_scatter(x=x, y=agg["plan_volume"], name="计划量", mode="lines",
                    line=dict(color=COLOR_PLAN, dash="dash", width=2))
    fig.update_layout(barmode="stack", yaxis_title="产量（吨）",
                      xaxis_title="")
    return style_fig(fig, "月度采剥总量", height=360)


def _cost_mini(cost: pd.DataFrame) -> go.Figure:
    """绘制单位成本迷你趋势图。"""
    total = cost[list(COST_COMPONENTS)].sum(axis=1)
    x = cost["month"].dt.strftime("%Y-%m")
    fig = go.Figure()
    fig.add_scatter(x=x, y=total, mode="lines+markers", name="单位成本",
                    line=dict(color="#2C3E50", width=2))
    fig.update_layout(yaxis_title="成本（元/吨）", xaxis_title="",
                      showlegend=False)
    return style_fig(fig, "月度单位成本", height=360)


def render(data: dict, date_range) -> None:
    """渲染总览模块。

    参数:
        data: 全部数据集字典。
        date_range: 全局日期范围筛选。
    """
    st.subheader("🏠 生产指标总览")

    prod = filter_by_date(data["production"], date_range)
    ld = filter_by_date(data["loss_dilution"], date_range)
    shovel = filter_by_date(data["shovel"], date_range)
    truck = filter_by_date(data["truck"], date_range)
    cost = filter_by_date(data["cost"], date_range, col="month")

    if prod.empty:
        st.warning("所选时间范围内没有数据，请调整时间范围。")
        return

    total = prod["total_volume"].sum()
    plan = prod["plan_volume"].sum()
    completion = total / plan * 100 if plan else 0.0
    kpi_row([
        ("采剥总量", f"{total / 1e4:,.1f} 万吨", None),
        ("计划完成率", f"{completion:.1f}%", f"{completion - 100:+.1f} pp"),
        ("平均损失率",
         f"{ld['loss_rate'].mean():.2f}%" if not ld.empty else "—", None),
        ("平均贫化率",
         f"{ld['dilution_rate'].mean():.2f}%" if not ld.empty else "—", None),
    ])

    if not shovel.empty:
        shovel_avg = ((shovel["avg_loading_time_sec"]
                       * shovel["trucks_loaded"]).sum()
                      / shovel["trucks_loaded"].sum())
        shovel_text = f"{shovel_avg:.1f} 秒/车"
    else:
        shovel_text = "—"
    truck_text = f"{truck['trips'].mean():.1f} 趟/班" if not truck.empty else "—"
    if not cost.empty:
        latest_cost = cost.iloc[-1][list(COST_COMPONENTS)].sum()
        cost_text = f"{latest_cost:.2f} 元/吨"
    else:
        cost_text = "—"
    grade_text = (f"{(ld['actual_grade'] - ld['model_grade']).mean():+.2f} pp"
                  if not ld.empty else "—")
    kpi_row([
        ("电铲平均装车时间", shovel_text, None),
        ("矿车平均趟数", truck_text, None),
        ("最新单位成本", cost_text, None),
        ("品位平均偏差", grade_text, None),
    ])

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_production_mini(prod), width="stretch")
    with c2:
        if cost.empty:
            st.info("所选时间范围内没有成本数据。")
        else:
            st.plotly_chart(_cost_mini(cost), width="stretch")

    st.caption("💡 使用左侧边栏切换功能模块、调整分析时间范围。")
