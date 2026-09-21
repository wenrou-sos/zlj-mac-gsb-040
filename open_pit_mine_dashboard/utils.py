"""通用工具函数与 UI 组件：图表样式、KPI 卡片、日期过滤、下载按钮。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

#: Plotly 图表全局字体（自动回退到系统中文字体）
PLOT_FONT = "Microsoft YaHei, PingFang SC, Hiragino Sans GB, sans-serif"


def style_fig(fig, title: str | None = None, height: int = 420):
    """统一设置 Plotly 图表样式，保证全看板视觉风格一致。

    参数:
        fig: Plotly Figure 对象。
        title: 图表标题，为 None 时不设置。
        height: 图表高度（像素）。

    返回:
        样式化后的 Figure 对象。
    """
    fig.update_layout(
        template="plotly_white",
        font=dict(family=PLOT_FONT, size=13),
        height=height,
        margin=dict(l=40, r=30, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=17)))
    return fig


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    """渲染一行 KPI 指标卡片。

    参数:
        items: 由 ``(标签, 数值, 变化量)`` 三元组组成的列表，
            变化量传 None 则不显示。
    """
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            st.metric(label, value, delta)


def download_button(df: pd.DataFrame, filename: str,
                    label: str = "📥 下载数据 (CSV)") -> None:
    """生成 DataFrame 的 CSV 下载按钮（UTF-8 带 BOM，兼容 Excel）。"""
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label, csv, filename, "text/csv")


def filter_by_date(df: pd.DataFrame, date_range, col: str = "date"
                   ) -> pd.DataFrame:
    """按侧边栏选择的日期范围过滤数据框。

    参数:
        df: 待过滤的数据框。
        date_range: ``(起始日期, 结束日期)`` 二元组；长度不为 2 时返回原表。
        col: 日期列列名。

    返回:
        过滤后的数据框副本。
    """
    if df.empty or not date_range or len(date_range) != 2:
        return df
    start = pd.to_datetime(date_range[0])
    end = pd.to_datetime(date_range[1])
    return df[(df[col] >= start) & (df[col] <= end)].copy()
