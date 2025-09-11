from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio, json, time
from typing import List, Dict, Optional

from .store import LIVE, HIST, load_history_from_csv, save_history_to_csv
from .ingest_wrm import update_live_and_history
from .forecast import make_forecast

# --- opcjonalny TF-IDF do RAG ---
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    _HAS_SK = True
except Exception:
    _HAS_SK = False

app = FastAPI(title="WRM Forecast API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- MODELE (Pydantic) -----------------
class Station(BaseModel):
    station_id: str = Field(..., example="16341036")
    station_name: str = Field(..., example="Wrocław Stadion, stacja kolejowa")
    lat: Optional[float] = Field(None, example=51.13673)
    lon: Optional[float] = Field(None, example=16.94133)
    racks: int = Field(..., example=12, description="Pojemność stacji (liczba stojaków)")
    bikes: int = Field(..., example=4, description="Aktualnie dostępne rowery")
    timestamp: int = Field(..., example=1757518741)

class ForecastPoint(BaseModel):
    t: int = Field(..., example=1757519941, description="Unix time (sekundy)")
    bikes: float = Field(..., example=4.0)

class ForecastResponse(BaseModel):
    step_minutes: int = Field(..., example=10)
    points: List[ForecastPoint]

class AskResult(BaseModel):
    station_id: str = Field(..., example="544486355")
    station_name: str = Field(..., example="Kamieniec Wrocławski – Szkoła")
    bikes: int = Field(..., example=7)
    lat: Optional[float] = Field(None, example=51.077945)
    lon: Optional[float] = Field(None, example=17.17357)

class AskResponse(BaseModel):
    answer: str = Field(..., example='Najbardziej pasujące stacje do „dworzec”.')
    results: List[AskResult]

# ----------------- STARTUP / POLLER -----------------
@app.on_event("startup")
async def _startup():
    load_history_from_csv()
    asyncio.create_task(poller())  # odświeżaj stan co 60 s

async def poller():
    while True:
        update_live_and_history()
        save_history_to_csv()
        await asyncio.sleep(60)

# ----------------- REST -----------------
@app.get("/stations", response_model=List[Station], tags=["default"])
def stations():
    """Zwraca aktualny stan stacji (po filtrze Wrocław)."""
    return list(LIVE.values())

@app.get("/forecast", response_model=ForecastResponse, tags=["default"])
def forecast(station_id: str, step_minutes: int = 10, horizon_minutes: int = 60):
    """Prognoza liczby rowerów dla wybranej stacji."""
    history = HIST.get(station_id, [])
    # make_forecast powinno zwracać dict w formacie zgodnym z ForecastResponse
    return make_forecast(history, step_minutes=step_minutes, horizon_minutes=horizon_minutes)

def _stations_corpus():
    items = list(LIVE.values())
    texts = [str(i.get("station_name", "")) for i in items]
    return items, texts

@app.get("/ask", response_model=AskResponse, tags=["default"])
def ask(
    q: str = Query(..., min_length=2, description="Zapytanie tekstowe, np. 'Dworzec'"),
    k: int = Query(5, ge=1, le=20),
):
    """
    RAG-lite: wyszukaj stacje pasujące do zapytania (po nazwie),
    zwróć top-k oraz bieżącą liczbę rowerów.
    """
    items, texts = _stations_corpus()
    if not items:
        return {"answer": "Brak danych stacji.", "results": []}

    # TF-IDF gdy dostępny, inaczej proste dopasowanie substring
    try:
        if _HAS_SK:
            vec = TfidfVectorizer().fit(texts)
            X = vec.transform(texts)
            xq = vec.transform([q])
            sims = linear_kernel(xq, X).flatten()
            order = sims.argsort()[::-1]
        else:
            qn = q.lower()
            scores = [(i, texts[i].lower().count(qn)) for i in range(len(texts))]
            order = [i for i, sc in sorted(scores, key=lambda t: t[1], reverse=True)]
    except Exception:
        order = list(range(len(texts)))  # awaryjnie: kolejność dowolna

    top = order[:k]
    results = []
    for idx in top:
        s = items[idx]
        results.append({
            "station_id": s.get("station_id"),
            "station_name": s.get("station_name"),
            "bikes": int(s.get("bikes") or 0),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
        })
    return {"answer": f"Najbardziej pasujące stacje do „{q}”.", "results": results}

# ----------------- WebSocket: prognozy -----------------
@app.websocket("/ws/forecast")
async def ws_forecast(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # prognoza dla wszystkich stacji co 60 s
            payload: Dict[str, dict] = {}
            for sid, rows in HIST.items():
                payload[sid] = make_forecast(rows)
            await ws.send_text(json.dumps({"ts": int(time.time()), "forecasts": payload}))
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        # po cichu kończymy sesję
        pass

# ----------------- WebSocket: snapshot LIVE -----------------
@app.websocket("/ws")
async def ws_live(websocket: WebSocket):
    """Co 30 s wysyła aktualny snapshot wszystkich stacji."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(list(LIVE.values()))
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
