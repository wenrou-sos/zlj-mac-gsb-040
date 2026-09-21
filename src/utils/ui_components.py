"""通用界面组件：KPI 卡片、区块标题、数据下载按钮等。"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def kpi_row(items: list[dict], columns_per_row: int = 4) -> None:
    """渲染一行 KPI 指标卡片。

    Parameters
    ----------
    items:
        每个元素为字典，支持键：
        ``label``（名称）、``value``（主值）、``delta``（变化值）、
        ``help``（悬浮说明）、``color``（强调色，可选）。
    columns_per_row:
        每行卡片数量（响应式，移动端会自动换行）。
    """
    for start in range(0, len(items), columns_per_row):
        batch = items[start : start + columns_per_row]
        cols = st.columns(len(batch))
        for col, item in zip(cols, batch, strict=True):
            with col:
                st.metric(
                    label=item["label"],
                    value=item["value"],
                    delta=item.get("delta"),
                    help=item.get("help"),
                )
                color = item.get("color")
                if color:
                    # 通过卡片底部色条强调状态
                    st.markdown(
                        f"<div style='height:3px;border-radius:2px;"
                        f"background:{color};margin-top:-10px;'></div>",
                        unsafe_allow_html=True,
                    )


def section_title(title: str, subtitle: str = "", icon: str = "") -> None:
    """渲染模块内分区标题。"""
    st.subheader(f"{icon} {title}".strip())
    if subtitle:
        st.caption(subtitle)


def info_banner(kind: str, message: str) -> None:
    """渲染提示横幅。

    Parameters
    ----------
    kind:
        提示类型：info / success / warning / error。
    message:
        提示文本。
    """
    getattr(st, kind)(message)


def download_csv_button(df: pd.DataFrame, filename: str, label: str = "⬇️ 导出 CSV") -> None:
    """渲染 DataFrame CSV 下载按钮（utf-8-sig，Excel 可直接打开）。"""
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
    )


def format_wan_tonnes(value: float) -> str:
    """将吨格式化为万吨字符串。"""
    return f"{value / 10000:,.1f} 万吨"
