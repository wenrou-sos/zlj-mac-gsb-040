"""看板冒烟测试（无需启动浏览器）。

使用 Streamlit 内置 AppTest 框架以无头方式执行 ``app.py``，
逐一切换功能模块并检查是否有未捕获异常。

用法::

    .venv/bin/python tests/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"

MODULE_LABELS = [
    "🏔️ 矿山运行总览",
    "⛏️ 产量分析",
    "🚛 设备效率",
    "🧪 损失贫化",
    "🧨 爆破效果",
    "📊 成本分析",
]


def main() -> int:
    """依次渲染所有模块，返回非零退出码表示存在失败。"""
    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run()
    failures: list[str] = []

    def has_problem() -> bool:
        """同时检查未捕获异常与 st.error 提示。"""
        return bool(at.exception) or bool(at.error)

    def problems() -> list[str]:
        msgs = [f"异常：{e.value}" for e in at.exception]
        msgs += [f"错误提示：{e.value}" for e in at.error]
        return msgs

    if has_problem():
        for msg in problems():
            print(f"[初始渲染] {msg}")
        failures.append("初始渲染")

    # 默认范围为近一年，额外勾选全量数据再验证一遍
    [c for c in at.sidebar.checkbox if "全部数据" in c.label][0].check().run()
    if has_problem():
        for msg in problems():
            print(f"[全量数据范围] {msg}")
        failures.append("全量数据范围")

    # 定位侧边栏中的模块单选控件
    radios = [w for w in at.sidebar.radio if len(w.options) == len(MODULE_LABELS)]
    nav = radios[0] if radios else None
    if nav is None:
        print("未找到模块导航控件")
        return 1

    for label in MODULE_LABELS:
        nav.set_value(label).run()
        if has_problem():
            for msg in problems():
                print(f"[{label}] {msg}")
            failures.append(label)
        else:
            print(f"[{label}] 渲染通过 ✓")

    # 额外验证：切换产量周期为「月」「年」
    if not failures:
        nav.set_value("⛏️ 产量分析").run()
        for period_radio in at.radio:
            if "统计周期" in str(period_radio.label):
                for value in ("月", "年"):
                    period_radio.set_value(value).run()
                    if has_problem():
                        print(f"[产量-{value}] {problems()[0]}")
                        failures.append(f"产量-{value}")
                    else:
                        print(f"[产量-{value}视图] 渲染通过 ✓")
                break

    if failures:
        print(f"\n失败模块：{', '.join(failures)}")
        return 1
    print("\n全部模块冒烟测试通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
