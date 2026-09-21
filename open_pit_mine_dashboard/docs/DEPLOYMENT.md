# 部署说明文档

本文档介绍「露天矿关键生产指标分析看板」的部署方式，包括本地部署、
局域网部署、Docker 部署及常见问题处理。

---

## 1. 环境要求

| 项目 | 要求 |
| ---- | ---- |
| 操作系统 | Windows 10+ / macOS 12+ / Linux（Ubuntu 20.04+ 等） |
| Python | 3.10 及以上 |
| 内存 | ≥ 2 GB |
| 磁盘 | ≥ 500 MB |
| 浏览器 | Chrome / Edge / Firefox 最新版本 |

Python 依赖见 `requirements.txt`：

```
streamlit>=1.46.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
```

## 2. 本地部署（推荐）

```bash
# 1. 获取项目代码后进入项目目录
cd open_pit_mine_dashboard

# 2. （可选）创建虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 生成模拟数据（首次运行必须执行）
python data_generator.py

# 5. 启动应用
streamlit run app.py
```

启动成功后，浏览器自动打开 <http://localhost:8501>；
如未自动打开，请手动访问该地址。

## 3. 局域网 / 服务器部署

在服务器上部署供团队访问时：

```bash
streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true
```

- `--server.address 0.0.0.0`：监听所有网卡，允许局域网访问；
- `--server.headless true`：服务器模式，不自动打开浏览器；
- 访问地址：`http://<服务器IP>:8501`。

**后台常驻运行（Linux）：**

```bash
nohup streamlit run app.py --server.address 0.0.0.0 \
    --server.port 8501 --server.headless true > app.log 2>&1 &
```

或使用 `systemd` / `supervisor` 托管进程，实现开机自启与异常重启。

**防火墙**：如无法访问，请放行 8501 端口，例如
`sudo ufw allow 8501/tcp`。

## 4. Docker 部署（可选）

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python data_generator.py

EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.headless=true"]
```

构建并运行：

```bash
docker build -t mine-dashboard .
docker run -d -p 8501:8501 --name mine-dashboard mine-dashboard
```

## 5. Streamlit Community Cloud 部署（可选）

1. 将项目推送至 GitHub 仓库（先本地执行 `python data_generator.py`
   并将 `data/` 一并提交，或在应用启动逻辑中自动生成）；
2. 登录 <https://share.streamlit.io>，选择 **New app**；
3. 选择仓库、分支与入口文件 `app.py`，点击 **Deploy**。

## 6. 数据更新与重新生成

- **重新生成模拟数据**：执行 `python data_generator.py`
  会覆盖 `data/` 目录下全部 CSV（随机种子固定，结果可复现；
  修改脚本中 `RANDOM_SEED` 可生成不同数据）。
- **接入真实数据**：按 `data/` 中 CSV 的字段结构准备真实数据文件，
  替换同名文件后重启应用（或点击页面右上角 ⋮ → Rerun）即可。
  字段说明详见《功能使用说明文档》附录。

## 7. 常见问题（FAQ）

**Q1：启动后页面提示「数据文件缺失」？**
A：首次运行必须先执行 `python data_generator.py` 生成模拟数据。

**Q2：`streamlit` 命令找不到？**
A：使用 `python -m streamlit run app.py`；
或将 Python Scripts 目录加入系统 PATH。

**Q3：页面图表中文显示为方框？**
A：图表在浏览器端渲染，请确认操作系统安装了中文字体
（如微软雅黑、苹方、Noto Sans CJK）。

**Q4：修改代码后页面未更新？**
A：Streamlit 会提示「Source file changed」，点击 **Rerun**；
或设置菜单勾选 **Run on save** 自动重跑。

**Q5：端口被占用？**
A：更换端口启动：`streamlit run app.py --server.port 8502`。

**Q6：数据缓存未刷新？**
A：数据加载使用了 `@st.cache_data` 缓存。替换 CSV 后，
在页面右上角菜单选择 **⋮ → Clear cache**，然后刷新页面。
