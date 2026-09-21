"""露天矿关键生产指标分析看板 —— 模拟数据生成模块。

生成 6 份带真实业务规律（季节性、设备老化、成本上涨、异常事件等）的
CSV 数据文件，供 Streamlit 看板加载使用：

1. production_daily.csv  采剥生产日报（日计划 / 实际矿石量、岩石量、完成率）
2. shovel_daily.csv      电铲装车效率日报（秒/车）
3. truck_daily.csv       矿车运输效率日报（趟/班）
4. loss_dilution.csv     矿石损失 / 贫化及品位对比（按爆区/月份）
5. blasting.csv          爆破记录（炸药单耗、块度合格率等）
6. cost_monthly.csv      采矿单位成本月度数据（四项成本构成）

用法::

    python -m src.data_generation            # 生成到 ./data
    python -m src.data_generation --reset    # 强制重新生成
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# 全局参数
# --------------------------------------------------------------------------
START_DATE = "2023-01-01"
END_DATE = "2026-09-20"
RNG_SEED = 20260921

# 采剥计划基准：首年计划矿石量 / 岩石量（吨/日）
BASE_ORE_PLAN = 42000.0
BASE_WASTE_PLAN = 105000.0
# 年度产量增长系数（每年在去年基础上增长）
ANNUAL_GROWTH = 0.05

# 电铲 / 矿车台账（编号, 名称, 投用年份）
SHOVELS = [
    ("WK-10", "10#电铲", 2015),
    ("WK-12", "12#电铲", 2018),
    ("WK-15", "15#电铲", 2020),
    ("WK-18", "18#电铲", 2022),
    ("WK-20", "20#电铲", 2012),
    ("WK-22", "22#电铲", 2019),
    ("WK-25", "25#电铲", 2023),
    ("WK-28", "28#电铲", 2016),
]
TRUCKS = [
    ("TR-01", "01#矿车", 2017),
    ("TR-02", "02#矿车", 2021),
    ("TR-03", "03#矿车", 2019),
    ("TR-04", "04#矿车", 2014),
    ("TR-05", "05#矿车", 2022),
    ("TR-06", "06#矿车", 2018),
    ("TR-07", "07#矿车", 2020),
    ("TR-08", "08#矿车", 2015),
    ("TR-09", "09#矿车", 2023),
    ("TR-10", "10#矿车", 2016),
    ("TR-11", "11#矿车", 2021),
    ("TR-12", "12#矿车", 2013),
]

# 各成本项首年基准（元/吨）
BASE_COST = {
    "drilling": 2.35,  # 穿孔
    "blasting": 3.60,  # 爆破
    "loading": 2.85,  # 铲装
    "haulage": 7.40,  # 运输
}


def _seasonal_factor(day_of_year: np.ndarray) -> np.ndarray:
    """季节性系数：雨季（夏季）效率略低，四季度冲刺产量略高。"""
    angle = 2 * np.pi * (day_of_year - 15) / 365.0
    return 1.0 + 0.07 * np.cos(angle) - 0.03 * np.cos(4 * np.pi * day_of_year / 365.0)


def generate_production(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成采剥生产日报数据。

    实际产量 = 计划产量 × 季节性系数 × 完成率扰动
    （含自相关，模拟连续天气影响）。
    完成率 = 实际采剥总量 / 计划采剥总量 × 100%。
    """
    years = dates.year - dates.year.min()
    growth = (1.0 + ANNUAL_GROWTH) ** years.to_numpy()
    season = _seasonal_factor(dates.dayofyear.to_numpy())

    ore_plan = BASE_ORE_PLAN * growth * season
    waste_plan = BASE_WASTE_PLAN * growth * season

    # 自相关扰动：AR(1) 过程，模拟连续数天的天气/设备工况影响
    noise = np.zeros(len(dates))
    for i in range(1, len(dates)):
        noise[i] = 0.65 * noise[i - 1] + rng.normal(0, 0.035)

    # 矿石与岩石的实现率略有差异
    ore_noise = noise + rng.normal(0, 0.02, len(dates))
    waste_noise = noise + rng.normal(0, 0.025, len(dates))
    ore_actual = ore_plan * np.clip(1.0 + ore_noise, 0.55, 1.2)
    waste_actual = waste_plan * np.clip(1.0 + waste_noise, 0.55, 1.22)

    # 注入少量设备故障导致的低产日
    fault_idx = rng.choice(len(dates), size=8, replace=False)
    for idx in fault_idx:
        ore_actual[idx] *= rng.uniform(0.45, 0.65)
        waste_actual[idx] *= rng.uniform(0.45, 0.65)

    total_plan = ore_plan + waste_plan
    total_actual = ore_actual + waste_actual

    df = pd.DataFrame(
        {
            "date": dates,
            "ore_plan_t": np.round(ore_plan, 1),
            "waste_plan_t": np.round(waste_plan, 1),
            "total_plan_t": np.round(total_plan, 1),
            "ore_actual_t": np.round(ore_actual, 1),
            "waste_actual_t": np.round(waste_actual, 1),
            "total_actual_t": np.round(total_actual, 1),
            "completion_rate": np.round(total_actual / total_plan * 100.0, 2),
            "stripping_ratio": np.round(waste_actual / ore_actual, 3),
        }
    )
    return df


