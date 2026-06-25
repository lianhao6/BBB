from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


DATASET = "nathanlauga/nba-games"
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
REQUIRED_FILES = {
    "games.csv",
    "games_details.csv",
    "players.csv",
    "ranking.csv",
    "teams.csv",
}


def find_kaggle_executable() -> str | None:
    venv_kaggle = Path(sys.executable).with_name("kaggle")
    if venv_kaggle.exists():
        return str(venv_kaggle)
    return shutil.which("kaggle")


def missing_files() -> list[str]:
    return sorted(name for name in REQUIRED_FILES if not (RAW_DIR / name).exists())


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    missing = missing_files()
    if not missing:
        print("All raw CSV files already exist in data/raw.")
        return 0

    kaggle = find_kaggle_executable()
    if not kaggle:
        print("Kaggle CLI was not found.")
        print("Install dependencies and place the required CSV files in data/raw.")
        print("Required files:", ", ".join(sorted(REQUIRED_FILES)))
        return 1

    command = [
        kaggle,
        "datasets",
        "download",
        "-d",
        DATASET,
        "-p",
        str(RAW_DIR),
        "--unzip",
    ]
    print("Downloading Kaggle dataset:", DATASET)
    print("Output directory:", RAW_DIR)

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print("\nKaggle download failed.")
        print("Confirm that ~/.kaggle/kaggle.json exists and has permission 600.")
        print("You can also manually download the dataset and unzip it into data/raw.")
        return 1

    missing = missing_files()
    if missing:
        print("Download finished, but these required files are still missing:")
        for name in missing:
            print("-", name)
        return 1

    print("Dataset is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
