"""数据加载工具。

负责从 CSV 文件加载模拟数据，并完成日期类型转换、字段校验等
基础处理。所有加载函数带 Streamlit 缓存，避免重复 IO。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

# CSV 文件 -> (日期列名) 映射
DATA_FILES = {
    "production": ("production_daily.csv", "date"),
    "shovel": ("shovel_daily.csv", "date"),
    "truck": ("truck_daily.csv", "date"),
    "loss_dilution": ("loss_dilution.csv", "date"),
    "blasting": ("blasting.csv", "date"),
    "cost": ("cost_monthly.csv", None),  # 月份使用 YYYY-MM 字符串
}


def get_data_dir() -> Path:
    """返回数据目录，优先使用环境变量 ``MINE_DATA_DIR``。"""
    return Path(__file__).resolve().parent.parent.parent / "data"


@st.cache_data(show_spinner="正在加载数据…")
def load_data() -> dict[str, pd.DataFrame]:
    """加载全部 CSV 数据并做基础类型转换。

    Returns
    -------
    dict
        键为数据集名称，值为对应的 ``DataFrame``。

    Raises
    ------
    FileNotFoundError
        数据目录或 CSV 文件不存在时抛出，由上层界面捕获并提示。
    """
    data_dir = get_data_dir()
    if not data_dir.exists():
        raise FileNotFoundError(f"数据目录不存在：{data_dir}，请先运行数据生成脚本。")

    result: dict[str, pd.DataFrame] = {}
    for key, (filename, date_col) in DATA_FILES.items():
        filepath = data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"数据文件缺失：{filepath}，请先运行数据生成脚本。")
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if date_col is not None:
            df[date_col] = pd.to_datetime(df[date_col])
        result[key] = df

    # 成本月度数据补充真正的月份时间戳
    result["cost"]["month_date"] = pd.to_datetime(result["cost"]["month"] + "-01")
    return result


def filter_by_date(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    date_col: str = "date",
) -> pd.DataFrame:
    """按闭区间 ``[start, end]`` 过滤数据。"""
    mask = (df[date_col] >= pd.Timestamp(start)) & (df[date_col] <= pd.Timestamp(end))
    return df.loc[mask].copy()
