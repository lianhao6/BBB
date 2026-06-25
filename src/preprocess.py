from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REPORTS_DIR = ROOT_DIR / "reports"

REQUIRED_FILES = {
    "games": "games.csv",
    "game_details": "games_details.csv",
    "players": "players.csv",
    "rankings": "ranking.csv",
    "teams": "teams.csv",
}


@dataclass
class ProfileRow:
    table: str
    raw_rows: int
    cleaned_rows: int
    duplicate_rows_removed: int
    missing_cells_before: int
    missing_cells_after: int


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def to_numeric(df: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")


def to_datetime_text(df: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce")
            df[column] = parsed.dt.strftime("%Y-%m-%d")


def minutes_to_seconds(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                minutes = int(float(parts[0]))
                seconds = int(float(parts[1]))
                return float(minutes * 60 + seconds)
            except ValueError:
                return None
    try:
        return float(text) * 60
    except ValueError:
        return None


def load_raw() -> dict[str, pd.DataFrame]:
    missing = [name for name in REQUIRED_FILES.values() if not (RAW_DIR / name).exists()]
    if missing:
        files = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing raw dataset files in {RAW_DIR}: {files}. "
            "Run python src/download_data.py or manually unzip the Kaggle dataset."
        )

    return {
        table: normalize_columns(pd.read_csv(RAW_DIR / filename, low_memory=False))
        for table, filename in REQUIRED_FILES.items()
    }


def profile(table: str, raw: pd.DataFrame, cleaned: pd.DataFrame) -> ProfileRow:
    return ProfileRow(
        table=table,
        raw_rows=len(raw),
        cleaned_rows=len(cleaned),
        duplicate_rows_removed=max(len(raw) - len(cleaned), 0),
        missing_cells_before=int(raw.isna().sum().sum()),
        missing_cells_after=int(cleaned.isna().sum().sum()),
    )


def clean_teams(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    numeric_columns = [
        "league_id",
        "team_id",
        "min_year",
        "max_year",
        "yearfounded",
        "arenacapacity",
    ]
    to_numeric(df, numeric_columns)
    df = df.drop_duplicates(subset=["team_id"], keep="last")
    return df


def clean_games(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    if "game_date_est" in df.columns:
        df = df.rename(columns={"game_date_est": "game_date"})
    to_datetime_text(df, ["game_date"])

    numeric_columns = [
        "game_id",
        "home_team_id",
        "visitor_team_id",
        "season",
        "team_id_home",
        "pts_home",
        "fg_pct_home",
        "ft_pct_home",
        "fg3_pct_home",
        "ast_home",
        "reb_home",
        "team_id_away",
        "pts_away",
        "fg_pct_away",
        "ft_pct_away",
        "fg3_pct_away",
        "ast_away",
        "reb_away",
        "home_team_wins",
    ]
    to_numeric(df, numeric_columns)
    df["total_points"] = df.get("pts_home", 0) + df.get("pts_away", 0)
    df = df.drop_duplicates(subset=["game_id"], keep="last")
    df = df.sort_values(["season", "game_date", "game_id"], na_position="last")
    return df


def clean_players(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    to_numeric(df, ["team_id", "player_id", "season"])
    df = df.drop_duplicates(subset=["player_id", "team_id", "season"], keep="last")
    return df


def clean_rankings(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    if "standingsdate" in df.columns:
        df = df.rename(columns={"standingsdate": "standings_date"})
    to_datetime_text(df, ["standings_date"])
    to_numeric(
        df,
        [
            "team_id",
            "league_id",
            "season_id",
            "g",
            "w",
            "l",
            "w_pct",
            "returntoplay",
        ],
    )
    df = df.drop_duplicates(
        subset=["team_id", "standings_date", "season_id"], keep="last"
    )
    return df


def clean_game_details(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    to_numeric(
        df,
        [
            "game_id",
            "team_id",
            "player_id",
            "fgm",
            "fga",
            "fg_pct",
            "fg3m",
            "fg3a",
            "fg3_pct",
            "ftm",
            "fta",
            "ft_pct",
            "oreb",
            "dreb",
            "reb",
            "ast",
            "stl",
            "blk",
            "to",
            "pf",
            "pts",
            "plus_minus",
        ],
    )
    if "min" in df.columns:
        df["seconds_played"] = df["min"].map(minutes_to_seconds)
    else:
        df["seconds_played"] = None

    df["played"] = (
        df["seconds_played"].fillna(0).gt(0)
        | df["pts"].notna()
        | df["reb"].notna()
        | df["ast"].notna()
    ).astype(int)

    counting_columns = [
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "to",
        "pf",
        "pts",
    ]
    for column in counting_columns:
        if column in df.columns:
            df[column] = df[column].fillna(0)

    df = df.drop_duplicates(subset=["game_id", "player_id"], keep="last")
    return df


def write_profile(rows: list[ProfileRow]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "data_profile.md"
    lines = [
        "# 数据清洗概要",
        "",
        "| 表 | 原始行数 | 清洗后行数 | 删除重复行数 | 清洗前缺失单元格 | 清洗后缺失单元格 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.table} | {row.raw_rows} | {row.cleaned_rows} | "
            f"{row.duplicate_rows_removed} | {row.missing_cells_before} | "
            f"{row.missing_cells_after} |"
        )

    lines.extend(
        [
            "",
            "## 处理说明",
            "",
            "- 字段名统一转为小写，便于 SQL 查询。",
            "- 日期字段转为 `YYYY-MM-DD` 文本格式。",
            "- 分数、命中率、篮板、助攻、抢断、盖帽等字段转为数值类型。",
            "- 球员未上场记录保留，并使用 `played` 字段标记。",
            "- 计数类技术统计缺失值按 0 处理；命中率类字段无法计算时保留为空。",
            "- 按业务主键去除明显重复记录。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote profile: {path}")


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_tables = load_raw()

    cleaners = {
        "teams": clean_teams,
        "games": clean_games,
        "players": clean_players,
        "rankings": clean_rankings,
        "game_details": clean_game_details,
    }

    profiles: list[ProfileRow] = []
    for table, cleaner in cleaners.items():
        raw = raw_tables[table]
        cleaned = cleaner(raw)
        output_name = "player_game_stats.csv" if table == "game_details" else f"{table}.csv"
        output_path = PROCESSED_DIR / output_name
        cleaned.to_csv(output_path, index=False)
        profiles.append(profile(table, raw, cleaned))
        print(f"{table}: {len(raw)} rows -> {len(cleaned)} rows; wrote {output_path}")

    write_profile(profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
