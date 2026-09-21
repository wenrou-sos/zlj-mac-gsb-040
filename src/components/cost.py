"""成本分析模块。

功能：
* 采矿单位成本（元/吨）拆解为穿孔、爆破、铲装、运输四项；
* 堆叠面积/柱状图展示成本构成演变；
* 同比（与去年同期）与环比（与上一周期）分析；
* 超计划/环比突增异常预警及成本优化建议。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.chart_style import (
    COLOR_ACCENT,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COST_COLORS,
    apply_style,
)
from src.utils.ui_components import (
    download_csv_button,
    kpi_row,
    section_title,
)

COST_ITEMS = [
    ("drilling_cost", "穿孔", COST_COLORS["drilling"]),
    ("blasting_cost", "爆破", COST_COLORS["blasting"]),
    ("loading_cost", "铲装", COST_COLORS["loading"]),
    ("haulage_cost", "运输", COST_COLORS["haulage"]),
]

# 环比突增预警阈值（元/吨）
MOM_ALERT = 0.5
# 环比突增预警阈值（百分比）
MOM_PCT_ALERT = 3.0
# 超计划比例预警阈值
PLAN_OVER_RATIO = 0.05


def build_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """计算环比、同比偏移及成本构成占比。"""
    out = df.sort_values("month_date").reset_index(drop=True).copy()
    # 环比（shift(1)）与同比（shift(12)）
    out["mom_delta"] = (out["total_cost"] - out["total_cost"].shift(1)).round(2)
    out["mom_pct"] = (out["total_cost"].pct_change(1) * 100.0).round(1)
    out["yoy_delta"] = (out["total_cost"] - out["total_cost"].shift(12)).round(2)
    out["yoy_pct"] = (out["total_cost"].pct_change(12) * 100.0).round(1)
    for col, _, _ in COST_ITEMS:
        out[col + "_ratio"] = (out[col] / out["total_cost"] * 100).round(1)
    out["over_plan_pct"] = (
        (out["total_cost"] - out["plan_total_cost"]) / out["plan_total_cost"] * 100.0
    ).round(1)
    return out


def composition_chart(df: pd.DataFrame) -> go.Figure:
    """绘制四项成本构成堆叠面积图。"""
    fig = go.Figure()
    for col, label, color in COST_ITEMS:
        fig.add_trace(
            go.Scatter(
                x=df["month"],
                y=df[col],
                name=label,
                mode="lines",
                stackgroup="cost",
                line=dict(width=0.5, color=color),
                fillcolor=color,
                hovertemplate=f"{label}：%{{y:.2f}} 元/吨<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["total_cost"],
            name="合计单位成本",
            mode="lines",
            line=dict(color="#111827", width=2.2),
            hovertemplate="合计：%{y:.2f} 元/吨<extra></extra>",
        )
    )
    fig.update_layout(
        title="采矿单位成本构成趋势（元/吨）",
        yaxis_title="单位成本（元/吨）",
        hovermode="x unified",
    )
    return apply_style(fig, 420)


def compare_chart(df: pd.DataFrame, mode: str) -> go.Figure:
    """绘制同比/环比变化柱状图。

    Parameters
    ----------
    mode:
        ``"mom"`` 环比（与上月），``"yoy"`` 同比（与去年同月）。
    """
    col, name = (
        ("mom_pct", "环比（较上月）") if mode == "mom" else ("yoy_pct", "同比（较去年同月）")
    )
    data = df.dropna(subset=[col])
    threshold = MOM_PCT_ALERT if mode == "mom" else 0.0
    colors = [
        COLOR_DANGER if v > threshold else COLOR_SUCCESS if v < 0 else COLOR_ACCENT
        for v in data[col]
    ]
    fig = go.Figure(
        go.Bar(
            x=data["month"],
            y=data[col],
            marker_color=colors,
            name=name,
            hovertemplate="%{x}<br>" + name + "：%{y:+.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color="#374151", line_width=1)
    fig.update_layout(title=f"单位成本{name}变化率", yaxis_title="变化率（%）")
    return apply_style(fig, 380)


def item_yoy_chart(df_full: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> go.Figure:
    """绘制区间末 12 个月四项成本同比对比分组柱状图。

    Parameters
    ----------
    df_full:
        经过 :func:`build_comparison` 处理的**全量**月度数据
        （需含去年同期才能计算同比）。
    start, end:
        当前筛选区间。
    """
    plot_df = df_full.copy()
    yoy_cols: list[str] = []
    for col, _, _ in COST_ITEMS:
        yoy_col = col.replace("_cost", "_yoy")
        plot_df[yoy_col] = (plot_df[col].pct_change(12) * 100.0).round(1)
        yoy_cols.append(yoy_col)
    recent = plot_df[(plot_df["month_date"] >= start) & (plot_df["month_date"] <= end)].tail(12)

    fig = go.Figure()
    for (_col, label, color), yoy_col in zip(COST_ITEMS, yoy_cols, strict=True):
        fig.add_trace(
            go.Bar(
                x=recent["month"],
                y=recent[yoy_col],
                name=label,
                marker_color=color,
                hovertemplate=f"{label}同比：%{{y:+.1f}}%<extra></extra>",
            )
        )
    fig.add_hline(y=0, line_color="#374151", line_width=1)
    fig.update_layout(
        title="近 12 个月各项成本同比变化率",
        yaxis_title="同比变化率（%）",
        barmode="group",
    )
    return apply_style(fig, 380)


def cost_pie_chart(latest: pd.Series) -> go.Figure:
    """绘制最新月份成本构成饼图。"""
    values = [latest[col] for col, _, _ in COST_ITEMS]
    labels = [label for _, label, _ in COST_ITEMS]
    colors = [color for _, _, color in COST_ITEMS]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="white", width=2)),
            textinfo="label+percent",
            hovertemplate="%{label}：%{value:.2f} 元/吨（%{percent}）<extra></extra>",
        )
    )
    fig.update_layout(title=f"{latest['month']} 成本构成")
    return apply_style(fig, 360)


def optimization_advice(row: pd.Series) -> list[str]:
    """根据最新月份各成本项及环比情况生成优化建议。"""
    advice: list[str] = []
    ratios = {label: row[col + "_ratio"] for col, label, _ in COST_ITEMS}
    if ratios.get("运输", 0) > 42:
        advice.append(
            "💰 **运输成本占比偏高（>42%）**：优化采场道路"
            "（洒水降尘、路面维护）、缩短运距、推进陡帮开采，"
            "并核查柴油单耗与轮胎寿命。"
        )
    if row["drilling_cost"] > 3.2:
        advice.append(
            "🔩 **穿孔成本偏高**：优化孔网参数与钻头选型，推行高精度钻孔（GPS 定位），减少废孔率。"
        )
    if row["blasting_cost"] > 4.6:
        advice.append(
            "🧨 **爆破成本偏高**：结合「爆破效果」模块推荐的"
            "最佳单耗区间优化装药，推广多孔粒状铵油炸药"
            "混装车，降低二次破碎量。"
        )
    if row["loading_cost"] > 3.6:
        advice.append(
            "🏗️ **铲装成本偏高**：结合「设备效率」模块排查"
            "低效电铲，提高铲斗满斗率，减少电铲待车时间。"
        )
    if row["over_plan_pct"] > PLAN_OVER_RATIO * 100:
        advice.append(
            f"📈 **超计划 {row['over_plan_pct']:.1f}%**："
            "建议召开成本分析会，将超支科目纳入月度考核。"
        )
    if not advice:
        advice.append(
            "✅ 当前各项成本均处于受控区间，建议维持现有"
            "管控措施并持续跟踪油耗、配件等主要驱动因素。"
        )
    return advice


def render(df_all: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """渲染成本分析模块主界面。

    成本为月度数据，时间筛选按月份首日落在区间内进行。
    """
    section_title(
        "成本分析",
        "采矿单位成本四项构成拆解、同比/环比分析、异常预警与优化建议",
        "📊",
    )

    df = build_comparison(df_all)
    mask = (df["month_date"] >= start) & (df["month_date"] <= end)
    df = df.loc[mask].reset_index(drop=True)
    if df.empty:
        st.warning("当前时间范围内没有成本数据。")
        return

    latest = df.iloc[-1]
    yoy_row = df[
        df["month"]
        == (pd.Timestamp(latest["month_date"]) - pd.DateOffset(years=1)).strftime("%Y-%m")
    ]
    yoy_value = yoy_row.iloc[0]["total_cost"] if not yoy_row.empty else None

    kpi_row(
        [
            {
                "label": f"{latest['month']} 单位成本",
                "value": f"{latest['total_cost']:.2f} 元/吨",
            },
            {
                "label": "环比变化",
                "value": (
                    f"{latest['mom_delta']:+.2f} 元/吨" if pd.notna(latest["mom_delta"]) else "—"
                ),
                "delta": (f"{latest['mom_pct']:+.1f}%" if pd.notna(latest["mom_pct"]) else None),
                "color": COLOR_DANGER
                if pd.notna(latest["mom_delta"]) and latest["mom_delta"] > MOM_ALERT
                else COLOR_SUCCESS,
            },
            {
                "label": "同比变化",
                "value": (
                    f"{latest['yoy_delta']:+.2f} 元/吨" if pd.notna(latest["yoy_delta"]) else "—"
                ),
                "delta": (f"{latest['yoy_pct']:+.1f}%" if pd.notna(latest["yoy_pct"]) else None),
                "color": COLOR_DANGER
                if pd.notna(latest["yoy_delta"]) and latest["yoy_delta"] > 0
                else COLOR_SUCCESS,
            },
            {
                "label": "计划单位成本",
                "value": f"{latest['plan_total_cost']:.2f} 元/吨",
            },
            {
                "label": "超计划幅度",
                "value": f"{latest['over_plan_pct']:+.1f}%",
                "color": COLOR_DANGER
                if latest["over_plan_pct"] > PLAN_OVER_RATIO * 100
                else COLOR_SUCCESS,
            },
        ],
        columns_per_row=5,
    )

    st.plotly_chart(composition_chart(df), width="stretch")

    tab_mom, tab_yoy, tab_pie = st.tabs(["↕️ 环比分析", "📅 同比分析", "🥧 构成占比"])
    with tab_mom:
        st.plotly_chart(compare_chart(df, "mom"), width="stretch")
    with tab_yoy:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(compare_chart(df, "yoy"), width="stretch")
        with c2:
            st.plotly_chart(
                item_yoy_chart(build_comparison(df_all), start, end),
                width="stretch",
            )
    with tab_pie:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(cost_pie_chart(latest), width="stretch")
        if yoy_value:
            with c2:
                st.plotly_chart(
                    cost_pie_chart(
                        pd.Series(
                            {
                                "month": (
                                    pd.Timestamp(latest["month_date"]) - pd.DateOffset(years=1)
                                ).strftime("%Y-%m"),
                                **{c: yoy_row.iloc[0][c] for c, _, _ in COST_ITEMS},
                            }
                        )
                    ),
                    width="stretch",
                )

    # ---- 异常预警 ----
    st.markdown("#### 🚨 成本异常预警")
    alerts = df[
        (df["mom_delta"] > MOM_ALERT)
        | (df["over_plan_pct"] > PLAN_OVER_RATIO * 100)
        | (df["anomaly_flag"] == 1)
    ].sort_values("month", ascending=False)
    if alerts.empty:
        st.success("当前时间范围内未触发成本异常预警。")
    else:
        st.caption(
            f"预警规则：环比上升 > {MOM_ALERT} 元/吨，或超计划 > {PLAN_OVER_RATIO * 100:.0f}%。"
        )
        show_alerts = alerts[
            [
                "month",
                "total_cost",
                "mom_delta",
                "mom_pct",
                "yoy_pct",
                "over_plan_pct",
                "anomaly_reason",
            ]
        ].head(12)
        show_alerts.columns = [
            "月份",
            "单位成本(元/吨)",
            "环比变动",
            "环比%",
            "同比%",
            "超计划%",
            "记录原因",
        ]
        st.dataframe(show_alerts, width="stretch", hide_index=True)

    # ---- 优化建议 ----
    st.markdown("#### 💡 成本优化建议")
    for tip in optimization_advice(latest):
        st.markdown(f"- {tip}")

    with st.expander("📋 查看成本月度明细"):
        st.dataframe(df, width="stretch", hide_index=True)
        download_csv_button(df, "成本分析明细.csv")
