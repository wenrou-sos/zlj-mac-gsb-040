"""爆破效果模块。

功能：
- 炸药单耗与块度合格率关系散点分析；
- 高亮显示最佳炸药单耗区间；
- 相关性分析（Pearson 系数 + 二次拟合 R²）与合格率预测。
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import COLOR_OK, OPTIMAL_CONSUMPTION_RANGE
from utils import download_button, kpi_row, style_fig


def _fit_quadratic(x: np.ndarray, y: np.ndarray):
    """对单耗-合格率关系做二次多项式拟合。

    返回:
        ``(拟合多项式, Pearson 相关系数, 决定系数 R²)`` 三元组。
    """
    poly = np.poly1d(np.polyfit(x, y, 2))
    pearson = float(np.corrcoef(x, y)[0, 1])
    ss_res = float(((y - poly(x)) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return poly, pearson, r2


def _scatter_chart(d: pd.DataFrame, poly) -> go.Figure:
    """绘制单耗-合格率散点图，叠加拟合曲线并高亮最佳区间。"""
    lo, hi = OPTIMAL_CONSUMPTION_RANGE
    fig = px.scatter(
        d, x="explosive_consumption", y="fragmentation_rate",
        color="rock_type", size="rock_volume_m3",
        hover_data=["blast_id", "date", "bench"],
        labels={
            "explosive_consumption": "炸药单耗（kg/m³）",
            "fragmentation_rate": "块度合格率（%）",
            "rock_type": "岩性",
            "rock_volume_m3": "爆破量(m³)",
        })
    xs = np.linspace(d["explosive_consumption"].min(),
                     d["explosive_consumption"].max(), 200)
    fig.add_trace(go.Scatter(x=xs, y=poly(xs), mode="lines",
                             name="二次拟合曲线",
                             line=dict(color="#2C3E50", dash="dash")))
    fig.add_vrect(x0=lo, x1=hi, fillcolor=COLOR_OK, opacity=0.12,
                  line_width=0, annotation_text="最佳单耗区间",
                  annotation_position="top left")
    fig = style_fig(fig, "炸药单耗 vs 块度合格率", height=520)
    fig.update_layout(hovermode="closest")
    return fig


def render(df: pd.DataFrame) -> None:
    """渲染爆破效果模块。

    参数:
        df: 已按全局时间范围过滤后的爆破数据。
    """
    st.subheader("💥 爆破效果分析")
    if df.empty:
        st.warning("所选时间范围内没有爆破数据，请调整时间范围。")
        return
    if len(df) < 10:
        st.warning("数据量过少（< 10 条），无法进行分析，请扩大时间范围。")
        return

    rock_types = sorted(df["rock_type"].unique())
    sel_types = st.multiselect("岩性筛选", rock_types, default=rock_types,
                               key="blast_types")
    d = df[df["rock_type"].isin(sel_types)]
    if len(d) < 10:
        st.warning("筛选后数据量过少，请放宽筛选条件。")
        return

    x = d["explosive_consumption"].to_numpy()
    y = d["fragmentation_rate"].to_numpy()
    poly, pearson, r2 = _fit_quadratic(x, y)

    lo, hi = OPTIMAL_CONSUMPTION_RANGE
    in_zone = d[d["explosive_consumption"].between(lo, hi)]
    out_zone = d[~d["explosive_consumption"].between(lo, hi)]

    kpi_row([
        ("爆破次数", f"{len(d)} 次", None),
        ("平均单耗", f"{x.mean():.3f} kg/m³", None),
        ("平均合格率", f"{y.mean():.1f}%", None),
        ("Pearson 相关系数", f"{pearson:.2f}", None),
    ])

    st.plotly_chart(_scatter_chart(d, poly), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 📊 相关性分析")
        st.write(f"- Pearson 线性相关系数：**{pearson:.3f}**")
        st.write(f"- 二次拟合决定系数 R²：**{r2:.3f}**")
        in_mean = in_zone["fragmentation_rate"].mean()
        out_mean = out_zone["fragmentation_rate"].mean()
        st.write(f"- 区间内平均合格率：**{in_mean:.1f}%**（{len(in_zone)} 次）")
        st.write(f"- 区间外平均合格率：**{out_mean:.1f}%**（{len(out_zone)} 次）")
        st.caption(
            "💡 单耗与合格率呈非线性关系：单耗过低导致大块率升高，"
            "过高则产生过粉碎，因此线性相关系数可能偏弱，"
            "二次拟合更能反映真实规律。")
    with c2:
        st.markdown("##### 🔮 合格率预测")
        plan_c = st.slider("计划炸药单耗（kg/m³）", 0.30, 0.85, 0.55, 0.01,
                           key="blast_pred")
        pred = float(poly(plan_c))
        st.metric("预测块度合格率", f"{pred:.1f}%")
        if lo <= plan_c <= hi:
            st.success(f"✅ 位于最佳单耗区间 [{lo}, {hi}] kg/m³ 内。")
        else:
            st.warning(f"⚠️ 偏离最佳单耗区间 [{lo}, {hi}] kg/m³，建议调整装药设计。")

    with st.expander("📋 爆破明细数据"):
        st.dataframe(d, width="stretch", hide_index=True)
        download_button(d, "blasting_detail.csv")
