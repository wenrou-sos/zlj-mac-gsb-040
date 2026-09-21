"""损失贫化模块。

功能：
* 矿石损失率、贫化率按月度趋势可视化，异常爆区高亮；
* 实际出矿品位与地质模型预测品位对比及偏差分析；
* 异常数据明细表，提供原因分析/处置措施的记录区域
  （记录保存在当前会话中）。
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.chart_style import (
    COLOR_ACCENT,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    apply_style,
)
from src.utils.ui_components import (
    download_csv_button,
    kpi_row,
    section_title,
)

# 损失率 / 贫化率异常阈值（%）
LOSS_THRESHOLD = 8.5
DILUTION_THRESHOLD = 7.5
GRADE_DEV_THRESHOLD = 0.25


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """将爆区记录聚合为月度损失率/贫化率（按出矿量加权）。"""
    records: list[dict] = []
    for period, group in df.groupby(df["date"].dt.to_period("M")):
        records.append(
            {
                "date": period.to_timestamp(),
                "loss_rate_pct": round(_weighted_mean(group, "loss_rate_pct"), 3),
                "dilution_rate_pct": round(_weighted_mean(group, "dilution_rate_pct"), 3),
                "model_grade_pct": round(_weighted_mean(group, "model_grade_pct"), 3),
                "actual_grade_pct": round(_weighted_mean(group, "actual_grade_pct"), 3),
                "anomaly_count": int(group["anomaly_flag"].sum()),
                "blocks": len(group),
            }
        )
    return pd.DataFrame(records)


def _weighted_mean(group: pd.DataFrame, col: str) -> float:
    """按出矿量加权平均。"""
    weights = group["ore_tonnage_wt"]
    if weights.sum() == 0:
        return group[col].mean()
    return float((group[col] * weights).sum() / weights.sum())


def loss_dilution_chart(monthly: pd.DataFrame) -> go.Figure:
    """绘制损失率/贫化率双折线趋势图，异常月份加标记。"""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["loss_rate_pct"],
            name="矿石损失率",
            mode="lines+markers",
            line=dict(color=COLOR_PRIMARY, width=2.5),
            hovertemplate="损失率：%{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["dilution_rate_pct"],
            name="矿石贫化率",
            mode="lines+markers",
            line=dict(color=COLOR_ACCENT, width=2.5),
            hovertemplate="贫化率：%{y:.2f}%<extra></extra>",
        )
    )
    # 异常月份红色描边标记
    abnormal = monthly[monthly["anomaly_count"] > 0]
    fig.add_trace(
        go.Scatter(
            x=abnormal["date"],
            y=abnormal["loss_rate_pct"],
            mode="markers",
            name="存在异常爆区",
            marker=dict(
                size=13,
                color="rgba(0,0,0,0)",
                line=dict(color=COLOR_DANGER, width=2.5),
            ),
            hovertemplate="%{x|%Y-%m} 异常%{customdata}个<extra></extra>",
            customdata=abnormal["anomaly_count"],
        )
    )
    fig.add_hline(
        y=LOSS_THRESHOLD,
        line_dash="dot",
        line_width=1,
        line_color=COLOR_PRIMARY,
        annotation_text=f"损失率预警 {LOSS_THRESHOLD}%",
    )
    fig.add_hline(
        y=DILUTION_THRESHOLD,
        line_dash="dot",
        line_width=1,
        line_color=COLOR_ACCENT,
        annotation_text=f"贫化率预警 {DILUTION_THRESHOLD}%",
    )
    fig.update_layout(title="矿石损失率与贫化率月度趋势", yaxis_title="比率（%）")
    return apply_style(fig, 400)


def grade_compare_chart(df: pd.DataFrame) -> go.Figure:
    """绘制模型品位 vs 实际品位对比散点图（对角线表示完全吻合）。"""
    fig = go.Figure()
    normal = df[df["anomaly_flag"] == 0]
    abnormal = df[df["anomaly_flag"] == 1]
    fig.add_trace(
        go.Scatter(
            x=normal["model_grade_pct"],
            y=normal["actual_grade_pct"],
            mode="markers",
            name="正常爆区",
            marker=dict(
                size=9,
                color=COLOR_SECONDARY,
                opacity=0.65,
                line=dict(width=0.5, color="white"),
            ),
            text=normal["block_id"],
            hovertemplate="%{text}<br>模型品位：%{x:.3f}%<br>实际品位：%{y:.3f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=abnormal["model_grade_pct"],
            y=abnormal["actual_grade_pct"],
            mode="markers",
            name="异常爆区",
            marker=dict(
                size=12,
                color=COLOR_DANGER,
                symbol="diamond",
                line=dict(width=1, color="white"),
            ),
            text=abnormal["block_id"],
            hovertemplate="%{text}<br>模型品位：%{x:.3f}%<br>实际品位：%{y:.3f}%<extra></extra>",
        )
    )
    low = min(df["model_grade_pct"].min(), df["actual_grade_pct"].min())
    high = max(df["model_grade_pct"].max(), df["actual_grade_pct"].max())
    fig.add_trace(
        go.Scatter(
            x=[low, high],
            y=[low, high],
            mode="lines",
            name="y = x 吻合线",
            line=dict(color=COLOR_SUCCESS, dash="dash", width=1.5),
        )
    )
    fig.update_layout(
        title="地质模型预测品位 vs 实际出矿品位",
        xaxis_title="模型预测品位（%）",
        yaxis_title="实际出矿品位（%）",
    )
    return apply_style(fig, 400)


def grade_deviation_chart(monthly: pd.DataFrame) -> go.Figure:
    """绘制品位偏差（实际-模型）柱状图。"""
    monthly = monthly.copy()
    monthly["dev"] = monthly["actual_grade_pct"] - monthly["model_grade_pct"]
    colors = [
        COLOR_DANGER if abs(v) > GRADE_DEV_THRESHOLD else COLOR_SECONDARY for v in monthly["dev"]
    ]
    fig = go.Figure(
        go.Bar(
            x=monthly["date"],
            y=monthly["dev"],
            marker_color=colors,
            name="品位偏差",
            hovertemplate="%{x|%Y-%m}<br>偏差：%{y:.3f} 个百分点<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color="#374151", line_width=1)
    fig.update_layout(
        title="实际品位与模型预测品位偏差（月度加权）",
        yaxis_title="品位偏差（百分点）",
    )
    return apply_style(fig, 360)


def render(df_all: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """渲染损失贫化模块主界面。"""
    section_title(
        "损失贫化分析",
        "矿石损失率/贫化率趋势、模型品位与实际品位差异及异常原因分析",
        "🧪",
    )

    df = df_all[(df_all["date"] >= start) & (df_all["date"] <= end)].copy()
    if df.empty:
        st.warning("当前时间范围内没有损失贫化数据。")
        return

    # 会话状态保存异常原因分析记录
    if "ld_notes" not in st.session_state:
        st.session_state["ld_notes"] = {}

    only_abnormal = st.checkbox("仅显示异常爆区", value=False, key="ld_only_ab")
    view_df = df[df["anomaly_flag"] == 1] if only_abnormal else df

    tonnage = df["ore_tonnage_wt"].sum()
    w_loss = _weighted_mean(df, "loss_rate_pct")
    w_dilution = _weighted_mean(df, "dilution_rate_pct")
    w_model = _weighted_mean(df, "model_grade_pct")
    w_actual = _weighted_mean(df, "actual_grade_pct")
    n_ab = int(df["anomaly_flag"].sum())
    kpi_row(
        [
            {"label": "统计出矿量", "value": f"{tonnage:,.0f} 万吨"},
            {
                "label": "加权损失率",
                "value": f"{w_loss:.2f}%",
                "color": COLOR_DANGER if w_loss > LOSS_THRESHOLD else COLOR_SUCCESS,
            },
            {
                "label": "加权贫化率",
                "value": f"{w_dilution:.2f}%",
                "color": COLOR_DANGER if w_dilution > DILUTION_THRESHOLD else COLOR_SUCCESS,
            },
            {
                "label": "模型/实际品位",
                "value": f"{w_model:.2f}% / {w_actual:.2f}%",
                "delta": f"{w_actual - w_model:+.3f} pp",
            },
            {
                "label": "异常爆区数",
                "value": f"{n_ab} 个",
                "color": COLOR_DANGER if n_ab else COLOR_SUCCESS,
                "help": f"损失率>{LOSS_THRESHOLD}% 或贫化率>{DILUTION_THRESHOLD}% 自动标记",
            },
        ],
        columns_per_row=5,
    )

    monthly = monthly_trend(df)
    st.plotly_chart(loss_dilution_chart(monthly), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(grade_compare_chart(df), width="stretch")
    with c2:
        st.plotly_chart(grade_deviation_chart(monthly), width="stretch")

    # ---- 异常明细与原因分析记录 ----
    st.markdown("#### 🚨 异常数据标记与原因分析")
    abnormal = df[df["anomaly_flag"] == 1].sort_values("date", ascending=False)
    if abnormal.empty:
        st.success("当前时间范围内未检测到损失/贫化异常爆区。")
    else:
        st.caption(
            "系统已根据阈值自动标记异常，可在「处置分析」列补充"
            "原因与整改措施，内容在本次会话内保留。"
        )
        for _, row in abnormal.iterrows():
            with st.container(border=True):
                cols = st.columns([1.4, 1.2, 1.2, 2.2, 4])
                cols[0].markdown(f"**{row['block_id']}**  \n{row['date']:%Y-%m-%d}")
                cols[1].metric("损失率", f"{row['loss_rate_pct']:.2f}%", delta=None)
                cols[2].metric("贫化率", f"{row['dilution_rate_pct']:.2f}%")
                cols[3].markdown(
                    f"模型品位：{row['model_grade_pct']:.3f}%  \n"
                    f"实际品位：{row['actual_grade_pct']:.3f}%  \n"
                    f"偏差：{row['grade_deviation_pct']:+.3f} pp"
                )
                note_key = f"ld_note_{row['block_id']}"
                default_note = st.session_state["ld_notes"].get(
                    row["block_id"], row["anomaly_reason"]
                )
                note = cols[4].text_area(
                    "处置分析",
                    value=default_note,
                    key=note_key,
                    height=68,
                    label_visibility="collapsed",
                )
                st.session_state["ld_notes"][row["block_id"]] = note

    with st.expander("📋 查看爆区明细数据"):
        show = view_df.copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(show, width="stretch", hide_index=True)
        download_csv_button(show, "损失贫化明细.csv")
