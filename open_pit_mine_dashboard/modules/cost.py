"""成本分析模块。

功能：
- 将采矿单位成本（元/吨）拆解为穿孔、爆破、铲装、运输四项构成；
- 支持同比（与去年同期）与环比（与上一周期）分析；
- 成本异常预警与成本优化建议。
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (COLOR_ACTUAL, COLOR_WARNING, COST_COMPONENT_COLORS,
                    COST_COMPONENTS, COST_YOY_ALERT)
from utils import download_button, kpi_row, style_fig


def _structure_chart(df: pd.DataFrame) -> go.Figure:
    """绘制成本构成堆叠柱状图，并叠加总成本折线。"""
    x = df["month"].dt.strftime("%Y-%m")
    fig = go.Figure()
    for col, name in COST_COMPONENTS.items():
        fig.add_bar(x=x, y=df[col], name=name,
                    marker_color=COST_COMPONENT_COLORS[name])
    fig.add_scatter(x=x, y=df["total_cost"], name="总成本",
                    mode="lines+markers",
                    line=dict(color="#2C3E50", width=2))
    fig.update_layout(barmode="stack", yaxis_title="成本（元/吨）",
                      xaxis_title="")
    return style_fig(fig, "采矿单位成本构成（元/吨）")


def _yoy_chart(df: pd.DataFrame) -> go.Figure:
    """绘制成本同比变化柱状图，超过预警线的月份标红。"""
    x = df["month"].dt.strftime("%Y-%m")
    colors = [COLOR_WARNING if v > COST_YOY_ALERT else COLOR_ACTUAL
              for v in df["yoy_pct"].fillna(0)]
    fig = go.Figure()
    fig.add_bar(x=x, y=df["yoy_pct"].round(2), marker_color=colors,
                name="同比")
    fig.add_hline(y=COST_YOY_ALERT, line_dash="dash",
                  line_color=COLOR_WARNING,
                  annotation_text=f"预警线 {COST_YOY_ALERT}%")
    fig.update_layout(yaxis_title="同比（%）", xaxis_title="",
                      showlegend=False)
    return style_fig(fig, "单位成本同比变化", height=340)


def _mom_chart(df: pd.DataFrame) -> go.Figure:
    """绘制成本环比变化折线图。"""
    x = df["month"].dt.strftime("%Y-%m")
    fig = go.Figure()
    fig.add_scatter(x=x, y=df["mom_pct"].round(2), mode="lines+markers",
                    name="环比", line=dict(color=COLOR_ACTUAL, width=2))
    fig.add_hline(y=0, line_dash="dot", line_color="#7F8C8D")
    fig.update_layout(yaxis_title="环比（%）", xaxis_title="",
                      showlegend=False)
    return style_fig(fig, "单位成本环比变化", height=340)


def render(df: pd.DataFrame) -> None:
    """渲染成本分析模块。

    参数:
        df: 已按全局时间范围过滤后的月度成本数据。
    """
    st.subheader("💰 成本分析")
    if df.empty:
        st.warning("所选时间范围内没有成本数据，请调整时间范围。")
        return

    df = df.sort_values("month").reset_index(drop=True)
    df["total_cost"] = df[list(COST_COMPONENTS)].sum(axis=1)
    df["mom_pct"] = df["total_cost"].pct_change() * 100
    df["yoy_pct"] = df["total_cost"].pct_change(12) * 100

    latest = df.iloc[-1]
    top_col = max(COST_COMPONENTS, key=lambda c: latest[c])
    mom_delta = (f"{latest['mom_pct']:+.2f}% 环比"
                 if pd.notna(latest["mom_pct"]) else None)
    yoy_text = (f"{latest['yoy_pct']:+.2f}%"
                if pd.notna(latest["yoy_pct"]) else "—")
    kpi_row([
        ("最新单位成本", f"{latest['total_cost']:.2f} 元/吨", mom_delta),
        ("同比变化", yoy_text, None),
        ("运输成本占比",
         f"{latest['transport_cost'] / latest['total_cost'] * 100:.1f}%", None),
        ("最高成本项",
         f"{COST_COMPONENTS[top_col]} {latest[top_col]:.2f} 元/吨", None),
    ])

    st.plotly_chart(_structure_chart(df), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_yoy_chart(df), width="stretch")
    with c2:
        st.plotly_chart(_mom_chart(df), width="stretch")

    # 成本异常预警
    alerts = df[df["yoy_pct"] > COST_YOY_ALERT]
    if not alerts.empty:
        months = "、".join(alerts["month"].dt.strftime("%Y-%m"))
        st.warning(f"⚠️ 成本预警：**{months}** 单位成本同比涨幅超过 "
                   f"{COST_YOY_ALERT}%，建议重点关注运输与爆破成本。")
    else:
        st.success(f"✅ 各月成本同比涨幅均在 {COST_YOY_ALERT}% 预警线以内。")

    with st.expander("💡 成本优化建议"):
        st.markdown(
            "- **运输成本**：占比最高时优先优化运距（合理布局排土场 / "
            "破碎站）、推广新能源矿卡、优化调度减少空驶。\n"
            "- **爆破成本**：联动「爆破效果」模块，将炸药单耗控制在最佳"
            "区间，避免过量装药造成浪费。\n"
            "- **穿孔成本**：优化布孔参数与钻机走位，提高钻机台班效率。\n"
            "- **铲装成本**：联动「设备效率」模块，加强电铲预防性检修，"
            "降低故障停机损失。"
        )

    with st.expander("📋 成本明细数据"):
        show = df.rename(columns={
            "month": "月份", "total_cost": "总成本(元/吨)",
            "mom_pct": "环比(%)", "yoy_pct": "同比(%)",
            **{k: f"{v}(元/吨)" for k, v in COST_COMPONENTS.items()},
        })
        st.dataframe(show, width="stretch", hide_index=True)
        download_button(df, "cost_detail.csv")
