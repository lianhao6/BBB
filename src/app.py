from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from agent import DB_PATH, SAMPLE_QUESTIONS, run_question, run_sql_direct


st.set_page_config(page_title="NBA 数据分析智能体", layout="wide")


CHART_QUERIES = {
    "赛季场均总得分趋势": """
        SELECT season, ROUND(AVG(total_points), 2) AS avg_total_points
        FROM games
        WHERE total_points IS NOT NULL
        GROUP BY season
        ORDER BY season
    """,
    "球队场均得分 Top 10": """
        SELECT t.nickname AS team, ROUND(AVG(team_points), 2) AS avg_points
        FROM (
            SELECT home_team_id AS team_id, pts_home AS team_points FROM games
            UNION ALL
            SELECT visitor_team_id AS team_id, pts_away AS team_points FROM games
        ) s
        JOIN teams t ON t.team_id = s.team_id
        GROUP BY t.team_id, t.nickname
        ORDER BY avg_points DESC
        LIMIT 10
    """,
    "主队胜率随赛季变化": """
        SELECT season, ROUND(AVG(home_team_wins) * 100, 2) AS home_win_rate
        FROM games
        WHERE home_team_wins IS NOT NULL
        GROUP BY season
        ORDER BY season
    """,
}


def database_status(db_path: Path) -> tuple[bool, str]:
    if not db_path.exists():
        return False, f"数据库不存在：{db_path}"
    try:
        with sqlite3.connect(db_path) as conn:
            tables = pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
            )
        return True, "已连接：" + ", ".join(tables["name"].tolist())
    except Exception as exc:  # pragma: no cover - UI guard
        return False, f"数据库检查失败：{exc}"


def render_dashboard_charts() -> None:
    st.subheader("固定业务分析图表")
    chart_tabs = st.tabs(list(CHART_QUERIES.keys()))
    for tab, (title, sql) in zip(chart_tabs, CHART_QUERIES.items()):
        with tab:
            try:
                df = run_sql_direct(sql, limit=200)
            except Exception as exc:
                st.warning(f"无法加载图表数据：{exc}")
                continue

            st.dataframe(df, use_container_width=True)
            if title == "赛季场均总得分趋势":
                fig = px.line(
                    df,
                    x="season",
                    y="avg_total_points",
                    markers=True,
                    labels={"season": "赛季", "avg_total_points": "场均总得分"},
                )
            elif title == "球队场均得分 Top 10":
                fig = px.bar(
                    df,
                    x="avg_points",
                    y="team",
                    orientation="h",
                    labels={"team": "球队", "avg_points": "场均得分"},
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
            else:
                fig = px.line(
                    df,
                    x="season",
                    y="home_win_rate",
                    markers=True,
                    labels={"season": "赛季", "home_win_rate": "主队胜率(%)"},
                )
            st.plotly_chart(fig, use_container_width=True)


def render_dynamic_chart(question: str, df: pd.DataFrame) -> None:
    if df.empty or len(df.columns) < 2:
        return

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        return

    x_column = next((column for column in df.columns if column not in numeric_columns), df.columns[0])
    y_column = numeric_columns[-1]
    lower_question = question.lower()

    st.subheader("本次查询图表")
    if "趋势" in question or "season" in lower_question or "赛季" in question:
        fig = px.line(df, x=df.columns[0], y=y_column, markers=True)
    else:
        fig = px.bar(df, x=x_column, y=y_column)
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.title("NBA 数据分析智能体")
    st.caption("Python + pandas + SQLite + LangChain + DeepSeek API + Streamlit")

    ok, status = database_status(DB_PATH)
    with st.sidebar:
        st.header("项目状态")
        if ok:
            st.success(status)
        else:
            st.error(status)
            st.info("请先运行：python src/preprocess.py 和 python src/build_database.py")

        st.header("示例问题")
        for index, question in enumerate(SAMPLE_QUESTIONS):
            if st.button(question, key=f"sample_{index}", use_container_width=True):
                st.session_state["question"] = question

    if "question" not in st.session_state:
        st.session_state["question"] = SAMPLE_QUESTIONS[0]

    with st.form("question_form"):
        question = st.text_area("输入中文业务问题", value=st.session_state["question"], height=100)
        submitted = st.form_submit_button("运行分析")

    if submitted:
        st.session_state["question"] = question
        with st.spinner("正在生成 SQL、执行查询并分析结果..."):
            try:
                result = run_question(question)
            except Exception as exc:
                st.error(str(exc))
            else:
                st.subheader("生成的 SQL")
                st.code(result.sql, language="sql")

                st.subheader("SQL 查询结果")
                st.dataframe(result.data, use_container_width=True)

                st.subheader("智能体分析结论")
                st.write(result.analysis)

                render_dynamic_chart(question, result.data)

    if ok:
        render_dashboard_charts()


if __name__ == "__main__":
    main()
