"""设备效率模块。

功能：
* 每台电铲装车效率（秒/车，越低越好）及日装车数；
* 每台矿车运输效率（趟/班，越高越好）及日运量；
* 自动识别效率最低的前 5 台设备并高亮；
* 根据指标阈值生成针对性的检修建议。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.chart_style import (
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_WARNING,
    PALETTE,
    apply_style,
)
from src.utils.ui_components import (
    download_csv_button,
    kpi_row,
    section_title,
)

# 电铲秒/车阈值（优秀 / 警告）
SHOVEL_GOOD, SHOVEL_WARN = 135.0, 150.0
# 矿车趟/班阈值（优秀 / 警告）
TRUCK_GOOD, TRUCK_WARN = 8.0, 6.8
TOP_N = 5  # 低效设备标记数量


def shovel_advice(sec: float, work_hours: float) -> str:
    """根据电铲装车周期生成检修建议。"""
    if sec >= SHOVEL_WARN:
        return (
            "建议立即安排停机检修：重点检查推压/提升钢丝绳磨损、"
            "铲斗斗齿及回转机构，并核查爆破大块率是否过高导致等挖。"
        )
    if sec >= SHOVEL_GOOD:
        return "建议加强班前点检与润滑保养，关注液压系统压力及司机操作规范，避免效率进一步下滑。"
    return "运行状态良好，保持定期点检与预防性维护即可。"


def truck_advice(trips: float, utilization: float) -> str:
    """根据矿车趟/班生成检修建议。"""
    if trips < TRUCK_WARN:
        return (
            "建议安排专项检修：检查发动机功率、轮胎磨损与制动系统，"
            "同时排查采场道路平整度及装车等待时间。"
        )
    if trips < TRUCK_GOOD:
        return "建议跟踪柴油消耗与故障记录，检查货箱粘连、举升系统，并优化与电铲的匹配调度。"
    return "运行状态良好，保持例行保养与轮胎换位计划。"


def shovel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """按设备汇总电铲平均装车周期与作业量。"""
    summary = df.groupby(["equipment_id", "equipment_name", "build_year"], as_index=False).agg(
        avg_cycle_sec=("cycle_sec_per_truck", "mean"),
        max_cycle_sec=("cycle_sec_per_truck", "max"),
        total_trucks=("trucks_loaded", "sum"),
        avg_work_hours=("work_hours", "mean"),
        availability=("work_hours", lambda s: (s > 6).mean() * 100.0),
    )
    summary["avg_cycle_sec"] = summary["avg_cycle_sec"].round(1)
    summary["max_cycle_sec"] = summary["max_cycle_sec"].round(1)
    summary["avg_work_hours"] = summary["avg_work_hours"].round(1)
    summary["availability"] = summary["availability"].round(1)
    # 秒/车越高效率越低，降序取前 5 即为最低效
    summary = summary.sort_values("avg_cycle_sec", ascending=False)
    summary["rank"] = range(1, len(summary) + 1)
    summary["bottom5"] = summary["rank"] <= TOP_N
    summary["advice"] = summary.apply(
        lambda r: shovel_advice(r["avg_cycle_sec"], r["avg_work_hours"]),
        axis=1,
    )
    return summary.reset_index(drop=True)


def truck_summary(df: pd.DataFrame) -> pd.DataFrame:
    """按设备汇总矿车平均趟/班与运量。"""
    summary = df.groupby(
        ["equipment_id", "equipment_name", "build_year", "payload_t"],
        as_index=False,
    ).agg(
        avg_trips=("trips_per_shift", "mean"),
        min_trips=("trips_per_shift", "min"),
        total_haulage_t=("daily_haulage_t", "sum"),
        avg_shifts=("shifts_worked", "mean"),
        workday_rate=("shifts_worked", lambda s: (s > 0).mean() * 100.0),
    )
    summary["avg_trips"] = summary["avg_trips"].round(2)
    summary["min_trips"] = summary["min_trips"].round(2)
    summary["avg_shifts"] = summary["avg_shifts"].round(1)
    summary["workday_rate"] = summary["workday_rate"].round(1)
    # 趟/班越低效率越低，升序取前 5
    summary = summary.sort_values("avg_trips")
    summary["rank"] = range(1, len(summary) + 1)
    summary["bottom5"] = summary["rank"] <= TOP_N
    summary["advice"] = summary.apply(
        lambda r: truck_advice(r["avg_trips"], r["avg_shifts"]), axis=1
    )
    return summary.reset_index(drop=True)


def bar_chart(
    summary: pd.DataFrame,
    value_col: str,
    title: str,
    unit: str,
    good_high: bool,
) -> go.Figure:
    """绘制设备效率排名条形图，前 5 低效设备红色高亮。"""
    ascending = good_high  # 趟/班越高越好：升序画，最差在底部
    data = summary.sort_values(value_col, ascending=ascending)
    colors = [COLOR_DANGER if b else COLOR_SUCCESS for b in data["bottom5"]]
    fig = go.Figure(
        go.Bar(
            x=data[value_col],
            y=data["equipment_name"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f} {unit}" for v in data[value_col]],
            textposition="outside",
            hovertemplate="%{y}<br>" + f"%{{x:.2f}} {unit}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=unit,
        yaxis_title="",
        yaxis=dict(categoryorder="array"),
    )
    return apply_style(fig, 420)


def daily_trend_chart(df: pd.DataFrame, value_col: str, title: str, unit: str) -> go.Figure:
    """绘制设备逐日效率折线（7 日滚动平均），用于横向对比。"""
    pivot = df.pivot_table(
        index="date",
        columns="equipment_name",
        values=value_col,
        aggfunc="mean",
    )
    pivot = pivot.rolling(7, min_periods=1).mean()
    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=pivot[col],
                name=col,
                mode="lines",
                line=dict(width=1.6, color=PALETTE[i % len(PALETTE)]),
                hovertemplate=f"{col}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}} {unit}<extra></extra>",
            )
        )
    fig.update_layout(title=title, yaxis_title=unit)
    return apply_style(fig, 420)


def render_bottom5(summary: pd.DataFrame, value_col: str, unit: str, eq_type: str) -> None:
    """渲染效率最低前 5 台设备的检修建议区域。"""
    bottom = summary[summary["bottom5"]]
    st.markdown(f"#### 🛠️ 效率最低 TOP{TOP_N} {eq_type}及检修建议")
    for _, row in bottom.iterrows():
        with st.container(border=True):
            cols = st.columns([2, 2, 6])
            cols[0].markdown(f"**{row['equipment_name']}**  \n`{row['equipment_id']}`")
            cols[1].metric(f"平均效率（{unit}）", f"{row[value_col]:.1f}")
            severity = (
                ("🔴 低效预警" if row[value_col] >= SHOVEL_WARN else "🟡 关注")
                if eq_type == "电铲"
                else ("🔴 低效预警" if row[value_col] < TRUCK_WARN else "🟡 关注")
            )
            cols[2].markdown(f"{severity}（投用年份：{row['build_year']}）")
            cols[2].caption(row["advice"])


def render(
    shovel_df: pd.DataFrame,
    truck_df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> None:
    """渲染设备效率模块主界面。"""
    section_title(
        "设备效率分析",
        "电铲装车效率（秒/车）与矿车运输效率（趟/班），自动标记最低效 5 台设备",
        "🚛",
    )

    s_df = shovel_df[(shovel_df["date"] >= start) & (shovel_df["date"] <= end)].copy()
    t_df = truck_df[(truck_df["date"] >= start) & (truck_df["date"] <= end)].copy()
    if s_df.empty or t_df.empty:
        st.warning("当前时间范围内没有设备运行数据。")
        return

    # 可选设备过滤
    eq_filter = st.checkbox("只查看指定设备", value=False, key="eq_filter_enable")
    if eq_filter:
        chosen_s = st.multiselect(
            "选择电铲",
            sorted(s_df["equipment_name"].unique()),
            default=sorted(s_df["equipment_name"].unique()),
            key="eq_filter_shovel",
        )
        chosen_t = st.multiselect(
            "选择矿车",
            sorted(t_df["equipment_name"].unique()),
            default=sorted(t_df["equipment_name"].unique()),
            key="eq_filter_truck",
        )
        s_df = s_df[s_df["equipment_name"].isin(chosen_s)]
        t_df = t_df[t_df["equipment_name"].isin(chosen_t)]

    s_sum = shovel_summary(s_df)
    t_sum = truck_summary(t_df)

    kpi_row(
        [
            {
                "label": "电铲平均装车周期",
                "value": f"{s_sum['avg_cycle_sec'].mean():.1f} 秒/车",
            },
            {
                "label": "电铲最低效设备",
                "value": s_sum.iloc[0]["equipment_name"],
                "color": COLOR_DANGER,
                "delta": f"{s_sum.iloc[0]['avg_cycle_sec']:.1f} 秒/车",
            },
            {
                "label": "矿车平均运输效率",
                "value": f"{t_sum['avg_trips'].mean():.2f} 趟/班",
            },
            {
                "label": "矿车最低效设备",
                "value": t_sum.iloc[0]["equipment_name"],
                "color": COLOR_DANGER,
                "delta": f"{t_sum.iloc[0]['avg_trips']:.2f} 趟/班",
            },
            {
                "label": "矿车累计运量",
                "value": f"{t_sum['total_haulage_t'].sum() / 1e4:,.0f} 万吨",
            },
        ],
        columns_per_row=5,
    )

    tab_s, tab_t = st.tabs(["🏗️ 电铲效率", "🚚 矿车效率"])
    with tab_s:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(
                bar_chart(
                    s_sum,
                    "avg_cycle_sec",
                    "电铲平均装车周期排名（红色为最低效 TOP5）",
                    "秒/车",
                    False,
                ),
                width="stretch",
            )
        with c2:
            st.markdown("**阈值参考**")
            st.markdown(
                f"- ≤ {SHOVEL_GOOD:.0f} 秒/车：<span style='color:{COLOR_SUCCESS}'>良好</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"- {SHOVEL_GOOD:.0f}~{SHOVEL_WARN:.0f} 秒/车："
                f"<span style='color:{COLOR_WARNING}'>关注</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"- ≥ {SHOVEL_WARN:.0f} 秒/车：<span style='color:{COLOR_DANGER}'>预警</span>",
                unsafe_allow_html=True,
            )
        st.plotly_chart(
            daily_trend_chart(
                s_df,
                "cycle_sec_per_truck",
                "电铲逐日装车周期（7 日滚动平均）",
                "秒/车",
            ),
            width="stretch",
        )
        render_bottom5(s_sum, "avg_cycle_sec", "秒/车", "电铲")
        with st.expander("📋 电铲效率汇总明细"):
            st.dataframe(
                s_sum.drop(columns=["bottom5"]),
                width="stretch",
                hide_index=True,
            )
            download_csv_button(s_sum, "电铲效率汇总.csv")

    with tab_t:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(
                bar_chart(
                    t_sum,
                    "avg_trips",
                    "矿车平均运输效率排名（红色为最低效 TOP5）",
                    "趟/班",
                    True,
                ),
                width="stretch",
            )
        with c2:
            st.markdown("**阈值参考（趟/班）**")
            st.markdown(
                f"- ≥ {TRUCK_GOOD:.1f}：<span style='color:{COLOR_SUCCESS}'>良好</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"- {TRUCK_WARN:.1f}~{TRUCK_GOOD:.1f}："
                f"<span style='color:{COLOR_WARNING}'>关注</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"- < {TRUCK_WARN:.1f}：<span style='color:{COLOR_DANGER}'>预警</span>",
                unsafe_allow_html=True,
            )
        st.plotly_chart(
            daily_trend_chart(
                t_df,
                "trips_per_shift",
                "矿车逐日运输效率（7 日滚动平均）",
                "趟/班",
            ),
            width="stretch",
        )
        render_bottom5(t_sum, "avg_trips", "趟/班", "矿车")
        with st.expander("📋 矿车效率汇总明细"):
            st.dataframe(
                t_sum.drop(columns=["bottom5"]),
                width="stretch",
                hide_index=True,
            )
            download_csv_button(t_sum, "矿车效率汇总.csv")
