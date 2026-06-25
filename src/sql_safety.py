from __future__ import annotations

import re


DISALLOWED_KEYWORDS = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
    "vacuum",
}


class UnsafeSQLError(ValueError):
    pass


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(r"^\s*sql\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def remove_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def validate_readonly_sql(sql: str) -> str:
    cleaned = remove_sql_comments(strip_code_fence(sql))
    if not cleaned:
        raise UnsafeSQLError("SQL is empty.")

    without_trailing_semicolon = cleaned.rstrip().rstrip(";").strip()
    if ";" in without_trailing_semicolon:
        raise UnsafeSQLError("Only one SQL statement is allowed.")

    lowered = without_trailing_semicolon.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise UnsafeSQLError("Only SELECT or WITH queries are allowed.")

    tokens = set(re.findall(r"\b[a-z_]+\b", lowered))
    blocked = sorted(tokens & DISALLOWED_KEYWORDS)
    if blocked:
        raise UnsafeSQLError(f"Disallowed SQL keyword(s): {', '.join(blocked)}")

    return without_trailing_semicolon


def ensure_limit(sql: str, default_limit: int = 100) -> str:
    safe_sql = validate_readonly_sql(sql)
    lowered = safe_sql.lower()
    if re.search(r"\blimit\s+\d+\b", lowered):
        return safe_sql
    return f"{safe_sql}\nLIMIT {default_limit}"