def _aging_factor(year: int, current: int) -> float:
    """设备老化系数：每多服役一年，效率指标恶化约 1%。"""
    return 1.0 + max(current - year, 0) * 0.008


def generate_shovels(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成电铲装车效率日报（秒/车，数值越低效率越高）。"""
    records: list[dict] = []
    for shovel_id, name, build_year in SHOVELS:
        base_cycle = rng.uniform(118.0, 132.0)  # 基础装车周期
        ar = rng.normal(0, 1.5, len(dates))
        for i in range(1, len(ar)):
            ar[i] = 0.4 * ar[i - 1] + ar[i]
        age_penalty = np.array([_aging_factor(build_year, d.year) for d in dates])
        cycle_sec = np.asarray(
            base_cycle * age_penalty
            + 4.0 * np.sin(2 * np.pi * dates.dayofyear.to_numpy() / 365.0)
            + ar,
            dtype=float,
        )
        # 故障/大修日：周期显著拉长
        fault_days = rng.choice(len(dates), size=rng.integers(6, 12), replace=False)
        cycle_sec[fault_days] += rng.uniform(35.0, 90.0, len(fault_days))
        cycle_sec = np.clip(cycle_sec, 95.0, 260.0)

        # 日装车数与作业时长
        work_hours = np.full(len(dates), rng.uniform(18.0, 21.0))
        work_hours[fault_days] = rng.uniform(4.0, 12.0, len(fault_days))
        trucks_loaded = np.floor(work_hours * 3600.0 / cycle_sec)

        for i, d in enumerate(dates):
            records.append(
                {
                    "date": d,
                    "equipment_id": shovel_id,
                    "equipment_name": name,
                    "build_year": build_year,
                    "cycle_sec_per_truck": round(float(cycle_sec[i]), 1),
                    "trucks_loaded": int(trucks_loaded[i]),
                    "work_hours": round(float(work_hours[i]), 1),
                }
            )
    df = pd.DataFrame(records)
    return df.sort_values(["date", "equipment_id"]).reset_index(drop=True)


def generate_trucks(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成矿车运输效率日报（趟/班，数值越高效率越高）。"""
    records: list[dict] = []
    for truck_id, name, build_year in TRUCKS:
        base_trips = rng.uniform(7.5, 9.2)  # 基础趟/班
        ar = rng.normal(0, 0.25, len(dates))
        for i in range(1, len(ar)):
            ar[i] = 0.35 * ar[i - 1] + ar[i]
        age_penalty = np.array([1.0 / _aging_factor(build_year, d.year) for d in dates])
        # 雨季道路条件差，趟数下降
        rain = -0.45 * np.maximum(
            np.sin(2 * np.pi * (dates.dayofyear.to_numpy() - 60) / 365.0), 0.0
        )
        trips_per_shift = np.asarray(base_trips * age_penalty + rain + ar, dtype=float)

        fault_days = rng.choice(len(dates), size=rng.integers(8, 16), replace=False)
        trips_per_shift[fault_days] -= rng.uniform(2.5, 5.0, len(fault_days))
        trips_per_shift = np.clip(trips_per_shift, 2.0, 11.0)

        payload = rng.uniform(215.0, 235.0)
        shifts = rng.choice([2, 3], size=len(dates), p=[0.35, 0.65])
        shifts[fault_days] = rng.choice([0, 1], size=len(fault_days), p=[0.4, 0.6])
        haulage_t = trips_per_shift * shifts * payload

        for i, d in enumerate(dates):
            records.append(
                {
                    "date": d,
                    "equipment_id": truck_id,
                    "equipment_name": name,
                    "build_year": build_year,
                    "trips_per_shift": round(float(trips_per_shift[i]), 2),
                    "shifts_worked": int(shifts[i]),
                    "payload_t": round(payload, 1),
                    "daily_haulage_t": round(float(haulage_t[i]), 1),
                }
            )
    df = pd.DataFrame(records)
    return df.sort_values(["date", "equipment_id"]).reset_index(drop=True)


def generate_loss_dilution(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成矿石损失率、贫化率及品位对比数据（按爆区，约每月 4 条）。"""
    records: list[dict] = []
    block_counter = 1
    for _period, group in pd.Series(dates).groupby(dates.to_period("M")):
        month_days = group.values
        # 每月 3~5 个出矿爆区
        n_blocks = int(rng.integers(3, 6))
        chosen = rng.choice(month_days, size=min(n_blocks, len(month_days)), replace=False)
        chosen = sorted(chosen)
        for event_day in chosen:
            d = pd.Timestamp(event_day)
            year_idx = d.year - dates.year.min()

            # 损失率、贫化率随管理水平提升缓慢下降
            loss_mean = 6.2 - 0.25 * year_idx
            dilution_mean = 5.4 - 0.2 * year_idx
            loss_rate = loss_mean + rng.normal(0, 0.7)
            dilution_rate = dilution_mean + rng.normal(0, 0.6)

            # 地质模型品位围绕 2.8% 波动，实际品位因贫化系统性略低
            model_grade = 2.85 + 0.25 * np.sin(block_counter / 9.0) + rng.normal(0, 0.08)
            actual_grade = model_grade * (1.0 - dilution_rate / 100.0) + rng.normal(0, 0.04)
            tonnage = rng.uniform(8.0, 20.0)  # 爆区出矿量（万吨）

            # 异常注入：约 8% 爆区出现损失或贫化异常
            anomaly_type = ""
            roll = rng.random()
            if roll < 0.045:
                loss_rate += rng.uniform(3.0, 5.5)
                anomaly_type = "损失率异常：矿岩分界欠挖/底板残留"
            elif roll < 0.085:
                dilution_rate += rng.uniform(3.0, 5.0)
                actual_grade -= rng.uniform(0.25, 0.5)
                anomaly_type = "贫化率异常：废石混入/边坡塌落"

            grade_deviation = actual_grade - model_grade
            records.append(
                {
                    "date": d,
                    "block_id": f"B{block_counter:04d}",
                    "ore_tonnage_wt": round(tonnage, 2),
                    "loss_rate_pct": round(float(loss_rate), 2),
                    "dilution_rate_pct": round(float(dilution_rate), 2),
                    "model_grade_pct": round(float(model_grade), 3),
                    "actual_grade_pct": round(float(actual_grade), 3),
                    "grade_deviation_pct": round(float(grade_deviation), 3),
                    "anomaly_flag": int(bool(anomaly_type)),
                    "anomaly_reason": anomaly_type,
                }
            )
            block_counter += 1
    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


def generate_blasting(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成爆破效果记录（炸药单耗 vs 块度合格率）。

    块度合格率与炸药单耗呈倒 U 形关系，最佳区间约 0.70~0.95 kg/t。
    """
    n_events = 165
    event_days = rng.choice(dates, size=n_events, replace=True)
    event_days = pd.DatetimeIndex(sorted(event_days))

    powder_factor = np.clip(rng.normal(0.82, 0.13, n_events), 0.45, 1.35)
    # 倒 U 形：偏离最佳单耗 0.82 越远合格率越低
    optimum = 0.82
    quality = (
        94.0
        - 60.0 * (powder_factor - optimum) ** 2
        - 30.0 * np.maximum(powder_factor - 1.05, 0.0)
        + rng.normal(0, 1.5, n_events)
    )
    quality = np.clip(quality, 58.0, 98.0)

    # 岩石坚固性系数 f：硬度越高需要的单耗越大
    rock_hardness = np.clip(
        8.0 + 25.0 * (powder_factor - 0.6) + rng.normal(0, 1.2, n_events),
        4.0,
        18.0,
    )
    hole_count = rng.integers(60, 220, n_events)
    total_tonnage = rng.uniform(6.0, 22.0, n_events)  # 爆破矿岩量（万吨）

    df = pd.DataFrame(
        {
            "date": event_days,
            "blast_id": [f"BL-{i + 1:04d}" for i in range(n_events)],
            "powder_factor_kgpt": np.round(powder_factor, 3),
            "fragment_pass_rate_pct": np.round(quality, 1),
            "rock_hardness_f": np.round(rock_hardness, 1),
            "hole_count": hole_count,
            "blast_tonnage_wt": np.round(total_tonnage, 2),
            "boulder_rate_pct": np.round(
                np.clip(100.0 - quality + rng.normal(0, 1.0, n_events), 1.0, 40.0),
                1,
            ),
        }
    )
    return df.sort_values("date").reset_index(drop=True)


def generate_costs(rng: np.random.Generator, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """生成采矿单位成本月度数据（元/吨），含同比/环比所需的完整历史。"""
    months = pd.date_range(START_DATE, END_DATE, freq="MS")
    records: list[dict] = []
    for m in months:
        idx = (m.year - int(START_DATE[:4])) * 12 + m.month - 1
        # 缓慢通胀 + 季节性（冬季柴油/轮胎消耗高）
        inflation = 1.0 + 0.003 * idx
        winter = 1.0 + 0.02 * max(np.cos(2 * np.pi * (m.month - 1) / 12.0), 0.0)

        costs = {}
        for key, base in BASE_COST.items():
            noise = rng.normal(0, 0.06)
            costs[key] = max(0.5, base * inflation * winter + noise)

        # 注入异常成本月份
        anomaly_reason = ""
        roll = rng.random()
        if roll < 0.06:
            costs["haulage"] += rng.uniform(0.6, 1.4)  # 柴油涨价
            anomaly_reason = "柴油价格上涨/运距增加"
        elif roll < 0.11:
            costs["blasting"] += rng.uniform(0.5, 1.1)  # 炸药涨价
            anomaly_reason = "炸药单价上涨/大块二次破碎"
        elif roll < 0.15:
            costs["drilling"] += rng.uniform(0.3, 0.7)
            anomaly_reason = "钻具损耗异常/钻头寿命下降"

        drilling, blasting_cost = costs["drilling"], costs["blasting"]
        loading, haulage = costs["loading"], costs["haulage"]
        total = drilling + blasting_cost + loading + haulage
        # 计划成本按理论值（无异常、低噪声）估算
        plan_total = sum(BASE_COST[k] * inflation * 0.985 for k in BASE_COST)

        records.append(
            {
                "month": m.strftime("%Y-%m"),
                "drilling_cost": round(drilling, 2),
                "blasting_cost": round(blasting_cost, 2),
                "loading_cost": round(loading, 2),
                "haulage_cost": round(haulage, 2),
                "total_cost": round(total, 2),
                "plan_total_cost": round(plan_total, 2),
                "anomaly_flag": int(bool(anomaly_reason)),
                "anomaly_reason": anomaly_reason,
            }
        )
    return pd.DataFrame(records)


def generate_all(data_dir: str | Path = "data", reset: bool = False) -> dict[str, pd.DataFrame]:
    """生成全部 CSV 文件并返回数据字典。

    Parameters
    ----------
    data_dir:
        CSV 输出目录。
    reset:
        为 ``True`` 时即使文件已存在也强制重新生成。
    """
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(RNG_SEED)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")

    generators = {
        "production_daily.csv": lambda: generate_production(rng, dates),
        "shovel_daily.csv": lambda: generate_shovels(rng, dates),
        "truck_daily.csv": lambda: generate_trucks(rng, dates),
        "loss_dilution.csv": lambda: generate_loss_dilution(rng, dates),
        "blasting.csv": lambda: generate_blasting(rng, dates),
        "cost_monthly.csv": lambda: generate_costs(rng, dates),
    }

    result: dict[str, pd.DataFrame] = {}
    for filename, gen_func in generators.items():
        target = data_path / filename
        if target.exists() and not reset:
            result[filename] = pd.read_csv(target)
            continue
        df = gen_func()
        df.to_csv(target, index=False, encoding="utf-8-sig")
        result[filename] = df
        print(f"已生成 {filename}: {len(df):,} 行")
    return result


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="生成露天矿看板模拟数据")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("MINE_DATA_DIR", "data"),
        help="CSV 输出目录（默认 ./data）",
    )
    parser.add_argument("--reset", action="store_true", help="强制重新生成全部数据")
    args = parser.parse_args()
    generate_all(args.data_dir, reset=args.reset)
    print(f"\n全部数据已保存至: {Path(args.data_dir).resolve()}")


if __name__ == "__main__":
    main()
