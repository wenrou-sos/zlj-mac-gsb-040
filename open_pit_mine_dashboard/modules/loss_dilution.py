"""损失贫化模块。

功能：
- 可视化展示矿石损失率与贫化率的变化趋势；
- 对比实际品位与地质模型预测品位的差异；
- 自动标记异常数据，并提供原因分析空间。
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (COLOR_ACTUAL, COLOR_DILUTION, COLOR_LOSS, COLOR_MODEL,
                    COLOR_WARNING, DILUTION_RATE_THRESHOLD,
                    GRADE_DIFF_THRESHOLD, LOSS_RATE_THRESHOLD)
from utils import download_button, kpi_row, style_fig

#: 平滑粒度 -> pandas 重采样频率
_FREQ = {"日": "D", "周": "W", "月": "MS"}


def _rate_trend_chart(agg: pd.DataFrame) -> go.Figure:
    """绘制损失率与贫化率趋势图，并标注预警线。"""
    fig = go.Figure()
    fig.add_scatter(x=agg["date"], y=agg["loss_rate"], name="损失率",
                    line=dict(color=COLOR_LOSS, width=2))
    fig.add_scatter(x=agg["date"], y=agg["dilution_rate"], name="贫化率",
                    line=dict(color=COLOR_DILUTION, width=2))
    fig.add_hline(y=LOSS_RATE_THRESHOLD, line_dash="dash",
                  line_color=COLOR_LOSS,
                  annotation_text=f"损失率预警 {LOSS_RATE_THRESHOLD}%")
    fig.add_hline(y=DILUTION_RATE_THRESHOLD, line_dash="dash",
                  line_color=COLOR_DILUTION,
                  annotation_text=f"贫化率预警 {DILUTION_RATE_THRESHOLD}%")
    fig.update_layout(yaxis_title="比率（%）", xaxis_title="")
    return style_fig(fig, "损失率与贫化率趋势")


def _grade_chart(agg: pd.DataFrame, anomalies: pd.DataFrame) -> go.Figure:
    """绘制实际品位与模型品位对比图，异常点以红色叉号标记。"""
    fig = go.Figure()
    fig.add_scatter(x=agg["date"], y=agg["actual_grade"], name="实际品位",
                    line=dict(color=COLOR_ACTUAL, width=2))
    fig.add_scatter(x=agg["date"], y=agg["model_grade"], name="模型品位",
                    line=dict(color=COLOR_MODEL, dash="dash"))
    if not anomalies.empty:
        fig.add_scatter(x=anomalies["date"], y=anomalies["actual_grade"],
                        mode="markers", name="异常点",
                        marker=dict(color=COLOR_WARNING, size=9,
                                    symbol="x"))
    fig.update_layout(yaxis_title="品位（%）", xaxis_title="")
    return style_fig(fig, "实际品位 vs 地质模型品位")


def render(df: pd.DataFrame) -> None:
    """渲染损失贫化模块。

    参数:
        df: 已按全局时间范围过滤后的损失贫化数据。
    """
    st.subheader("📉 损失贫化分析")
    if df.empty:
        st.warning("所选时间范围内没有损失贫化数据，请调整时间范围。")
        return

    df = df.copy()
    df["grade_diff"] = df["actual_grade"] - df["model_grade"]

    gran = st.radio("平滑粒度", list(_FREQ), index=1, horizontal=True,
                    key="ld_gran")
    cols = ["loss_rate", "dilution_rate", "actual_grade", "model_grade"]
    agg = df.set_index("date").resample(_FREQ[gran])[cols].mean().reset_index()

    anomalies = df[df["grade_diff"].abs() > GRADE_DIFF_THRESHOLD]
    kpi_row([
        ("平均损失率", f"{df['loss_rate'].mean():.2f}%", None),
        ("平均贫化率", f"{df['dilution_rate'].mean():.2f}%", None),
        ("平均品位偏差", f"{df['grade_diff'].mean():+.2f} pp", None),
        ("品位异常点", f"{len(anomalies)} 个", None),
    ])

    st.plotly_chart(_rate_trend_chart(agg), width="stretch")
    st.plotly_chart(_grade_chart(agg, anomalies), width="stretch")

    expanded = not anomalies.empty
    with st.expander(f"⚠️ 品位异常记录（|偏差| > {GRADE_DIFF_THRESHOLD} pp，"
                     f"共 {len(anomalies)} 条）", expanded=expanded):
        if anomalies.empty:
            st.success("✅ 当前时间范围内未发现品位异常。")
        else:
            show = anomalies[["date", "actual_grade", "model_grade",
                              "grade_diff"]].rename(columns={
                                  "date": "日期",
                                  "actual_grade": "实际品位(%)",
                                  "model_grade": "模型品位(%)",
                                  "grade_diff": "偏差(pp)",
                              })
            st.dataframe(show, width="stretch", hide_index=True)
            download_button(anomalies, "grade_anomalies.csv", "📥 下载异常记录")

        st.markdown("**🔎 常见原因排查清单**")
        st.markdown(
            "- 爆区边界控制偏差，围岩 / 夹石混入\n"
            "- 地质模型局部失真（断层、破碎带未准确建模）\n"
            "- 配矿计划执行偏差，高低品位矿石搭配失衡\n"
            "- 取样、制样或化验环节误差"
        )
        st.text_area("原因分析记录", key="ld_note",
                     placeholder="在此记录异常原因分析与处理措施（会话内保留）…")
