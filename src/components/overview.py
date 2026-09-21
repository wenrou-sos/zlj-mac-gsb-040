"""总览看板模块（首页）。

汇总产量、设备、损失贫化、爆破、成本五个维度的核心 KPI 与
关键图表，使管理者一屏掌握矿山整体运行情况。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.components import (
    blasting as blast_mod,
)
from src.components import (
    cost as cost_mod,
)
from src.components import (
    equipment as equip_mod,
)
from src.components import (
    loss_dilution as ld_mod,
)
from src.components import (
    production as prod_mod,
)
from src.utils.chart_style import (
    COLOR_ACCENT,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WASTE,
    apply_style,
)
from src.utils.ui_components import kpi_row, section_title


def render(data: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> None:
    """渲染总览首页。"""
    section_title("矿山运行总览", f"统计区间：{start:%Y-%m-%d} 至 {end:%Y-%m-%d}", "🏔️")

    prod = data["production"]
    shovel = data["shovel"]
    truck = data["truck"]
    loss = data["loss_dilution"]
    blast = data["blasting"]
    cost = data["cost"]

    p_df = prod[(prod["date"] >= start) & (prod["date"] <= end)]
    s_df = shovel[(shovel["date"] >= start) & (shovel["date"] <= end)]
    t_df = truck[(truck["date"] >= start) & (truck["date"] <= end)]
    l_df = loss[(loss["date"] >= start) & (loss["date"] <= end)]
    b_df = blast[(blast["date"] >= start) & (blast["date"] <= end)]
    c_df = cost_mod.build_comparison(cost)
    c_df = c_df[(c_df["month_date"] >= start) & (c_df["month_date"] <= end)]

    if p_df.empty:
        st.warning("当前时间范围内无数据。")
        return

    # ---------------- 核心 KPI ----------------
    completion = p_df["total_actual_t"].sum() / p_df["total_plan_t"].sum() * 100.0
    latest_cost = c_df.iloc[-1] if not c_df.empty else None
    kpi_row(
        [
            {
                "label": "采剥总量",
                "value": f"{p_df['total_actual_t'].sum() / 1e4:,.0f} 万吨",
            },
            {
                "label": "计划完成率",
                "value": f"{completion:.1f}%",
                "color": COLOR_SUCCESS if completion >= 100 else COLOR_ACCENT,
                "delta": f"{completion - 100:+.1f} pp",
            },
            {
                "label": "电铲平均装车周期",
                "value": f"{s_df['cycle_sec_per_truck'].mean():.1f} 秒/车"
                if not s_df.empty
                else "—",
            },
            {
                "label": "矿车平均运输效率",
                "value": f"{t_df['trips_per_shift'].mean():.2f} 趟/班" if not t_df.empty else "—",
            },
            {
                "label": "加权损失率",
                "value": f"{ld_mod._weighted_mean(l_df, 'loss_rate_pct'):.2f}%"
                if not l_df.empty
                else "—",
                "color": COLOR_DANGER
                if not l_df.empty
                and ld_mod._weighted_mean(l_df, "loss_rate_pct") > ld_mod.LOSS_THRESHOLD
                else COLOR_SUCCESS,
            },
            {
                "label": "块度合格率",
                "value": f"{b_df['fragment_pass_rate_pct'].mean():.1f}%" if not b_df.empty else "—",
            },
            {
                "label": "单位采矿成本",
                "value": f"{latest_cost['total_cost']:.2f} 元/吨"
                if latest_cost is not None
                else "—",
            },
            {
                "label": "异常爆区/成本月",
                "value": f"{int(l_df['anomaly_flag'].sum())} / {int(c_df['anomaly_flag'].sum())}",
            },
        ],
        columns_per_row=4,
    )

    # ---------------- 图表区域 ----------------
    monthly = prod_mod.aggregate(p_df, "月")
    fig_prod = go.Figure()
    fig_prod.add_trace(
        go.Bar(
            x=monthly["date"],
            y=monthly["ore_actual_t"] / 1e4,
            name="矿石量",
            marker_color=COLOR_ACCENT,
        )
    )
    fig_prod.add_trace(
        go.Bar(
            x=monthly["date"],
            y=monthly["waste_actual_t"] / 1e4,
            name="岩石量",
            marker_color=COLOR_WASTE,
        )
    )
    fig_prod.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["completion_rate"],
            name="完成率",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color=COLOR_PRIMARY, width=2.2),
        )
    )
    fig_prod.update_layout(
        title="月度采剥量与计划完成率",
        barmode="stack",
        yaxis_title="采剥量（万吨）",
        yaxis2=dict(
            title="完成率（%）",
            overlaying="y",
            side="right",
            range=[60, 125],
            showgrid=False,
        ),
    )
    fig_prod = apply_style(fig_prod, 400)

    # 成本构成
    fig_cost = cost_mod.composition_chart(c_df)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(fig_prod, width="stretch")
    with right:
        st.plotly_chart(fig_cost, width="stretch")

    # 设备效率排名（合并电铲/矿车标准化分数不太直观，分别画两个小图）
    s_sum = equip_mod.shovel_summary(s_df) if not s_df.empty else None
    t_sum = equip_mod.truck_summary(t_df) if not t_df.empty else None
    with left:
        if s_sum is not None:
            st.plotly_chart(
                equip_mod.bar_chart(
                    s_sum,
                    "avg_cycle_sec",
                    "电铲装车周期（秒/车）",
                    "秒/车",
                    False,
                ),
                width="stretch",
            )
    with right:
        if t_sum is not None:
            st.plotly_chart(
                equip_mod.bar_chart(t_sum, "avg_trips", "矿车运输效率（趟/班）", "趟/班", True),
                width="stretch",
            )

    # 爆破与损失贫化
    if len(b_df) >= 10:
        coef, best_x, _r2 = blast_mod.fit_quadratic(b_df)
        low, high = blast_mod.optimal_range(b_df, best_x)
        with left:
            st.plotly_chart(
                blast_mod.scatter_chart(b_df, coef, best_x, low, high),
                width="stretch",
            )
    if not l_df.empty:
        with right:
            st.plotly_chart(
                ld_mod.loss_dilution_chart(ld_mod.monthly_trend(l_df)),
                width="stretch",
            )

    st.info(
        "💡 提示：通过左侧菜单进入各专题模块可查看详细分析、数据下钻、异常处置记录与数据导出功能。"
    )
