# 应用部署说明

露天矿关键生产指标分析看板（Python + Streamlit + Plotly）部署文档。

## 1. 环境要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows / macOS / Linux 均可 |
| Python | 3.10 及以上（开发环境为 3.11） |
| 浏览器 | Chrome / Edge / Firefox / Safari 最新两个大版本 |
| 磁盘空间 | ≥ 200 MB（含依赖） |
| 内存 | ≥ 2 GB |

## 2. 项目结构

```text
open-pit-mine-dashboard/
├── app.py                    # Streamlit 应用入口
├── requirements.txt          # Python 依赖清单
├── pyproject.toml            # 代码规范（ruff）配置
├── data/                     # 模拟数据 CSV（6 份，运行时自动生成/读取）
│   ├── production_daily.csv  #   采剥生产日报
│   ├── shovel_daily.csv      #   电铲效率日报
│   ├── truck_daily.csv       #   矿车效率日报
│   ├── loss_dilution.csv     #   损失贫化与品位记录
│   ├── blasting.csv          #   爆破效果记录
│   └── cost_monthly.csv      #   采矿单位成本月报
├── src/
│   ├── data_generation.py    # 模拟数据生成脚本
│   ├── components/           # 六个功能模块（总览/产量/设备/损失贫化/爆破/成本）
│   └── utils/                # 数据加载、图表样式、通用 UI 组件
├── tests/smoke_test.py       # 无头冒烟测试（无需浏览器）
└── docs/                     # 使用说明等文档
```

## 3. 本地部署

### 3.1 获取源码并创建虚拟环境

```bash
# 进入项目目录
cd open-pit-mine-dashboard

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows PowerShell
```

### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

### 3.3 生成模拟数据（首次必须执行）

```bash
python -m src.data_generation
```

看到如下输出即成功：

```text
已生成 production_daily.csv: 1,359 行
已生成 shovel_daily.csv: 10,872 行
已生成 truck_daily.csv: 16,308 行
已生成 loss_dilution.csv: 174 行
已生成 blasting.csv: 165 行
已生成 cost_monthly.csv: 45 行
```

说明：

- 已存在的 CSV 默认不会重复生成，便于保留自定义修改；
- 加 `--reset` 可强制按内置随机种子重新生成确定性数据；
- 加 `--data-dir 目录路径` 或设置环境变量 `MINE_DATA_DIR` 可更改数据目录。

### 3.4 启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。若未自动打开，请手动访问该地址。

常用启动参数：

```bash
# 指定端口、允许局域网访问
streamlit run app.py --server.port 8502 --server.address 0.0.0.0

# 无头服务器（不尝试打开浏览器）
streamlit run app.py --server.headless true
```

## 4. 常见部署方式

### 4.1 局域网共享

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

同一网络内用户通过 `http://服务器IP:8501` 访问。

### 4.2 Docker 部署（示例）

在项目根目录新建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m src.data_generation
EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.headless=true"]
```

构建并运行：

```bash
docker build -t mine-dashboard .
docker run -p 8501:8501 mine-dashboard
```

### 4.3 云平台部署

Streamlit Community Cloud：将代码推送到 GitHub，在
<https://share.streamlit.io> 新建应用，主文件路径选择 `app.py`，
平台会自动执行 `requirements.txt`。由于数据目录需要初始化，可将
`data/` 一并提交，或在平台启动命令中先执行数据生成。

## 5. 验证与自检

```bash
# 无头冒烟测试：自动依次渲染全部模块并检查异常（无需浏览器）
python tests/smoke_test.py

# 健康检查（应用启动后）
curl http://localhost:8501/_stcore/health   # 返回 ok 即正常
```

## 6. 常见问题排查

| 现象 | 原因与处理 |
| --- | --- |
| 页面提示「数据文件缺失」 | 未生成数据，执行 `python -m src.data_generation` |
| 8501 端口被占用 | 启动时加 `--server.port 其他端口` |
| 图表中文显示为方框 | 系统缺少中文字体；Linux 可安装 `fonts-noto-cjk` |
| 修改代码后页面未更新 | 保存后点击页面右上角「Rerun」，或启用自动重运行 |
| 依赖安装缓慢 | 使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 想恢复初始数据 | 执行 `python -m src.data_generation --reset` |

## 7. 接入真实数据

替换 `data/` 下同名 CSV 即可。请保持字段名、日期格式（`YYYY-MM-DD`）
与单位不变；字段定义见各 CSV 表头及《功能使用说明》附录。
