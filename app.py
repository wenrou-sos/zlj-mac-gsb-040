"""露天矿关键生产指标分析看板 —— Streamlit 应用入口。

运行方式::

    streamlit run app.py

功能模块：总览、产量分析、设备效率、损失贫化、爆破效果、成本分析。
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components import (
    blasting,
    cost,
    equipment,
    loss_dilution,
    overview,
    production,
)
from src.utils.data_loader import load_data

# --------------------------------------------------------------------------
# 页面基础配置
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="露天矿关键生产指标分析看板",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* 主标题渐变条 */
    .app-header {
        background: linear-gradient(90deg, #1f3a5f 0%, #2c5282 60%,
                    #f59e0b 130%);
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        color: #fff;
        margin-bottom: 1.1rem;
    }
    .app-header h1 { margin: 0; font-size: 1.55rem; font-weight: 700; }
    .app-header p { margin: 0.25rem 0 0; opacity: .85; font-size: .9rem; }
    /* 卡片化容器 */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, .05);
    }
    [data-testid="stMetricValue"] { font-size: 1.25rem; }
    /* 侧边栏标题 */
    .side-title {
        font-weight: 700; color: #1f3a5f; font-size: 1.05rem;
        margin-bottom: .25rem;
    }
    /* 页脚 */
    .app-footer {
        text-align: center; color: #94a3b8; font-size: .8rem;
        margin-top: 2rem; padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }
    /* 窄屏适配 */
    @media (max-width: 640px) {
        .app-header h1 { font-size: 1.15rem; }
        [data-testid="stMetricValue"] { font-size: 1.05rem; }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

MODULES = {
    "🏔️ 矿山运行总览": ("overview", overview.render),
    "⛏️ 产量分析": ("production", production.render),
    "🚛 设备效率": ("equipment", equipment.render),
    "🧪 损失贫化": ("loss_dilution", loss_dilution.render),
    "🧨 爆破效果": ("blasting", blasting.render),
    "📊 成本分析": ("cost", cost.render),
}


@st.cache_data(show_spinner=False)
def get_date_bounds(
    prod_df: pd.DataFrame,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """获取数据集中可用的最小/最大日期。"""
    return prod_df["date"].min(), prod_df["date"].max()


def render_header() -> None:
    """渲染顶部渐变标题栏。"""
    st.markdown(
        """
        <div class="app-header">
            <h1>⛏️ 露天矿关键生产指标分析看板</h1>
            <p>采剥产量 · 设备效率 · 损失贫化 · 爆破效果 · 采矿成本
               一体化分析平台</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(
    min_date: pd.Timestamp, max_date: pd.Timestamp
) -> tuple[str, pd.Timestamp, pd.Timestamp]:
    """渲染侧边栏：模块导航与全局时间筛选。

    Returns
    -------
    tuple
        (所选模块名称, 起始日期, 截止日期)
    """
    with st.sidebar:
        st.markdown("<div class='side-title'>📍 功能导航</div>", unsafe_allow_html=True)
        choice = st.radio(
            "请选择分析模块",
            list(MODULES.keys()),
            label_visibility="collapsed",
        )
        st.divider()

        st.markdown(
            "<div class='side-title'>🗓️ 全局时间筛选</div>",
            unsafe_allow_html=True,
        )
        use_all = st.checkbox(
            "使用全部数据时间范围",
            value=False,
            help="勾选后忽略起止日期，对全量数据进行分析。",
        )
        if use_all:
            start, end = min_date, max_date
            st.caption(f"当前范围：{start:%Y-%m-%d} ~ {end:%Y-%m-%d}")
        else:
            date_range = st.date_input(
                "选择时间范围",
                value=(
                    max(min_date, max_date - pd.Timedelta(days=365)),
                    max_date,
                ),
                min_value=min_date,
                max_value=max_date,
                format="YYYY-MM-DD",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = (
                    pd.Timestamp(date_range[0]),
                    pd.Timestamp(date_range[1]) + pd.Timedelta(hours=23),
                )
            else:
                # 用户只选了一个日期时默认延展到最大日期
                start = pd.Timestamp(min_date)
                end = pd.Timestamp(max_date)
                st.info("请选择起止日期（拖拽可快速选择区间）。")

        st.divider()
        st.caption("📦 数据源：模拟 CSV 数据")
        st.caption("⚙️ 技术栈：Python · Streamlit · Plotly · Pandas")
    return choice, start, end


def main() -> None:
    """应用主流程：加载数据 -> 侧边栏筛选 -> 分发到各功能模块。"""
    render_header()

    # 数据加载与错误处理
    try:
        data = load_data()
    except FileNotFoundError as exc:
        st.error(f"数据文件缺失：{exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，保证界面友好提示
        st.error(f"数据加载失败：{exc}")
        st.caption("请尝试在终端执行：`python -m src.data_generation --reset` 重新生成数据。")
        st.stop()

    min_date, max_date = get_date_bounds(data["production"])
    choice, start, end = render_sidebar(min_date, max_date)

    if start > end:
        st.error("起始日期不能晚于截止日期，请重新选择时间范围。")
        st.stop()

    # 分发渲染
    module_key, render_func = MODULES[choice]
    try:
        if module_key == "overview":
            render_func(data, start, end)
        elif module_key == "production":
            render_func(data["production"], start, end)
        elif module_key == "equipment":
            render_func(data["shovel"], data["truck"], start, end)
        elif module_key == "loss_dilution":
            render_func(data["loss_dilution"], start, end)
        elif module_key == "blasting":
            render_func(data["blasting"], start, end)
        elif module_key == "cost":
            render_func(data["cost"], start, end)
    except Exception as exc:  # noqa: BLE001 - 模块级异常兜底
        st.error(f"模块渲染出现异常：{exc}")
        st.caption("请检查数据文件是否完整，或缩小时间范围后重试。")

    st.markdown(
        "<div class='app-footer'>露天矿关键生产指标分析看板 · "
        "数据均为模拟数据，仅用于功能演示 · © 2026</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
