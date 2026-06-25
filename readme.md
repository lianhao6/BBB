# 实验7 NBA 数据分析智能体

本项目用于完成《数据库系统原理》实验7：数据分析智能体的设计与实现。系统使用 NBA 公开比赛数据集，完成数据获取、pandas 清洗、SQLite 建库、LangChain + DeepSeek API 自然语言查询、SQL 执行、结果解释和 Streamlit 可视化展示。

## 技术栈

- Python 3.10
- pandas
- SQLite
- SQLAlchemy
- LangChain
- DeepSeek API
- Streamlit
- Plotly

## 目录结构

```text
.
├── data/
│   ├── raw/            # Kaggle 原始 CSV
│   └── processed/      # 清洗后的 CSV
├── db/                 # SQLite 数据库
├── reports/            # 报告辅助材料、截图、版本说明
├── src/
│   ├── download_data.py
│   ├── preprocess.py
│   ├── build_database.py
│   ├── sql_safety.py
│   ├── agent.py
│   └── app.py
├── .env.example
├── requirements.txt
└── 实验7-数据分析智能体.pdf
```

## 环境配置

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

复制配置模板，并填写新的 DeepSeek API Key：

```bash
cp .env.example .env
```

`.env` 示例：

```bash
DEEPSEEK_API_KEY=你的新key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

注意：不要把真实 `.env` 或 API Key 提交到 Git。

## 数据获取

默认数据集是 Kaggle `nathanlauga/nba-games`。

如果已经配置 Kaggle API Token，可运行：

```bash
python src/download_data.py
```

也可以手动从 Kaggle 下载并解压，把以下文件放入 `data/raw/`：

- `games.csv`
- `games_details.csv`
- `players.csv`
- `ranking.csv`
- `teams.csv`

## 运行流程

清洗数据：

```bash
python src/preprocess.py
```

构建数据库：

```bash
python src/build_database.py
```

启动 Streamlit：

```bash
streamlit run src/app.py
```

## 内置分析问题

- 每个赛季的比赛数量是多少？
- 每个赛季主队胜率是多少？
- 哪些球队场均得分最高？
- 单场得分最高的 10 名球员是谁？
- 不同赛季的场均总得分趋势如何变化？

## 提交注意

- 提交源码、`requirements.txt`、`.env.example`、实验报告、截图、数据集或数据获取说明、SQLite 数据库。
- 不提交真实 `.env` 和真实 API Key。
- 如果原始数据或数据库文件过大，可提交获取与构建脚本，并在报告中说明复现步骤。
