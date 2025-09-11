from pathlib import Path
import pandas as pd
from typing import Dict
from collections import defaultdict
import time

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Pamięć na live i historię
LIVE: Dict[str, dict] = {}       # station_id -> {name, lat, lon, bikes, racks, ts}
HIST = defaultdict(list)         # station_id -> list[dict]

def append_history(row: dict):
    HIST[row["station_id"]].append(row)

def save_history_to_csv():
    for sid, rows in HIST.items():
        if not rows:
            continue
        df = pd.DataFrame(rows)
        out = DATA_DIR / f"history_{sid}.csv"
        if out.exists():
            old = pd.read_csv(out)
            df = pd.concat([old, df], ignore_index=True)
            df.drop_duplicates(subset=["timestamp"], inplace=True)
        df.to_csv(out, index=False)

def load_history_from_csv():
    for p in DATA_DIR.glob("history_*.csv"):
        sid = p.stem.replace("history_", "")
        df = pd.read_csv(p)
        HIST[sid] = df.to_dict("records")

def now_ts() -> int:
    return int(time.time())
