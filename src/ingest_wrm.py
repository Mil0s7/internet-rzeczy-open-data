import os, unicodedata
import requests
from typing import List, Dict
from .store import LIVE, append_history, now_ts

def _ua_get(url: str):
    r = requests.get(url, timeout=20, headers={"User-Agent": "wrm-forecast/1.0"})
    r.raise_for_status()
    return r

def _norm(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)).lower()

# === KONFIG ===
GBFS_STATION_INFO_URL  = os.getenv("GBFS_STATION_INFO_URL", "").strip()
GBFS_STATION_STATUS_URL= os.getenv("GBFS_STATION_STATUS_URL", "").strip()
GBFS_REGIONS_URL       = os.getenv("GBFS_REGIONS_URL", "").strip()
WRM_REGION_NAME        = os.getenv("WRM_REGION_NAME", "Wroclaw").strip()

WRM_CKAN_API = os.getenv("WRM_CKAN_API", "").strip()  # puste = wyłączone
WRM_DATASTORE_RESOURCE_ID = os.getenv("WRM_DATASTORE_RESOURCE_ID", "").strip()

def _fetch_gbfs() -> List[Dict]:
    """Pobierz i złącz station_information + station_status, przefiltruj do Wrocławia."""
    info = _ua_get(GBFS_STATION_INFO_URL).json()
    status = _ua_get(GBFS_STATION_STATUS_URL).json()
    ts = now_ts()

    # mapy pomocnicze
    info_map = {str(s["station_id"]): s for s in info["data"]["stations"]}
    status_map = {str(s["station_id"]): s for s in status["data"]["stations"]}

    # regiony (opcjonalnie)
    region_name_by_id = {}
    if GBFS_REGIONS_URL:
        try:
            regions = _ua_get(GBFS_REGIONS_URL).json()
            region_name_by_id = {str(r["region_id"]): r.get("name","") for r in regions["data"]["regions"]}
        except Exception as e:
            print(f"[ingest_wrm] regions fetch warn: {e}")

    # filtr – dopuszczamy: region == 'Wroclaw' (bez ogonków) LUB nazwa stacji zawiera 'wroclaw/wrocław'
    want = _norm(WRM_REGION_NAME)
    rows: List[Dict] = []
    for sid, meta in info_map.items():
        st = status_map.get(sid)
        if not st:
            continue
        region_id = str(meta.get("region_id") or st.get("region_id") or "")
        region_ok = False
        if region_id and region_id in region_name_by_id:
            region_ok = _norm(region_name_by_id[region_id]).find(want) >= 0

        name = meta.get("name") or meta.get("station_name") or f"Station {sid}"
        name_ok = _norm(name).find("wroclaw") >= 0 or _norm(name).find("wrocław") >= 0

        if not (region_ok or name_ok):
            continue

        racks = meta.get("capacity") or 0
        try:
            racks = int(racks)
        except Exception:
            racks = 0

        rows.append({
            "station_id": sid,
            "station_name": name,
            "lat": float(meta.get("lat")) if meta.get("lat") not in (None, "") else None,
            "lon": float(meta.get("lon")) if meta.get("lon") not in (None, "") else None,
            "racks": racks,
            "bikes": int(st.get("num_bikes_available", 0)),
            "timestamp": ts,
        })
    print(f"[ingest_wrm] GBFS parsed (after Wroclaw filter): {len(rows)} rows")
    return rows

def fetch_live() -> List[Dict]:
    # Priorytet: GBFS, jeśli skonfigurowany
    if GBFS_STATION_INFO_URL and GBFS_STATION_STATUS_URL:
        try:
            return _fetch_gbfs()
        except Exception as e:
            print(f"[ingest_wrm] GBFS error: {e}")

    # (gdybyś kiedyś wrócił do CKAN – tutaj byłby kod CKAN/CSV)
    return []

def update_live_and_history():
    rows = fetch_live()
    for r in rows:
        LIVE[r["station_id"]] = r
        append_history(r)
