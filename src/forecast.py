import numpy as np
import pandas as pd
from typing import List, Dict

def seasonal_naive(history: pd.Series, period: int, horizon: int) -> np.ndarray:
    """Jeśli mamy wartość sprzed 'period', używamy jej; inaczej fallback do średniej z ostatnich k punktów."""
    y = history.values
    fcst = []
    for h in range(1, horizon + 1):
        if len(y) >= period:
            fcst.append(y[-period + (h - 1) % period])
        else:
            fcst.append(y[-min(len(y), 3):].mean() if len(y) else 0.0)
    return np.array(fcst)

def moving_average(history: pd.Series, window: int) -> float:
    if len(history) == 0:
        return 0.0
    return history.tail(window).mean()

def make_forecast(history_rows: List[Dict], step_minutes: int = 10, horizon_minutes: int = 60) -> Dict:
    if not history_rows:
        return {"step_minutes": step_minutes, "points": []}
    df = pd.DataFrame(history_rows).sort_values("timestamp")
    y = df["bikes"]
    period = int(24 * 60 / step_minutes)  # pełna doba w krokach
    horizon = int(horizon_minutes / step_minutes)
    fcst = seasonal_naive(y, period=period, horizon=horizon)
    last_ts = int(df["timestamp"].iloc[-1])
    points = []
    for i, val in enumerate(fcst, start=1):
        points.append({"t": last_ts + i * step_minutes * 60, "bikes": float(val)})
    return {"step_minutes": step_minutes, "points": points}
