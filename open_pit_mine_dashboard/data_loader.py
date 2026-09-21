"""数据加载模块：读取 CSV 数据文件并缓存。

所有加载函数均使用 ``st.cache_data`` 装饰器缓存结果，
避免页面交互时重复读取磁盘文件，保证应用响应速度。
"""

import pandas as pd
import streamlit as st

from config import (BLASTING_CSV, COST_CSV, LOSS_DILUTION_CSV, PRODUCTION_CSV,
                    SHOVEL_CSV, TRUCK_CSV)


def _read_csv(path, date_cols: list[str]) -> pd.DataFrame:
    """读取 CSV 文件并解析日期列。

    参数:
        path: CSV 文件路径。
        date_cols: 需要解析为日期的列名列表。

    返回:
        解析后的 DataFrame。

    异常:
        FileNotFoundError: 数据文件缺失时抛出，由入口层捕获并提示
            用户先运行 ``data_generator.py``。
    """
    if not path.exists():
        raise FileNotFoundError(f"数据文件缺失：{path.name}")
    return pd.read_csv(path, parse_dates=date_cols)


@st.cache_data(show_spinner=False)
def load_production() -> pd.DataFrame:
    """加载每日产量与计划数据。"""
    return _read_csv(PRODUCTION_CSV, ["date"])


@st.cache_data(show_spinner=False)
def load_shovel() -> pd.DataFrame:
    """加载电铲装车效率数据。"""
    return _read_csv(SHOVEL_CSV, ["date"])


@st.cache_data(show_spinner=False)
def load_truck() -> pd.DataFrame:
    """加载矿车运输效率数据。"""
    return _read_csv(TRUCK_CSV, ["date"])


@st.cache_data(show_spinner=False)
def load_loss_dilution() -> pd.DataFrame:
    """加载损失贫化与品位数据。"""
    return _read_csv(LOSS_DILUTION_CSV, ["date"])


@st.cache_data(show_spinner=False)
def load_blasting() -> pd.DataFrame:
    """加载爆破效果数据。"""
    return _read_csv(BLASTING_CSV, ["date"])


@st.cache_data(show_spinner=False)
def load_cost() -> pd.DataFrame:
    """加载月度成本构成数据。"""
    return _read_csv(COST_CSV, ["month"])


@st.cache_data(show_spinner="正在加载数据...")
def load_all() -> dict[str, pd.DataFrame]:
    """加载全部数据集。

    返回:
        以数据集名称为键、DataFrame 为值的字典。
    """
    return {
        "production": load_production(),
        "shovel": load_shovel(),
        "truck": load_truck(),
        "loss_dilution": load_loss_dilution(),
        "blasting": load_blasting(),
        "cost": load_cost(),
    }
