from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DB_DIR = ROOT_DIR / "db"
DB_PATH = DB_DIR / "nba_analysis.sqlite"
REPORTS_DIR = ROOT_DIR / "reports"


TABLE_FILES = {
    "teams": "teams.csv",
    "games": "games.csv",
    "players": "players.csv",
    "rankings": "rankings.csv",
    "player_game_stats": "player_game_stats.csv",
}


DDL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS player_game_stats;
DROP TABLE IF EXISTS rankings;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS teams;

CREATE TABLE teams (
    league_id INTEGER,
    team_id INTEGER PRIMARY KEY,
    min_year INTEGER,
    max_year INTEGER,
    abbreviation TEXT,
    nickname TEXT,
    yearfounded INTEGER,
    city TEXT,
    arena TEXT,
    arenacapacity REAL,
    owner TEXT,
    generalmanager TEXT,
    headcoach TEXT,
    dleagueaffiliation TEXT
);

CREATE TABLE games (
    game_date TEXT,
    game_id INTEGER PRIMARY KEY,
    game_status_text TEXT,
    home_team_id INTEGER,
    visitor_team_id INTEGER,
    season INTEGER,
    team_id_home INTEGER,
    pts_home REAL,
    fg_pct_home REAL,
    ft_pct_home REAL,
    fg3_pct_home REAL,
    ast_home REAL,
    reb_home REAL,
    team_id_away INTEGER,
    pts_away REAL,
    fg_pct_away REAL,
    ft_pct_away REAL,
    fg3_pct_away REAL,
    ast_away REAL,
    reb_away REAL,
    home_team_wins INTEGER,
    total_points REAL,
    FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY(visitor_team_id) REFERENCES teams(team_id)
);

CREATE TABLE players (
    player_name TEXT,
    team_id INTEGER,
    player_id INTEGER,
    season INTEGER,
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
);

CREATE TABLE rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER,
    league_id INTEGER,
    season_id INTEGER,
    standings_date TEXT,
    conference TEXT,
    team TEXT,
    g INTEGER,
    w INTEGER,
    l INTEGER,
    w_pct REAL,
    home_record TEXT,
    road_record TEXT,
    returntoplay REAL,
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
);

CREATE TABLE player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    team_id INTEGER,
    team_abbreviation TEXT,
    team_city TEXT,
    player_id INTEGER,
    player_name TEXT,
    nickname TEXT,
    start_position TEXT,
    comment TEXT,
    min TEXT,
    seconds_played REAL,
    played INTEGER,
    fgm REAL,
    fga REAL,
    fg_pct REAL,
    fg3m REAL,
    fg3a REAL,
    fg3_pct REAL,
    ftm REAL,
    fta REAL,
    ft_pct REAL,
    oreb REAL,
    dreb REAL,
    reb REAL,
    ast REAL,
    stl REAL,
    blk REAL,
    "to" REAL,
    pf REAL,
    pts REAL,
    plus_minus REAL,
    FOREIGN KEY(game_id) REFERENCES games(game_id),
    FOREIGN KEY(team_id) REFERENCES teams(team_id)
);

CREATE UNIQUE INDEX idx_player_game_unique
ON player_game_stats(game_id, player_id);

CREATE INDEX idx_games_season ON games(season);
CREATE INDEX idx_games_game_date ON games(game_date);
CREATE INDEX idx_games_home_team ON games(home_team_id);
CREATE INDEX idx_games_visitor_team ON games(visitor_team_id);
CREATE INDEX idx_player_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id);
CREATE INDEX idx_player_stats_team ON player_game_stats(team_id);
CREATE INDEX idx_rankings_team ON rankings(team_id);
CREATE INDEX idx_rankings_date ON rankings(standings_date);
"""


TABLE_COLUMNS = {
    "teams": [
        "league_id",
        "team_id",
        "min_year",
        "max_year",
        "abbreviation",
        "nickname",
        "yearfounded",
        "city",
        "arena",
        "arenacapacity",
        "owner",
        "generalmanager",
        "headcoach",
        "dleagueaffiliation",
    ],
    "games": [
        "game_date",
        "game_id",
        "game_status_text",
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
        "total_points",
    ],
    "players": ["player_name", "team_id", "player_id", "season"],
    "rankings": [
        "team_id",
        "league_id",
        "season_id",
        "standings_date",
        "conference",
        "team",
        "g",
        "w",
        "l",
        "w_pct",
        "home_record",
        "road_record",
        "returntoplay",
    ],
    "player_game_stats": [
        "game_id",
        "team_id",
        "team_abbreviation",
        "team_city",
        "player_id",
        "player_name",
        "nickname",
        "start_position",
        "comment",
        "min",
        "seconds_played",
        "played",
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
}


VERIFICATION_QUERIES = {
    "table_counts": """
        SELECT 'teams' AS table_name, COUNT(*) AS row_count FROM teams
        UNION ALL SELECT 'games', COUNT(*) FROM games
        UNION ALL SELECT 'players', COUNT(*) FROM players
        UNION ALL SELECT 'rankings', COUNT(*) FROM rankings
        UNION ALL SELECT 'player_game_stats', COUNT(*) FROM player_game_stats;
    """,
    "season_distribution": """
        SELECT season, COUNT(*) AS games
        FROM games
        GROUP BY season
        ORDER BY season
        LIMIT 20;
    """,
    "top_team_avg_points": """
        SELECT t.nickname AS team, ROUND(AVG(team_points), 2) AS avg_points
        FROM (
            SELECT home_team_id AS team_id, pts_home AS team_points FROM games
            UNION ALL
            SELECT visitor_team_id AS team_id, pts_away AS team_points FROM games
        ) s
        JOIN teams t ON t.team_id = s.team_id
        GROUP BY t.team_id, t.nickname
        ORDER BY avg_points DESC
        LIMIT 10;
    """,
}


def read_processed(table: str) -> pd.DataFrame:
    path = PROCESSED_DIR / TABLE_FILES[table]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing processed file: {path}. Run python src/preprocess.py first."
        )
    df = pd.read_csv(path, low_memory=False)
    missing = [column for column in TABLE_COLUMNS[table] if column not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    return df[TABLE_COLUMNS[table]]


def build_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(DDL)
        for table in ["teams", "games", "players", "rankings", "player_game_stats"]:
            df = read_processed(table)
            df.to_sql(table, conn, if_exists="append", index=False)
            print(f"Inserted {len(df)} rows into {table}.")
        conn.commit()


def run_verification() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "verification_queries.md"
    lines = ["# 数据库验证查询", ""]
    with sqlite3.connect(DB_PATH) as conn:
        for name, sql in VERIFICATION_QUERIES.items():
            df = pd.read_sql_query(sql, conn)
            print(f"\n[{name}]")
            print(df.to_string(index=False))
            lines.extend([f"## {name}", "", "```sql", sql.strip(), "```", ""])
            lines.extend([df.to_markdown(index=False), ""])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote verification report: {output_path}")


def main() -> int:
    build_database()
    run_verification()
    print(f"\nDatabase ready: {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
