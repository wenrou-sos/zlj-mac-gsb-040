"""设备效率模块。

功能：
- 展示每台电铲的装车效率（秒/车，数值越低效率越高）；
- 展示每台矿车的运输效率（趟/班，数值越高效率越高）；
- 自动识别效率最低的 5 台设备并给出检修建议。
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (BOTTOM_N, COLOR_ACTUAL, COLOR_WARNING,
                    SHOVEL_TIME_THRESHOLD, TRUCK_TRIPS_THRESHOLD)
from utils import download_button, kpi_row, style_fig


# ---------------------------------------------------------------------------
# 数据汇总
# ---------------------------------------------------------------------------
def _shovel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """按电铲汇总加权平均装车时间（按装车数加权）。"""
    tmp = df.assign(_wt=df["avg_loading_time_sec"] * df["trucks_loaded"])
    agg = tmp.groupby("shovel_id").agg(
        wt=("_wt", "sum"),
        trucks=("trucks_loaded", "sum"),
        shifts=("shift", "count"),
    ).reset_index()
    agg["avg_time"] = agg["wt"] / agg["trucks"]
    return agg.sort_values("avg_time").reset_index(drop=True)


def _truck_summary(df: pd.DataFrame) -> pd.DataFrame:
    """按矿车汇总平均每班趟数。"""
    agg = df.groupby("truck_id").agg(
        avg_trips=("trips", "mean"),
        total_trips=("trips", "sum"),
        shifts=("shift", "count"),
    ).reset_index()
    return agg.sort_values("avg_trips", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 图表与建议
# ---------------------------------------------------------------------------
def _efficiency_bar(agg: pd.DataFrame, id_col: str, val_col: str,
                    title: str, unit: str, threshold: float,
                    lower_better: bool) -> go.Figure:
    """绘制设备效率柱状图，效率最低的 BOTTOM_N 台以红色高亮。"""
    if lower_better:
        worst_ids = set(agg.nlargest(BOTTOM_N, val_col)[id_col])
    else:
        worst_ids = set(agg.nsmallest(BOTTOM_N, val_col)[id_col])
    colors = [COLOR_WARNING if i in worst_ids else COLOR_ACTUAL
              for i in agg[id_col]]
    fig = go.Figure(go.Bar(
        x=agg[id_col], y=agg[val_col].round(2), marker_color=colors,
        hovertemplate=f"%{{x}}<br>效率: %{{y:.1f}} {unit}<extra></extra>",
    ))
    fig.add_hline(y=threshold, line_dash="dash", line_color=COLOR_WARNING,
                  annotation_text=f"预警线 {threshold} {unit}")
    fig.update_layout(xaxis_title="设备编号",
                      yaxis_title=f"{title}（{unit}）", showlegend=False)
    return style_fig(fig, f"{title}（红色为效率最低 {BOTTOM_N} 台）")


def _advice_table(agg: pd.DataFrame, id_col: str, val_col: str,
                  threshold: float, lower_better: bool,
                  val_name: str, unit: str) -> pd.DataFrame:
    """生成低效设备检修建议表。

    根据设备效率偏离预警阈值的程度，分级给出检修建议。
    """
    if lower_better:
        worst = agg.nlargest(BOTTOM_N, val_col).copy()
        worst["deviation"] = (worst[val_col] - threshold) / threshold
    else:
        worst = agg.nsmallest(BOTTOM_N, val_col).copy()
        worst["deviation"] = (threshold - worst[val_col]) / threshold

    def _advice(dev: float) -> tuple[str, str]:
        if dev > 0.25:
            return ("🔴 严重偏离",
                    "建议立即停机检修，重点排查液压系统、动力单元与关键结构件。")
        if dev > 0.10:
            return ("🟠 中度偏离",
                    "建议安排计划性检修，检查易损件磨损并复核操作规范。")
        return ("🟡 轻度偏离",
                "建议加强日常点检保养，关注润滑与易损件状态。")

    levels, advices = zip(*[_advice(d) for d in worst["deviation"]])
    result = pd.DataFrame({
        "设备编号": worst[id_col],
        val_name: worst[val_col].round(1),
        "偏离预警线": (worst["deviation"] * 100).round(1).astype(str) + "%",
        "预警等级": levels,
        "检修建议": advices,
    })
    return result.reset_index(drop=True)


def _trend_chart(df: pd.DataFrame, id_col: str, val_col: str,
                 selected: list[str], y_title: str,
                 weight_col: str | None = None) -> go.Figure:
    """绘制所选设备效率月度趋势，并叠加车队平均水平。"""
    tmp = df[df[id_col].isin(selected)].copy()
    tmp["month"] = tmp["date"].dt.to_period("M").dt.to_timestamp()
    if weight_col:
        tmp["_wt"] = tmp[val_col] * tmp[weight_col]
        g = tmp.groupby(["month", id_col]).agg(
            wt=("_wt", "sum"), w=(weight_col, "sum")).reset_index()
        g[val_col] = g["wt"] / g["w"]
    else:
        g = tmp.groupby(["month", id_col])[val_col].mean().reset_index()
    fig = px.line(g, x="month", y=val_col, color=id_col, markers=True,
                  labels={"month": "", val_col: y_title, id_col: "设备"})

    fleet = df.copy()
    fleet["month"] = fleet["date"].dt.to_period("M").dt.to_timestamp()
    if weight_col:
        fleet["_wt"] = fleet[val_col] * fleet[weight_col]
        gf = fleet.groupby("month").agg(
            wt=("_wt", "sum"), w=(weight_col, "sum")).reset_index()
        gf[val_col] = gf["wt"] / gf["w"]
    else:
        gf = fleet.groupby("month")[val_col].mean().reset_index()
    fig.add_scatter(x=gf["month"], y=gf[val_col], name="车队平均",
                    mode="lines", line=dict(color="#7F8C8D", dash="dash"))
    return style_fig(fig, "效率月度趋势", height=380)


# ---------------------------------------------------------------------------
# 子模块渲染
# ---------------------------------------------------------------------------
def _render_shovel(df: pd.DataFrame) -> None:
    """渲染电铲效率子模块。"""
    agg = _shovel_summary(df)
    fleet_avg = ((df["avg_loading_time_sec"] * df["trucks_loaded"]).sum()
                 / df["trucks_loaded"].sum())
    kpi_row([
        ("在册电铲", f"{agg['shovel_id'].nunique()} 台", None),
        ("平均装车时间", f"{fleet_avg:.1f} 秒/车", None),
        ("最优设备", f"{agg.iloc[0]['shovel_id']}"
         f"（{agg.iloc[0]['avg_time']:.1f} 秒）", None),
        ("最差设备", f"{agg.iloc[-1]['shovel_id']}"
         f"（{agg.iloc[-1]['avg_time']:.1f} 秒）", None),
    ])
    st.plotly_chart(
        _efficiency_bar(agg, "shovel_id", "avg_time", "电铲装车效率",
                        "秒/车", SHOVEL_TIME_THRESHOLD, lower_better=True),
        width="stretch")

    st.markdown("##### 📈 效率趋势对比")
    worst3 = agg.nlargest(3, "avg_time")["shovel_id"].tolist()
    selected = st.multiselect("选择电铲", agg["shovel_id"].tolist(),
                              default=worst3, key="shovel_sel")
    if selected:
        st.plotly_chart(
            _trend_chart(df, "shovel_id", "avg_loading_time_sec", selected,
                         "装车时间（秒/车）", weight_col="trucks_loaded"),
            width="stretch")

    st.markdown(f"##### 🛠️ 低效设备检修建议（效率最低 {BOTTOM_N} 台）")
    advice = _advice_table(agg, "shovel_id", "avg_time",
                           SHOVEL_TIME_THRESHOLD, lower_better=True,
                           val_name="平均装车时间(秒/车)", unit="秒/车")
    st.dataframe(advice, width="stretch", hide_index=True)
    download_button(advice, "shovel_maintenance_advice.csv")


def _render_truck(df: pd.DataFrame) -> None:
    """渲染矿车效率子模块。"""
    agg = _truck_summary(df)
    fleet_avg = df["trips"].mean()
    kpi_row([
        ("在册矿车", f"{agg['truck_id'].nunique()} 台", None),
        ("平均运输效率", f"{fleet_avg:.1f} 趟/班", None),
        ("最优设备", f"{agg.iloc[0]['truck_id']}"
         f"（{agg.iloc[0]['avg_trips']:.1f} 趟）", None),
        ("最差设备", f"{agg.iloc[-1]['truck_id']}"
         f"（{agg.iloc[-1]['avg_trips']:.1f} 趟）", None),
    ])
    st.plotly_chart(
        _efficiency_bar(agg, "truck_id", "avg_trips", "矿车运输效率",
                        "趟/班", TRUCK_TRIPS_THRESHOLD, lower_better=False),
        width="stretch")

    st.markdown("##### 📈 效率趋势对比")
    worst3 = agg.nsmallest(3, "avg_trips")["truck_id"].tolist()
    selected = st.multiselect("选择矿车", agg["truck_id"].tolist(),
                              default=worst3, key="truck_sel")
    if selected:
        st.plotly_chart(
            _trend_chart(df, "truck_id", "trips", selected, "趟数（趟/班）"),
            width="stretch")

    st.markdown(f"##### 🛠️ 低效设备检修建议（效率最低 {BOTTOM_N} 台）")
    advice = _advice_table(agg, "truck_id", "avg_trips",
                           TRUCK_TRIPS_THRESHOLD, lower_better=False,
                           val_name="平均趟数(趟/班)", unit="趟/班")
    st.dataframe(advice, width="stretch", hide_index=True)
    download_button(advice, "truck_maintenance_advice.csv")


def render(shovel_df: pd.DataFrame, truck_df: pd.DataFrame) -> None:
    """渲染设备效率模块。

    参数:
        shovel_df: 已按全局时间范围过滤后的电铲效率数据。
        truck_df: 已按全局时间范围过滤后的矿车效率数据。
    """
    st.subheader("🚜 设备效率分析")
    if shovel_df.empty and truck_df.empty:
        st.warning("所选时间范围内没有设备效率数据，请调整时间范围。")
        return

    tab_shovel, tab_truck = st.tabs(["⛏️ 电铲装车效率", "🚚 矿车运输效率"])
    with tab_shovel:
        if shovel_df.empty:
            st.warning("所选时间范围内没有电铲数据。")
        else:
            _render_shovel(shovel_df)
    with tab_truck:
        if truck_df.empty:
            st.warning("所选时间范围内没有矿车数据。")
        else:
            _render_truck(truck_df)
