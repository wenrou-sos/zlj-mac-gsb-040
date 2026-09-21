"""露天矿关键生产指标分析看板 —— 应用入口。

功能模块：总览、产量分析、设备效率、损失贫化、爆破效果、成本分析。

运行方式:
    streamlit run app.py
"""

import streamlit as st

from config import APP_ICON, APP_SUBTITLE, APP_TITLE
from data_loader import load_all
from modules import blasting, cost, equipment, loss_dilution, overview
from modules import production
from utils import filter_by_date

# ---------------------------------------------------------------------------
# 页面配置（必须作为第一个 Streamlit 调用）
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

#: 自定义样式：顶部横幅、KPI 卡片、侧边栏底色
_CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.banner {
    background: linear-gradient(100deg, #154360 0%, #1F618D 60%, #2980B9 100%);
    padding: 1.1rem 1.6rem;
    border-radius: 12px;
    color: #ffffff;
    margin-bottom: 0.8rem;
}
.banner h1 {margin: 0; font-size: 1.55rem; font-weight: 700;}
.banner p {margin: 0.25rem 0 0 0; opacity: 0.85; font-size: 0.9rem;}
[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 0.55rem 0.9rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
[data-testid="stSidebar"] {background-color: #f7f9fb;}
</style>
"""

#: 功能模块路由表
MODULES = [
    "🏠 总览",
    "⛏️ 产量分析",
    "🚜 设备效率",
    "📉 损失贫化",
    "💥 爆破效果",
    "💰 成本分析",
]


def _route(module_name: str, data: dict, date_range) -> None:
    """根据侧边栏选择路由到对应功能模块。

    参数:
        module_name: 模块名称（见 ``MODULES``）。
        data: 全部数据集字典。
        date_range: 全局日期范围筛选。
    """
    if module_name == "🏠 总览":
        overview.render(data, date_range)
    elif module_name == "⛏️ 产量分析":
        production.render(filter_by_date(data["production"], date_range))
    elif module_name == "🚜 设备效率":
        equipment.render(filter_by_date(data["shovel"], date_range),
                         filter_by_date(data["truck"], date_range))
    elif module_name == "📉 损失贫化":
        loss_dilution.render(filter_by_date(data["loss_dilution"], date_range))
    elif module_name == "💥 爆破效果":
        blasting.render(filter_by_date(data["blasting"], date_range))
    elif module_name == "💰 成本分析":
        cost.render(filter_by_date(data["cost"], date_range, col="month"))


def main() -> None:
    """应用主入口：渲染页面框架、加载数据并路由到功能模块。"""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="banner"><h1>{APP_ICON} {APP_TITLE}</h1>'
        f"<p>{APP_SUBTITLE} · 产量 / 设备 / 质量 / 爆破 / 成本 一体化分析</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---------------- 数据加载（含异常处理） ----------------
    try:
        data = load_all()
    except FileNotFoundError as exc:
        st.error(f"❌ 数据加载失败：{exc}")
        st.info("💡 请先在项目根目录执行 `python data_generator.py` "
                "生成模拟数据，然后刷新页面。")
        st.stop()
    except Exception as exc:  # noqa: BLE001 —— 顶层兜底，避免白屏
        st.error(f"❌ 数据加载出现异常：{exc}")
        st.stop()

    # ---------------- 侧边栏控制台 ----------------
    st.sidebar.title("⚙️ 控制台")
    module_name = st.sidebar.radio("功能模块", MODULES)

    min_d = data["production"]["date"].min().date()
    max_d = data["production"]["date"].max().date()
    date_range = st.sidebar.date_input(
        "分析时间范围", value=(min_d, max_d),
        min_value=min_d, max_value=max_d)
    if not date_range or len(date_range) != 2:
        date_range = (min_d, max_d)
    st.sidebar.caption(f"📅 数据区间：{min_d} ~ {max_d}")

    with st.sidebar.expander("ℹ️ 关于本看板"):
        st.caption(
            "露天矿关键生产指标分析看板 v1.0\n\n"
            "- 数据来源：模拟生成 CSV\n"
            "- 技术栈：Streamlit + Plotly + Pandas\n"
            "- 业务阈值可在 `config.py` 中调整"
        )

    # ---------------- 模块路由（含异常处理） ----------------
    try:
        _route(module_name, data, date_range)
    except Exception as exc:  # noqa: BLE001 —— 顶层兜底，避免白屏
        st.error(f"😞 模块运行出错：{exc}")
        st.info("请尝试调整筛选条件；若问题持续，请检查数据文件完整性。")


if __name__ == "__main__":
    main()
