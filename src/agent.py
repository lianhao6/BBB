from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from sql_safety import UnsafeSQLError, ensure_limit, validate_readonly_sql


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "db" / "nba_analysis.sqlite"

SAMPLE_QUESTIONS = [
    "每个赛季的比赛数量是多少？",
    "每个赛季主队胜率是多少？",
    "哪些球队场均得分最高？",
    "单场得分最高的 10 名球员是谁？",
    "不同赛季的场均总得分趋势如何变化？",
]


@dataclass
class AgentResult:
    question: str
    sql: str
    data: pd.DataFrame
    analysis: str


def get_database_path() -> Path:
    return Path(os.getenv("NBA_DB_PATH", str(DB_PATH))).resolve()


def require_database() -> Path:
    path = get_database_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Database not found: {path}. Run python src/build_database.py first."
        )
    return path


def create_llm() -> ChatOpenAI:
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not configured. Copy .env.example to .env and fill in a new key."
        )
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0,
    )


def get_schema_text(db_path: Path) -> str:
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
    return db.get_table_info()


def generate_sql(question: str, schema_text: str, llm: ChatOpenAI) -> str:
    system = SystemMessage(
        content=(
            "你是一个严谨的 SQLite 数据分析助手。"
            "根据给定数据库 schema，把用户的中文业务问题转换成一条只读 SQL。"
            "只输出 SQL，不要输出解释、Markdown、代码块或多余文字。"
            "只能使用 SELECT 或 WITH，不允许修改数据库。"
            "字段不存在时要选择 schema 中最接近且真实存在的字段。"
        )
    )
    human = HumanMessage(
        content=(
            f"数据库 schema:\n{schema_text}\n\n"
            f"用户问题:\n{question}\n\n"
            "请生成 SQLite SQL。"
        )
    )
    response = llm.invoke([system, human])
    return validate_readonly_sql(str(response.content))


def execute_sql(sql: str, db_path: Path, limit: int = 100) -> pd.DataFrame:
    limited_sql = ensure_limit(sql, default_limit=limit)
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(limited_sql, conn)


def explain_result(
    question: str, sql: str, data: pd.DataFrame, llm: ChatOpenAI
) -> str:
    if data.empty:
        return "SQL 查询成功，但结果为空。建议检查问题条件、赛季范围或关联字段。"

    sample = data.head(20).to_markdown(index=False)
    system = SystemMessage(
        content=(
            "你是一个篮球数据分析助手。"
            "必须只基于用户问题、SQL 和查询结果进行解释，不能编造查询结果之外的事实。"
            "用中文输出 2 到 4 句简明结论。"
        )
    )
    human = HumanMessage(
        content=(
            f"用户问题:\n{question}\n\n"
            f"SQL:\n{sql}\n\n"
            f"查询结果前 20 行:\n{sample}\n\n"
            "请给出业务分析结论。"
        )
    )
    response = llm.invoke([system, human])
    return str(response.content).strip()


def run_question(question: str, limit: int = 100) -> AgentResult:
    db_path = require_database()
    llm = create_llm()
    schema_text = get_schema_text(db_path)
    sql = generate_sql(question, schema_text, llm)
    data = execute_sql(sql, db_path, limit=limit)
    analysis = explain_result(question, sql, data, llm)
    return AgentResult(question=question, sql=ensure_limit(sql, limit), data=data, analysis=analysis)


def run_sql_direct(sql: str, limit: int = 100) -> pd.DataFrame:
    db_path = require_database()
    safe_sql = ensure_limit(sql, default_limit=limit)
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(safe_sql, conn)


def main() -> int:
    question = " ".join(os.sys.argv[1:]).strip() or SAMPLE_QUESTIONS[0]
    try:
        result = run_question(question)
    except (RuntimeError, FileNotFoundError, UnsafeSQLError) as exc:
        print(f"Error: {exc}")
        return 1

    print("Question:", result.question)
    print("\nSQL:\n", result.sql)
    print("\nResult:")
    print(result.data.to_string(index=False))
    print("\nAnalysis:")
    print(result.analysis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
