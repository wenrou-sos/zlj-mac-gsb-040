"""露天矿模拟数据生成脚本。

运行本脚本将在 ``data/`` 目录下生成看板所需的全部 CSV 数据文件。
数据基于真实露天矿生产规律模拟（产能爬坡、季节波动、周日检修、
设备故障、断层带异常、燃油价格阶跃等），仅供系统演示与开发测试。

用法:
    python data_generator.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 全局常量
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
START_DATE = "2024-01-01"
END_DATE = "2026-09-19"
RANDOM_SEED = 42

SHIFTS = ["早班", "中班", "夜班"]
SHOVEL_IDS = [f"ES-{i:02d}" for i in range(1, 9)]    # 8 台电铲
TRUCK_IDS = [f"TR-{i:02d}" for i in range(1, 21)]    # 20 台矿车
ROCK_TYPES = ["花岗岩", "片麻岩", "大理岩", "砂岩"]
BENCHES = ["1010m", "1025m", "1040m", "1055m", "1070m"]


def generate_production(rng: np.random.Generator) -> pd.DataFrame:
    """生成每日产量与计划数据（矿石量、岩石量、计划量）。

    模拟特征：产能爬坡趋势、季节波动、周日检修减产、随机故障/天气事件。
    """
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    n = len(dates)
    doy = dates.dayofyear.to_numpy()
    dow = dates.dayofweek.to_numpy()

    trend = np.linspace(0, 4000, n)                    # 产能逐年爬坡
    seasonal = 2500 * np.sin(2 * np.pi * (doy - 90) / 365.25)
    sunday_drop = np.where(dow == 6, -5000, 0)         # 周日计划检修

    ore = (30000 + 0.4 * trend + 0.3 * seasonal + 0.4 * sunday_drop
           + rng.normal(0, 2200, n))
    rock = (50000 + 0.6 * trend + 0.7 * seasonal + 0.6 * sunday_drop
            + rng.normal(0, 3800, n))

    # 随机设备故障 / 极端天气导致的减产事件
    event_idx = rng.choice(n, size=20, replace=False)
    event_factor = rng.uniform(0.35, 0.75, size=20)
    ore[event_idx] *= event_factor
    rock[event_idx] *= event_factor

    df = pd.DataFrame({
        "date": dates,
        "ore_volume": np.clip(ore, 5000, None).round(0),
        "rock_volume": np.clip(rock, 8000, None).round(0),
    })
    df["total_volume"] = df["ore_volume"] + df["rock_volume"]

    # 计划量：按年/月台阶式增长，附加少量月度扰动
    month_keys = df["date"].dt.to_period("M")
    monthly_plan = {}
    for key in month_keys.unique():
        base = 80000 + (key.year - 2024) * 1500 + (key.month - 1) * 60
        monthly_plan[key] = base + rng.normal(0, 500)
    df["plan_volume"] = month_keys.map(monthly_plan).round(0)
    return df


def generate_shovel_efficiency(rng: np.random.Generator) -> pd.DataFrame:
    """生成电铲分班次装车效率数据（秒/车）。

    每台电铲设有固有效率水平，其中 ES-04、ES-07 明显偏低，
    用于演示低效设备自动识别功能。
    """
    base_map = {sid: rng.normal(125, 10) for sid in SHOVEL_IDS}
    base_map["ES-04"] += 35   # 液压系统老化，装车明显偏慢
    base_map["ES-07"] += 28
    base_map["ES-02"] += 12

    rows = []
    for date in pd.date_range(START_DATE, END_DATE, freq="D"):
        for shift in SHIFTS:
            for sid in SHOVEL_IDS:
                if rng.random() > 0.78:      # 约 22% 时间检修/停用
                    continue
                load_time = base_map[sid] + rng.normal(0, 8)
                if rng.random() < 0.03:      # 偶发故障导致效率恶化
                    load_time += rng.uniform(30, 80)
                trucks = max(int(rng.normal(95, 18)), 20)
                rows.append({
                    "date": date,
                    "shift": shift,
                    "shovel_id": sid,
                    "avg_loading_time_sec": round(max(load_time, 60), 1),
                    "trucks_loaded": trucks,
                    "ore_volume_t": round(trucks * rng.uniform(28, 33), 0),
                })
    return pd.DataFrame(rows)


def generate_truck_efficiency(rng: np.random.Generator) -> pd.DataFrame:
    """生成矿车分班次运输效率数据（趟/班）。

    TR-05、TR-12、TR-17 等车辆效率明显偏低，用于演示低效识别。
    """
    base_map = {tid: rng.normal(11.0, 0.9) for tid in TRUCK_IDS}
    for tid, cut in {"TR-05": 3.0, "TR-12": 2.6,
                     "TR-17": 2.2, "TR-08": 1.4}.items():
        base_map[tid] -= cut                 # 车况老化，趟数偏少

    rows = []
    for date in pd.date_range(START_DATE, END_DATE, freq="D"):
        for shift in SHIFTS:
            for tid in TRUCK_IDS:
                if rng.random() > 0.80:      # 约 20% 时间停用/保养
                    continue
                trips = base_map[tid] + rng.normal(0, 1.1)
                if rng.random() < 0.03:      # 偶发故障
                    trips -= rng.uniform(1.5, 3.5)
                trips = float(np.clip(trips, 3, 16))
                rows.append({
                    "date": date,
                    "shift": shift,
                    "truck_id": tid,
                    "trips": round(trips, 1),
                    "avg_cycle_time_min": round(
                        np.clip(470 / trips + rng.normal(0, 2.5), 25, 95), 1),
                    "payload_t": round(rng.normal(30, 2), 1),
                })
    return pd.DataFrame(rows)


def generate_loss_dilution(rng: np.random.Generator) -> pd.DataFrame:
    """生成每日损失率、贫化率与品位数据。

    模拟特征：2025-06 ~ 2025-08 断层破碎带开采导致损失贫化升高，
    并注入若干化验/配矿异常点用于演示异常标记功能。
    """
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    n = len(dates)
    doy = dates.dayofyear.to_numpy()

    loss = 4.3 + 0.5 * np.sin(2 * np.pi * doy / 365.25) + rng.normal(0, 0.45, n)
    dilution = (5.2 + 0.6 * np.sin(2 * np.pi * doy / 365.25 + 0.8)
                + rng.normal(0, 0.55, n))

    # 断层破碎带开采期：损失贫化显著升高
    fault = (dates >= "2025-06-01") & (dates <= "2025-08-15")
    loss = loss + np.where(fault, rng.uniform(1.2, 2.2, n), 0)
    dilution = dilution + np.where(fault, rng.uniform(1.5, 2.5, n), 0)

    model_grade = (30.8 + 0.6 * np.sin(2 * np.pi * doy / 365.25 + 2.0)
                   + rng.normal(0, 0.25, n))
    actual_grade = (model_grade - 0.75 + 0.05 * (dilution - 5.2)
                    + rng.normal(0, 0.3, n))
    actual_grade = actual_grade - np.where(fault, 0.45, 0)  # 断层带品位下滑

    # 偶发化验 / 配矿异常
    n_anom = 14
    idx = rng.choice(n, n_anom, replace=False)
    actual_grade[idx] += rng.choice([-1, 1], n_anom) * rng.uniform(1.5, 2.5, n_anom)

    return pd.DataFrame({
        "date": dates,
        "loss_rate": np.clip(loss, 1.5, 9.5).round(2),
        "dilution_rate": np.clip(dilution, 2.0, 10.5).round(2),
        "actual_grade": actual_grade.round(2),
        "model_grade": model_grade.round(2),
    })


def generate_blasting(rng: np.random.Generator,
                      n_blasts: int = 420) -> pd.DataFrame:
    """生成爆破效果数据（炸药单耗与块度合格率）。

    合格率与单耗呈倒 U 型关系：单耗过低大块率高，过高则过粉碎，
    最佳区间约在 0.48 ~ 0.62 kg/m³。
    """
    all_dates = pd.date_range(START_DATE, END_DATE, freq="D")
    dates = pd.to_datetime(rng.choice(all_dates, n_blasts))
    rock_types = rng.choice(ROCK_TYPES, n_blasts, p=[0.35, 0.30, 0.20, 0.15])
    consumption = rng.uniform(0.32, 0.80, n_blasts)

    base_frag = 55 + 42 * np.exp(-((consumption - 0.55) ** 2) / (2 * 0.09 ** 2))
    type_effect = np.select(
        [rock_types == "花岗岩", rock_types == "砂岩"],
        [-3.0, 2.0], default=0.0)
    frag = np.clip(base_frag + type_effect + rng.normal(0, 2.5, n_blasts),
                   55, 99)
    volume = rng.uniform(8000, 30000, n_blasts).round(0)

    df = pd.DataFrame({
        "date": dates,
        "bench": rng.choice(BENCHES, n_blasts),
        "rock_type": rock_types,
        "hole_depth_m": rng.uniform(12, 18, n_blasts).round(1),
        "burden_m": rng.uniform(3.5, 5.5, n_blasts).round(1),
        "explosive_kg": (consumption * volume).round(0),
        "rock_volume_m3": volume,
        "explosive_consumption": consumption.round(3),
        "fragmentation_rate": frag.round(1),
    })
    df = df.sort_values("date").reset_index(drop=True)
    df.insert(0, "blast_id", [f"BL-{i + 1:04d}" for i in range(len(df))])
    return df


def generate_cost(rng: np.random.Generator) -> pd.DataFrame:
    """生成月度采矿单位成本构成数据（元/吨）。

    模拟特征：成本逐年温和上涨，运输成本含季节波动，
    2025-07 ~ 2025-12 燃油价格上涨导致运输成本阶跃（触发同比预警）。
    """
    months = pd.date_range("2024-01-01", "2026-08-01", freq="MS")
    n = len(months)
    idx = np.arange(n)
    month_of_year = months.month.to_numpy()

    drilling = 2.45 + 0.05 * idx / 12 + rng.normal(0, 0.06, n)
    blasting = 3.35 + 0.07 * idx / 12 + rng.normal(0, 0.08, n)
    loading = 2.75 + 0.06 * idx / 12 + rng.normal(0, 0.07, n)
    transport = (5.30 + 0.30 * idx / 12
                 + 0.25 * np.sin(2 * np.pi * month_of_year / 12)
                 + rng.normal(0, 0.10, n))
    fuel_step = (months >= "2025-07-01") & (months <= "2025-12-31")
    transport[fuel_step] += 0.55            # 燃油涨价冲击

    return pd.DataFrame({
        "month": months,
        "drilling_cost": drilling.round(2),
        "blasting_cost": blasting.round(2),
        "loading_cost": loading.round(2),
        "transport_cost": transport.round(2),
    })


def main() -> None:
    """生成全部模拟数据并写入 data/ 目录。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)

    generators = {
        "production_daily.csv": generate_production,
        "shovel_efficiency.csv": generate_shovel_efficiency,
        "truck_efficiency.csv": generate_truck_efficiency,
        "loss_dilution.csv": generate_loss_dilution,
        "blasting.csv": generate_blasting,
        "cost_monthly.csv": generate_cost,
    }
    for filename, func in generators.items():
        df = func(rng)
        path = DATA_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"✅ 已生成 {filename}（{len(df):,} 行）")
    print(f"\n全部数据已保存至: {DATA_DIR}")


if __name__ == "__main__":
    main()
