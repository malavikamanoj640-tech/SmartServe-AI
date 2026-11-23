from database.db import ensure_database, get_connection
"""
SmartServe AI - F&B Demand Forecasting & Production Optimization
Flask backend: serves the dashboard UI and the forecasting / what-if / analytics APIs.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import urllib.parse
import urllib.request
import subprocess
import sys
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

import config
from database import db

app = Flask(__name__)

# --- Load model + dataset once at startup ---
_model = None
_metrics = None
_history_df = None


def load_model():
    """Load only a model compatible with the installed environment.

    Startup must never block while training. If the current model is absent or
    incompatible, SmartServe starts normally and uses the item-specific
    historical fallback. The model can be rebuilt separately with
    rebuild_model.bat.
    """
    global _model, _metrics
    model_path = config.MODEL_PATH
    _model = None

    if os.path.exists(model_path):
        try:
            import sklearn
            with open(model_path, "rb") as f:
                _model = joblib.load(f)
            print(f"[SmartServe] Demand model loaded: {model_path} (scikit-learn {sklearn.__version__})")
        except Exception as exc:
            _model = None
            print(f"[SmartServe] Current model unavailable: {exc}")
            print("[SmartServe] Starting with item-specific historical fallback.")
    else:
        print("[SmartServe] Current model not found.")
        print("[SmartServe] Starting with item-specific historical fallback.")
        print("[SmartServe] Run rebuild_model.bat once to train a model for this Python environment.")

    if os.path.exists(config.METRICS_PATH):
        try:
            with open(config.METRICS_PATH, encoding="utf-8") as f:
                _metrics = json.load(f)
        except Exception:
            _metrics = {}
    else:
        _metrics = {}

def load_history():
    global _history_df
    if os.path.exists(config.DATASET_PATH):
        _history_df = pd.read_csv(config.DATASET_PATH, parse_dates=["date"])
    else:
        _history_df = pd.DataFrame()


load_model()
load_history()


# ----------------------------------------------------------------------
# Core forecasting helpers
# ----------------------------------------------------------------------

def build_features(date_obj, item, weather, event, holiday):
    return pd.DataFrame(
        [
            {
                "day_of_week": date_obj.weekday(),
                "holiday": 1 if holiday else 0,
                "month": date_obj.month,
                "week_of_year": int(date_obj.isocalendar()[1]),
                "item": item,
                "weather": weather,
                "event": event,
            }
        ]
    )


def predict_demand(date_obj, item, weather, event, holiday):
    if _model is not None:
        features = build_features(date_obj, item, weather, event, holiday)
        pred = _model.predict(features)[0]
        return max(0.0, float(pred))

    # Safe item-specific fallback. Never return one hard-coded value for every
    # menu item: that masks model/data problems and produces misleading plans.
    if _history_df is not None and not _history_df.empty:
        hist = _history_df[_history_df["item"] == item]
        if not hist.empty:
            base = float(hist["demand"].mean())
            adjustment = 0.0
            if date_obj.weekday() >= 5:
                adjustment += 0.08
            if holiday:
                adjustment += 0.10
            if event and event != "None":
                adjustment += {"Festival": 0.18, "College Event": 0.10, "Sports Day": 0.12, "Exam Season": -0.06}.get(event, 0.05)
            if weather == "Hot":
                adjustment += 0.05
            elif weather == "Rainy":
                adjustment -= 0.05
            elif weather == "Cold":
                adjustment += 0.03
            return max(0.0, base * (1 + adjustment))
    return 0.0


def optimize_production(predicted_demand):
    recommended = predicted_demand * (1 + config.PRODUCTION_BUFFER_RATIO)
    return round(recommended)


def compute_waste_risk(predicted_demand, recommended_production):
    if predicted_demand <= 0:
        return "LOW", 0.0
    surplus = recommended_production - predicted_demand
    surplus_ratio = surplus / predicted_demand
    if surplus_ratio < config.WASTE_RISK_LOW_MAX:
        risk = "LOW"
    elif surplus_ratio < config.WASTE_RISK_MEDIUM_MAX:
        risk = "MEDIUM"
    else:
        risk = "HIGH"
    return risk, round(surplus_ratio * 100, 2)


def demand_drivers(date_obj, weather, event, holiday):
    drivers = []
    if date_obj.weekday() >= 4:
        drivers.append({"label": "Weekend demand", "impact": "+12%", "type": "positive"})
    if holiday:
        drivers.append({"label": "Holiday effect", "impact": "+18%", "type": "positive"})
    if event and event != "None":
        event_impacts = {"College Event": "+18%", "Corporate Event": "+28%", "Festival": "+38%", "Sports Day": "+22%", "Exam Season": "−8%"}
        drivers.append({"label": f"{event} effect", "impact": event_impacts.get(event, "+10%"), "type": "positive" if event != "Exam Season" else "negative"})
    if weather == "Hot":
        drivers.append({"label": "Hot weather", "impact": "+7%", "type": "positive"})
    elif weather == "Rainy":
        drivers.append({"label": "Rain impact", "impact": "−8%", "type": "negative"})
    elif weather == "Cold":
        drivers.append({"label": "Cold weather", "impact": "+4%", "type": "positive"})
    if not drivers:
        drivers.append({"label": "Normal operating conditions", "impact": "Baseline", "type": "neutral"})
    return drivers[:4]


def decision_message(result, drivers):
    if result["waste_risk"] == "HIGH":
        return f"Review {result['item']} production before preparation; expected surplus is {result['expected_surplus']} units."
    if result["predicted_demand"] >= 160:
        return f"High-demand signal for {result['item']}: prepare {result['recommended_production']} units and monitor service-period sales."
    if any(d["type"] == "positive" for d in drivers):
        return f"Demand is supported by the selected operating conditions. Prepare about {result['recommended_production']} units."
    return f"Conditions are close to baseline. Prepare about {result['recommended_production']} units and monitor actual sales."


def balance_score(demand, production):
    if demand <= 0:
        return {"waste_risk_pct": 0, "stockout_risk_pct": 0, "score": 100}
    surplus_pct = max(0, (production - demand) / demand * 100)
    waste = min(100, surplus_pct * 4)
    stockout = max(0, min(100, 12 - surplus_pct * 0.5))
    score = max(0, min(100, 100 - waste * 0.35 - stockout * 0.25))
    return {"waste_risk_pct": round(waste, 1), "stockout_risk_pct": round(stockout, 1), "score": round(score, 1)}


def item_intelligence():
    if _history_df is None or _history_df.empty:
        return []
    grouped = _history_df.groupby("item").agg(demand=("demand", "sum"), prepared=("prepared", "sum"), sold=("sold", "sum"))
    recent = _history_df.sort_values("date").groupby("item").tail(28).groupby("item")["demand"].mean()
    older = _history_df.sort_values("date").groupby("item").head(28).groupby("item")["demand"].mean()
    result=[]
    for item,row in grouped.iterrows():
        trend = ((recent.get(item,0)-older.get(item,0))/older.get(item,1)*100) if older.get(item,0) else 0
        waste=max(0,int(row["prepared"]-row["sold"]))
        result.append({"item":item,"demand":int(row["demand"]),"waste":waste,"trend_pct":round(float(trend),1),"trend":"Increasing" if trend>5 else ("Decreasing" if trend<-5 else "Stable")})
    return sorted(result,key=lambda x:x["demand"],reverse=True)


def forecast_confidence(date_obj, item, predicted_demand):
    """Prototype uncertainty band based on historical demand variability.
    This is a planning aid, not a statistically calibrated confidence interval.
    """
    if _history_df is None or _history_df.empty or "demand" not in _history_df.columns:
        margin = max(8, predicted_demand * 0.15)
    else:
        hist = _history_df[_history_df["item"] == item]["demand"].dropna()
        if len(hist) >= 8:
            std = float(hist.std())
            margin = max(5, min(predicted_demand * 0.25, 1.15 * std))
        else:
            margin = max(8, predicted_demand * 0.15)
    low = max(0, round(predicted_demand - margin))
    high = round(predicted_demand + margin)
    confidence = max(55, min(92, round(100 - (margin / max(predicted_demand, 1)) * 100)))
    return {"low": low, "high": high, "confidence_pct": confidence}


def production_plan(date_obj, weather, event, holiday):
    rows = []
    for item in config.FOOD_ITEMS:
        result = forecast_single_day(date_obj, item, weather, event, holiday)
        band = forecast_confidence(date_obj, item, result["predicted_demand"])
        result["confidence"] = band
        rows.append(result)
    total_demand = sum(r["predicted_demand"] for r in rows)
    total_production = sum(r["recommended_production"] for r in rows)
    total_surplus = sum(max(0, r["expected_surplus"]) for r in rows)
    high_risk = sum(1 for r in rows if r["waste_risk"] == "HIGH")
    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "weather": weather, "event": event, "holiday": holiday,
        "items": rows,
        "total_demand": total_demand,
        "total_production": total_production,
        "total_surplus": total_surplus,
        "high_risk_items": high_risk,
    }

def forecast_single_day(date_obj, item, weather, event, holiday):
    demand = predict_demand(date_obj, item, weather, event, holiday)
    production = optimize_production(demand)
    surplus = production - round(demand)
    risk, surplus_pct = compute_waste_risk(demand, production)
    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "day": date_obj.strftime("%a"),
        "item": item,
        "predicted_demand": round(demand),
        "recommended_production": production,
        "expected_surplus": surplus,
        "surplus_pct": surplus_pct,
        "waste_risk": risk,
        "drivers": demand_drivers(date_obj, weather, event, holiday),
        "balance": balance_score(demand, production),
        "confidence": forecast_confidence(date_obj, item, demand),
        "summary": decision_message({"item": item, "predicted_demand": round(demand), "recommended_production": production, "expected_surplus": surplus, "waste_risk": risk}, demand_drivers(date_obj, weather, event, holiday)),
    }




# ----------------------------------------------------------------------
# Real-time weather helpers (Open-Meteo, no API key required)
# ----------------------------------------------------------------------

def weather_code_label(code):
    code = int(code) if code is not None else -1
    if code == 0: return "Clear sky"
    if code in (1, 2, 3): return "Partly cloudy"
    if code in (45, 48): return "Foggy"
    if code in (51, 53, 55, 56, 57): return "Drizzle"
    if code in (61, 63, 65, 66, 67): return "Rain"
    if code in (71, 73, 75, 77): return "Snow"
    if code in (80, 81, 82): return "Rain showers"
    if code in (85, 86): return "Snow showers"
    if code in (95, 96, 99): return "Thunderstorm"
    return "Unknown"


def weather_category(code, temp_max=None, precipitation_probability=None):
    code = int(code) if code is not None else -1
    if code in (51,53,55,56,57,61,63,65,66,67,80,81,82,95,96,99) or (precipitation_probability or 0) >= 60:
        return "Rainy"
    if code in (71,73,75,77,85,86):
        return "Cold"
    if temp_max is not None and temp_max >= 32:
        return "Hot"
    if temp_max is not None and temp_max <= 18:
        return "Cold"
    return "Normal"


def fetch_live_weather(city, date_str):
    if not city:
        raise ValueError("City is required")
    q = urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
    geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + q
    with urllib.request.urlopen(geo_url, timeout=8) as resp:
        geo = json.loads(resp.read().decode("utf-8"))
    results = geo.get("results") or []
    if not results:
        raise ValueError(f"Location '{city}' was not found")
    loc = results[0]
    params = {
        "latitude": loc["latitude"], "longitude": loc["longitude"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
        "current": "temperature_2m,weather_code,precipitation,wind_speed_10m",
        "timezone": "auto", "forecast_days": 7
    }
    weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(weather_url, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if date_str not in dates:
        raise ValueError("Selected date is outside the available live forecast window")
    i = dates.index(date_str)
    code = daily.get("weather_code", [None])[i]
    tmax = daily.get("temperature_2m_max", [None])[i]
    tmin = daily.get("temperature_2m_min", [None])[i]
    rain_prob = daily.get("precipitation_probability_max", [None])[i]
    rain_mm = daily.get("precipitation_sum", [None])[i]
    category = weather_category(code, tmax, rain_prob)
    current = data.get("current", {})
    return {
        "city": loc.get("name", city), "country": loc.get("country", ""),
        "latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
        "timezone": data.get("timezone"), "date": date_str,
        "category": category, "condition": weather_code_label(code),
        "weather_code": code, "temp_max_c": tmax, "temp_min_c": tmin,
        "rain_probability_pct": rain_prob, "rain_mm": rain_mm,
        "current_temp_c": current.get("temperature_2m"),
        "current_condition": weather_code_label(current.get("weather_code")),
        "current_wind_kmh": current.get("wind_speed_10m"),
        "source": "Open-Meteo"
    }


# ----------------------------------------------------------------------
# Page routes
# ----------------------------------------------------------------------


# ------------------------------------------------------------
# MySQL auto-initialization
# Creates smartserve_db and required tables when possible.
# The application still runs in demo/offline mode if MySQL is unavailable.
# ------------------------------------------------------------
SMARTSERVE_DB_STATUS = {"available": False, "message": "Not initialized"}
try:
    _db_ok, _db_message = ensure_database()
    SMARTSERVE_DB_STATUS = {"available": bool(_db_ok), "message": _db_message}
    if _db_ok:
        print(f"[SmartServe] MySQL ready: {_db_message}")
    else:
        print(f"[SmartServe] MySQL unavailable, continuing without it: {_db_message}")
except Exception as _db_exc:
    SMARTSERVE_DB_STATUS = {"available": False, "message": str(_db_exc)}
    print(f"[SmartServe] MySQL unavailable, continuing without it: {_db_exc}")


@app.route("/api/database-status", methods=["GET"])
def api_database_status():
    return jsonify(SMARTSERVE_DB_STATUS)

@app.route("/")
def landing_page():
    return render_template("landing_page.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template(
        "dashboard.html",
        food_items=config.FOOD_ITEMS,
        weather_options=config.WEATHER_OPTIONS,
        event_options=config.EVENT_OPTIONS,
        ollama_model=config.OLLAMA_MODEL,
        daily_default_date=(_history_df["date"].max().strftime("%Y-%m-%d") if _history_df is not None and not _history_df.empty else ""),
    )


# ----------------------------------------------------------------------
# API routes
# ----------------------------------------------------------------------

@app.route("/api/forecast", methods=["POST"])
def api_forecast():
    payload = request.get_json(force=True)
    try:
        date_obj = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        date_obj = datetime.today()

    item = payload.get("item", config.FOOD_ITEMS[0])
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))

    result = forecast_single_day(date_obj, item, weather, event, holiday)

    # best-effort persistence, never blocks the response
    db.save_forecast(
        item, result["date"], result["predicted_demand"],
        result["recommended_production"], result["waste_risk"],
    )

    return jsonify(result)


@app.route("/api/forecast-week", methods=["POST"])
def api_forecast_week():
    payload = request.get_json(force=True)
    try:
        start_date = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        start_date = datetime.today()

    item = payload.get("item", config.FOOD_ITEMS[0])
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))

    days = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        # Only apply the holiday/event flags to the first day; subsequent
        # days default to normal conditions unless explicitly varied.
        day_holiday = holiday if i == 0 else False
        day_event = event if i == 0 else "None"
        days.append(forecast_single_day(d, item, weather, day_event, day_holiday))

    return jsonify({"item": item, "days": days})


@app.route("/api/what-if", methods=["POST"])
def api_what_if():
    payload = request.get_json(force=True)
    try:
        date_obj = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        date_obj = datetime.today()

    item = payload.get("item", config.FOOD_ITEMS[0])
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))
    demand_change_pct = float(payload.get("demand_change_pct", 0))
    delay_hours = float(payload.get("delay_hours", 0))

    baseline_demand = predict_demand(date_obj, item, weather, event, holiday)

    # Apply the simulated demand shift
    scenario_demand = baseline_demand * (1 + demand_change_pct / 100.0)

    # An operational delay reduces effective kitchen output capacity,
    # so we shave a bit off the achievable production for longer delays.
    delay_penalty = min(0.25, delay_hours * 0.05)  # capped at 25% loss
    recommended_production = optimize_production(scenario_demand) * (1 - delay_penalty)
    recommended_production = round(recommended_production)

    risk, surplus_pct = compute_waste_risk(scenario_demand, recommended_production)
    surplus = recommended_production - round(scenario_demand)

    return jsonify({
        "baseline_demand": round(baseline_demand),
        "scenario_demand": round(scenario_demand),
        "recommended_production": recommended_production,
        "expected_surplus": surplus,
        "surplus_pct": surplus_pct,
        "waste_risk": risk,
        "demand_change_pct": demand_change_pct,
        "delay_hours": delay_hours,
    })


@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    if _history_df is None or _history_df.empty:
        return jsonify({"error": "No historical dataset available"}), 404

    df = _history_df
    total_demand = int(df["demand"].sum())
    total_prepared = int(df["prepared"].sum())
    estimated_waste = int(max(0, total_prepared - df["sold"].sum()))
    waste_rate = round((estimated_waste / total_prepared) * 100, 2) if total_prepared else 0.0

    top_waste = (
        (df["prepared"] - df["sold"]).groupby(df["item"]).sum()
        .sort_values(ascending=False)
        .head(5)
    )
    top_waste_items = [
        {"item": item, "waste_units": int(units)} for item, units in top_waste.items()
    ]

    weekly = (
        df.set_index("date")
        .resample("W")[["demand", "prepared"]]
        .sum()
        .tail(12)
    )
    weekly_trend = [
        {
            "week": idx.strftime("%Y-%m-%d"),
            "demand": int(row["demand"]),
            "prepared": int(row["prepared"]),
        }
        for idx, row in weekly.iterrows()
    ]

    demand_vs_production = (
        df.groupby("item")[["demand", "prepared"]].sum().round(0).astype(int)
    )
    demand_vs_production_list = [
        {"item": item, "demand": int(row["demand"]), "production": int(row["prepared"])}
        for item, row in demand_vs_production.iterrows()
    ]

    return jsonify({
        "total_demand": total_demand,
        "total_prepared": total_prepared,
        "estimated_waste": estimated_waste,
        "waste_rate": waste_rate,
        "top_waste_items": top_waste_items,
        "weekly_trend": weekly_trend,
        "demand_vs_production": demand_vs_production_list,
        "model_metrics": _metrics,
    })


@app.route("/api/daily-analysis", methods=["GET"])
def api_daily_analysis():
    """Return a day-level operating analysis from the historical dataset."""
    if _history_df is None or _history_df.empty:
        return jsonify({"error": "No historical dataset available"}), 404

    raw_date = request.args.get("date")
    df = _history_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    try:
        selected_date = pd.to_datetime(raw_date).normalize() if raw_date else df["date"].max()
    except Exception:
        return jsonify({"error": "Invalid date. Use YYYY-MM-DD."}), 400
    day = df[df["date"] == selected_date].copy()

    # The demo dataset is historical, so if a requested date is outside the
    # available range, return a clear message instead of inventing observations.
    if day.empty:
        return jsonify({
            "error": "No historical observations are available for this date.",
            "available_start": df["date"].min().strftime("%Y-%m-%d"),
            "available_end": df["date"].max().strftime("%Y-%m-%d"),
        }), 404

    day["waste"] = (day["prepared"] - day["sold"]).clip(lower=0)
    day["gap"] = day["prepared"] - day["demand"]

    total_demand = int(day["demand"].sum())
    total_prepared = int(day["prepared"].sum())
    total_sold = int(day["sold"].sum())
    waste_units = int(day["waste"].sum())
    waste_rate = round((waste_units / total_prepared) * 100, 2) if total_prepared else 0.0
    sell_through = round((total_sold / total_prepared) * 100, 2) if total_prepared else 0.0

    item_rows = []
    for item, row in day.groupby("item")[["demand", "prepared", "sold", "waste", "gap"]].sum().iterrows():
        prepared = int(row["prepared"])
        sold = int(row["sold"])
        waste = int(row["waste"])
        demand = int(row["demand"])
        item_rows.append({
            "item": item,
            "demand": demand,
            "prepared": prepared,
            "sold": sold,
            "waste": waste,
            "gap": int(row["gap"]),
            "waste_rate": round((waste / prepared) * 100, 2) if prepared else 0.0,
            "sell_through": round((sold / prepared) * 100, 2) if prepared else 0.0,
        })
    item_rows.sort(key=lambda x: x["demand"], reverse=True)

    top_demand = item_rows[0] if item_rows else None
    top_waste = max(item_rows, key=lambda x: x["waste"]) if item_rows else None

    start = selected_date - pd.Timedelta(days=13)
    daily = (
        df[(df["date"] >= start) & (df["date"] <= selected_date)]
        .groupby("date")[["demand", "prepared", "sold"]]
        .sum()
        .sort_index()
    )
    daily_trend = []
    for idx, row in daily.iterrows():
        prepared = int(row["prepared"])
        sold = int(row["sold"])
        daily_trend.append({
            "date": idx.strftime("%Y-%m-%d"),
            "label": idx.strftime("%d %b"),
            "demand": int(row["demand"]),
            "prepared": prepared,
            "sold": sold,
            "waste": max(0, prepared - sold),
        })

    context_cols = [c for c in ["weather", "event", "holiday"] if c in day.columns]
    context = {}
    for col in context_cols:
        values = day[col].dropna().unique().tolist()
        context[col] = values[0] if len(values) == 1 else ", ".join(map(str, values))

    return jsonify({
        "date": selected_date.strftime("%Y-%m-%d"),
        "day_name": selected_date.strftime("%A"),
        "context": context,
        "total_demand": total_demand,
        "total_prepared": total_prepared,
        "total_sold": total_sold,
        "waste_units": waste_units,
        "waste_rate": waste_rate,
        "sell_through": sell_through,
        "avg_item_demand": round(total_demand / len(item_rows), 1) if item_rows else 0,
        "top_demand_item": top_demand["item"] if top_demand else "—",
        "top_demand_units": top_demand["demand"] if top_demand else 0,
        "top_waste_item": top_waste["item"] if top_waste else "—",
        "top_waste_units": top_waste["waste"] if top_waste else 0,
        "overproduction_items": sum(1 for x in item_rows if x["gap"] > 0),
        "underproduction_items": sum(1 for x in item_rows if x["gap"] < 0),
        "item_breakdown": item_rows,
        "daily_trend": daily_trend,
    })


@app.route("/api/insights", methods=["GET"])
def api_insights():
    intelligence = item_intelligence()
    if not intelligence:
        return jsonify({"items": [], "peak_item": None, "summary": "No historical data available."})
    peak = intelligence[0]
    highest_waste = max(intelligence, key=lambda x:x["waste"])
    rising = max(intelligence, key=lambda x:x["trend_pct"])
    return jsonify({
        "items": intelligence,
        "peak_item": peak,
        "highest_waste": highest_waste,
        "rising_item": rising,
        "summary": f"{peak['item']} has the highest historical demand, while {highest_waste['item']} has the largest estimated waste volume."
    })


@app.route("/api/alerts", methods=["GET"])
def api_alerts():
    alerts=[]
    intelligence=item_intelligence()
    if intelligence:
        top=intelligence[0]
        alerts.append({"severity":"HIGH" if top["demand"] > 30000 else "INFO", "title":"Demand leader", "message":f"{top['item']} is the highest-volume menu item in the historical dataset."})
        waste=max(intelligence,key=lambda x:x["waste"])
        alerts.append({"severity":"MEDIUM", "title":"Waste watch", "message":f"{waste['item']} has the highest estimated historical waste ({waste['waste']} units)."})
        rising=max(intelligence,key=lambda x:x["trend_pct"])
        if rising["trend_pct"]>5:
            alerts.append({"severity":"MEDIUM", "title":"Rising demand", "message":f"{rising['item']} shows an estimated {rising['trend_pct']}% recent-vs-early demand increase."})
    alerts.append({"severity":"LOW", "title":"Model status", "message":"Forecast engine is ready. Validate recommendations against real POS data before operational use."})
    return jsonify({"alerts":alerts})



@app.route("/api/production-plan", methods=["POST"])
def api_production_plan():
    payload = request.get_json(force=True)
    try:
        date_obj = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        date_obj = datetime.today()
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))
    return jsonify(production_plan(date_obj, weather, event, holiday))


@app.route("/api/export-plan", methods=["POST"])
def api_export_plan():
    payload = request.get_json(force=True)
    try:
        date_obj = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        date_obj = datetime.today()
    plan = production_plan(date_obj, payload.get("weather", "Normal"), payload.get("event", "None"), bool(payload.get("holiday", False)))
    lines = ["date,item,predicted_demand,recommended_production,expected_surplus,waste_risk,confidence_low,confidence_high,confidence_pct"]
    for r in plan["items"]:
        c=r["confidence"]
        lines.append(f"{plan['date']},{r['item']},{r['predicted_demand']},{r['recommended_production']},{r['expected_surplus']},{r['waste_risk']},{c['low']},{c['high']},{c['confidence_pct']}")
    from flask import Response
    return Response("\n".join(lines), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=smartserve_production_plan_{plan['date']}.csv"})


@app.route("/api/optimization", methods=["POST"])
def api_optimization():
    """Inventory-aware production, stockout and waste/cost simulation.
    Demo inventory values are configurable in config.INVENTORY.
    """
    payload = request.get_json(force=True)
    try:
        date_obj = datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError, TypeError):
        date_obj = datetime.today()
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))
    rows=[]; baseline_waste=ai_waste=waste_saved=savings=planned_shortfall=current_shortfall_total=revenue_risk=0.0
    for item in config.FOOD_ITEMS:
        demand=round(predict_demand(date_obj,item,weather,event,holiday)); base=optimize_production(demand)
        # Standard plan = existing 6% buffer. AI optimization uses a lean 2% buffer.
        ai_target=round(demand * (1 + config.AI_OPTIMIZATION_BUFFER_RATIO))
        info=config.INVENTORY.get(item,{"stock":0,"unit_cost":0,"sell_price":0})
        stock=int(info.get("stock",0)); cost=float(info.get("unit_cost",0)); price=float(info.get("sell_price",0))
        coverage=stock/max(demand,1)
        production=max(0,ai_target-stock); available=stock+production
        surplus=max(0,available-demand)
        short=max(0,demand-available)
        base_surplus=max(0,base-demand)
        # Risk is a pre-action inventory warning. After the recommended production is added,
        # the plan's shortfall should normally be zero.
        if coverage < config.STOCKOUT_COVERAGE_WATCH: sr="HIGH"
        elif coverage < config.STOCKOUT_COVERAGE_SAFE: sr="MEDIUM"
        else: sr="LOW"
        avoided=max(0,base_surplus-surplus); save=avoided*cost
        pre_action_shortfall=max(0,demand-stock); rev=pre_action_shortfall*price
        rows.append({"item":item,"predicted_demand":demand,"base_recommended_production":base,"current_stock":stock,"stock_coverage_pct":round(min(100,coverage*100),1),"production_needed":production,"available_after_plan":available,"expected_ai_surplus":surplus,"baseline_surplus":base_surplus,"waste_avoided_units":avoided,"shortfall_units":short,"pre_action_shortfall_units":pre_action_shortfall,"stockout_risk":sr,"unit_cost":cost,"sell_price":price,"estimated_waste_cost_avoided":round(save,2),"revenue_at_risk":round(rev,2)})
        baseline_waste+=base_surplus; ai_waste+=surplus; waste_saved+=avoided; savings+=save; planned_shortfall+=short; current_shortfall_total+=pre_action_shortfall; revenue_risk+=rev
    high=sum(r["stockout_risk"]=="HIGH" for r in rows)
    reduction_pct=round(waste_saved/baseline_waste*100,1) if baseline_waste else 0
    recommendation=(f"{high} item(s) need replenishment before service. The AI plan covers forecast demand while using a lean {int(config.AI_OPTIMIZATION_BUFFER_RATIO*100)}% buffer." if high else f"The AI plan covers forecast demand with a lean {int(config.AI_OPTIMIZATION_BUFFER_RATIO*100)}% buffer, reducing estimated surplus by {int(waste_saved)} unit(s).")
    return jsonify({"date":date_obj.strftime("%Y-%m-%d"),"weather":weather,"event":event,"holiday":holiday,"items":rows,"total_demand":sum(r["predicted_demand"] for r in rows),"total_stock":sum(r["current_stock"] for r in rows),"total_production_needed":sum(r["production_needed"] for r in rows),"baseline_surplus":int(baseline_waste),"ai_surplus":int(ai_waste),"waste_reduction_units":int(waste_saved),"waste_reduction_pct":reduction_pct,"estimated_savings":round(savings,2),"shortfall_units_after_plan":int(planned_shortfall),"current_shortfall_units":int(current_shortfall_total),"revenue_at_risk":round(revenue_risk,2),"high_stockout_items":high,"recommendation":recommendation,"prototype_note":"Inventory, costs, prices and savings are configurable demonstration estimates. Revenue at risk is the potential sales value of current stock shortfall before the recommended production action; it is not a forecast of actual lost revenue."})


def context_impact(date_obj, item, weather, event, holiday):
    """Estimate how selected context changes the model forecast versus baseline.
    The percentage is an explanatory scenario signal, not causal attribution.
    """
    contextual = predict_demand(date_obj, item, weather, event, holiday)
    baseline = predict_demand(date_obj, item, "Normal", "None", False)
    delta = contextual - baseline
    delta_pct = (delta / baseline * 100) if baseline else 0
    return round(contextual), round(baseline), round(delta_pct, 1)


def anomaly_signal(item, demand):
    if _history_df is None or _history_df.empty:
        return {"status":"UNKNOWN","score":0,"message":"Historical baseline unavailable."}
    hist = _history_df[_history_df["item"] == item]["demand"].dropna()
    if len(hist) < 8:
        return {"status":"UNKNOWN","score":0,"message":"Not enough history for anomaly screening."}
    mean=float(hist.mean()); std=float(hist.std()) or 1.0
    z=abs(demand-mean)/std
    if z >= 2:
        status="HIGH"
    elif z >= 1:
        status="WATCH"
    else:
        status="NORMAL"
    direction="above" if demand >= mean else "below"
    return {"status":status,"score":round(z,2),"message":f"Forecast is {direction} the historical average ({round(mean)} units)."}


@app.route("/api/context-intelligence", methods=["POST"])
def api_context_intelligence():
    payload=request.get_json(force=True)
    try:
        date_obj=datetime.strptime(payload.get("date"), "%Y-%m-%d")
    except (ValueError,TypeError):
        date_obj=datetime.today()
    weather=payload.get("weather","Normal")
    event=payload.get("event","None")
    holiday=bool(payload.get("holiday",False))
    rows=[]
    for item in config.FOOD_ITEMS:
        demand,baseline,delta_pct=context_impact(date_obj,item,weather,event,holiday)
        band=forecast_confidence(date_obj,item,demand)
        anomaly=anomaly_signal(item,demand)
        if delta_pct >= 15:
            action="INCREASE"; action_text=f"Increase {item} preparation; contextual demand is estimated {delta_pct}% above baseline."
        elif delta_pct <= -10:
            action="REDUCE"; action_text=f"Reduce {item} preparation; contextual demand is estimated {abs(delta_pct)}% below baseline."
        elif anomaly["status"] == "HIGH":
            action="MONITOR"; action_text=f"Monitor {item} closely; the forecast is an unusual deviation from historical demand."
        else:
            action="MAINTAIN"; action_text=f"Maintain the planned {item} production level and monitor actual sales."
        rows.append({"item":item,"baseline_demand":baseline,"context_demand":demand,"context_delta_pct":delta_pct,"weather":weather,"event":event,"holiday":holiday,"confidence":band,"anomaly":anomaly,"action":action,"action_text":action_text})
    rising=max(rows,key=lambda r:r["context_delta_pct"]) if rows else None
    falling=min(rows,key=lambda r:r["context_delta_pct"]) if rows else None
    alerts=[]
    if event != "None":
        alerts.append({"severity":"INFO","title":"Event impact active","message":f"{event} is included in the scenario and may shift demand."})
    if holiday:
        alerts.append({"severity":"INFO","title":"Holiday impact active","message":"Holiday context is included in the demand scenario."})
    if weather != "Normal":
        alerts.append({"severity":"WATCH","title":"Weather impact active","message":f"{weather} weather is included in the demand scenario."})
    high_anomalies=[r for r in rows if r["anomaly"]["status"]=="HIGH"]
    if high_anomalies:
        alerts.append({"severity":"HIGH","title":"Unusual demand detected","message":f"{len(high_anomalies)} menu item(s) show a high deviation from historical demand."})
    actions=[r for r in rows if r["action"] in ("INCREASE","REDUCE","MONITOR")]
    summary=(f"{event if event!='None' else 'Normal operations'} with {weather.lower()} weather "
             f"creates the largest estimated context shift for {rising['item']} ({rising['context_delta_pct']:+.1f}%). "
             f"Use the action signals as planning guidance, then confirm against live sales.") if rising else "No context intelligence available."
    return jsonify({"date":date_obj.strftime("%Y-%m-%d"),"weather":weather,"event":event,"holiday":holiday,"items":rows,"largest_increase":rising,"largest_decrease":falling,"alerts":alerts,"actions":actions,"summary":summary,"method_note":"Context impact compares the ML forecast with a Normal-weather, no-event, non-holiday baseline. It is an explanatory scenario signal, not causal attribution or a calibrated real-time weather forecast."})





@app.route("/api/7day-production-plan", methods=["POST"])
def api_7day_production_plan():
    payload = request.get_json(force=True) or {}
    city = str(payload.get("city", "Pune")).strip() or "Pune"
    event = str(payload.get("event", "None")).strip() or "None"
    holiday = int(payload.get("holiday", 0) or 0)

    try:
        weather_result = fetch_live_weather(city, datetime.today().strftime("%Y-%m-%d"))
        # Re-fetch the seven-day weather so the plan always contains all forecast dates.
        geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
            "name": city, "count": 1, "language": "en", "format": "json"
        })
        with urllib.request.urlopen(geo_url, timeout=8) as response:
            geo = json.loads(response.read().decode("utf-8"))
        results = geo.get("results") or []
        if not results:
            raise ValueError(f"Location '{city}' was not found.")
        place = results[0]

        weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": "auto",
            "forecast_days": 7
        })
        with urllib.request.urlopen(weather_url, timeout=8) as response:
            weather = json.loads(response.read().decode("utf-8"))

        daily = weather.get("daily", {})
        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        probs = daily.get("precipitation_probability_max", [])
        rains = daily.get("precipitation_sum", [])

        items = ["Veg Thali", "Paneer Rice", "Biryani", "Sandwich", "Idli", "Masala Dosa"]
        days = []

        for i, date_str in enumerate(dates[:7]):
            code = codes[i] if i < len(codes) else None
            high = highs[i] if i < len(highs) else None
            low = lows[i] if i < len(lows) else None
            prob = probs[i] if i < len(probs) else 0
            rain = rains[i] if i < len(rains) else 0
            category = weather_category(code, high, prob)

            item_rows = []
            total_demand = 0
            total_production = 0
            total_surplus = 0
            high_risk = 0

            for item in items:
                features = pd.DataFrame([{
                    "day_of_week": datetime.strptime(date_str, "%Y-%m-%d").weekday(),
                    "holiday": holiday,
                    "month": datetime.strptime(date_str, "%Y-%m-%d").month,
                    "week_of_year": datetime.strptime(date_str, "%Y-%m-%d").isocalendar().week,
                    "item": item,
                    "weather": category,
                    "event": event
                }])
                predicted = max(0, float(model.predict(features)[0]))
                production = int(round(predicted * (1 + AI_OPTIMIZATION_BUFFER_RATIO)))
                surplus = max(0, production - int(round(predicted)))
                surplus_pct = (surplus / predicted * 100) if predicted else 0
                risk = "HIGH" if surplus_pct >= 18 else ("MEDIUM" if surplus_pct >= 8 else "LOW")

                total_demand += predicted
                total_production += production
                total_surplus += surplus
                if risk == "HIGH":
                    high_risk += 1

                item_rows.append({
                    "item": item,
                    "predicted_demand": round(predicted, 1),
                    "recommended_production": production,
                    "expected_surplus": surplus,
                    "surplus_pct": round(surplus_pct, 1),
                    "waste_risk": risk
                })

            days.append({
                "date": date_str,
                "day": datetime.strptime(date_str, "%Y-%m-%d").strftime("%a"),
                "weather": category,
                "condition": weather_code_label(code),
                "temp_max_c": high,
                "temp_min_c": low,
                "rain_probability_pct": prob,
                "rain_mm": rain,
                "total_demand": round(total_demand, 1),
                "total_production": total_production,
                "expected_surplus": total_surplus,
                "high_risk_items": high_risk,
                "items": item_rows
            })

        return jsonify({
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "event": event,
            "holiday": holiday,
            "days": days,
            "items": items,
            "source": "Open-Meteo + SmartServe AI"
        })
    except Exception as exc:
        return jsonify({"error": str(exc), "fallback_available": True}), 502

@app.route("/api/7day-weather", methods=["POST"])
def api_7day_weather():
    payload = request.get_json(force=True) or {}
    city = str(payload.get("city", "Pune")).strip() or "Pune"

    try:
        # Geocode city using Open-Meteo.
        geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        })
        with urllib.request.urlopen(geo_url, timeout=8) as response:
            geo = json.loads(response.read().decode("utf-8"))

        results = geo.get("results") or []
        if not results:
            raise ValueError(f"Location '{city}' was not found.")

        place = results[0]
        latitude = place["latitude"]
        longitude = place["longitude"]

        weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": "auto",
            "forecast_days": 7
        })

        with urllib.request.urlopen(weather_url, timeout=8) as response:
            weather = json.loads(response.read().decode("utf-8"))

        daily = weather.get("daily", {})
        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        rain_prob = daily.get("precipitation_probability_max", [])
        rain_mm = daily.get("precipitation_sum", [])

        days = []
        for i, date_str in enumerate(dates[:7]):
            code = codes[i] if i < len(codes) else None
            high = tmax[i] if i < len(tmax) else None
            low = tmin[i] if i < len(tmin) else None
            prob = rain_prob[i] if i < len(rain_prob) else 0
            mm = rain_mm[i] if i < len(rain_mm) else 0
            days.append({
                "date": date_str,
                "day": datetime.strptime(date_str, "%Y-%m-%d").strftime("%a"),
                "condition": weather_code_label(code),
                "category": weather_category(code, high, prob),
                "weather_code": code,
                "temp_max_c": high,
                "temp_min_c": low,
                "rain_probability_pct": prob,
                "rain_mm": mm
            })

        return jsonify({
            "city": place.get("name", city),
            "country": place.get("country", ""),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": weather.get("timezone"),
            "days": days,
            "source": "Open-Meteo"
        })
    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "source": "Open-Meteo",
            "fallback_available": True
        }), 502

@app.route("/api/kitchen-control-tower", methods=["POST"])
def api_kitchen_control_tower():
    """End-to-end kitchen workflow: forecast -> ingredients -> inventory -> procurement."""
    payload = request.get_json(force=True) or {}
    city = str(payload.get("city", "Pune")).strip() or "Pune"
    event = str(payload.get("event", "None")).strip() or "None"
    holiday = int(payload.get("holiday", 0) or 0)
    start_text = str(payload.get("date", datetime.today().strftime("%Y-%m-%d")))
    try:
        start_date = datetime.strptime(start_text, "%Y-%m-%d")
    except ValueError:
        start_date = datetime.today()

    # Try live 7-day weather. If unavailable, retain a deterministic Normal-weather fallback.
    weather_days = []
    weather_source = "Scenario fallback"
    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
            "name": city, "count": 1, "language": "en", "format": "json"
        })
        with urllib.request.urlopen(geo_url, timeout=6) as response:
            geo = json.loads(response.read().decode("utf-8"))
        places = geo.get("results") or []
        if not places:
            raise ValueError("Location not found")
        place = places[0]
        weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
            "latitude": place["latitude"], "longitude": place["longitude"],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": "auto", "forecast_days": 7
        })
        with urllib.request.urlopen(weather_url, timeout=6) as response:
            wx = json.loads(response.read().decode("utf-8"))
        daily = wx.get("daily", {})
        for i, date_str in enumerate((daily.get("time") or [])[:7]):
            code = (daily.get("weather_code") or [None] * 7)[i]
            high = (daily.get("temperature_2m_max") or [None] * 7)[i]
            low = (daily.get("temperature_2m_min") or [None] * 7)[i]
            prob = (daily.get("precipitation_probability_max") or [0] * 7)[i]
            rain = (daily.get("precipitation_sum") or [0] * 7)[i]
            weather_days.append({"date": date_str, "category": weather_category(code, high, prob), "condition": weather_code_label(code), "temp_max_c": high, "rain_probability_pct": prob, "rain_mm": rain})
        weather_source = "Open-Meteo live forecast"
    except Exception as exc:
        for i in range(7):
            d = start_date + timedelta(days=i)
            weather_days.append({"date": d.strftime("%Y-%m-%d"), "category": "Normal", "condition": "Scenario fallback", "temp_max_c": None, "rain_probability_pct": 0, "rain_mm": 0})
        weather_source = "Fallback: live weather unavailable"

    # Keep the requested start date aligned with the planning horizon.
    if weather_days and weather_days[0]["date"] != start_date.strftime("%Y-%m-%d"):
        rebuilt = []
        for i in range(7):
            d = start_date + timedelta(days=i)
            existing = next((x for x in weather_days if x["date"] == d.strftime("%Y-%m-%d")), None)
            rebuilt.append(existing or {"date": d.strftime("%Y-%m-%d"), "category": "Normal", "condition": "Scenario fallback", "temp_max_c": None, "rain_probability_pct": 0, "rain_mm": 0})
        weather_days = rebuilt

    ingredient_totals = {name: 0.0 for name in config.INGREDIENT_INVENTORY}
    daily_actions = []
    menu_totals = {item: 0 for item in config.FOOD_ITEMS}

    for day in weather_days[:7]:
        d = datetime.strptime(day["date"], "%Y-%m-%d")
        day_items = []
        for item in config.FOOD_ITEMS:
            demand = predict_demand(d, item, day["category"], event, holiday)
            production = max(0, round(demand * (1 + config.AI_OPTIMIZATION_BUFFER_RATIO)))
            menu_totals[item] += production
            for ingredient, qty_per_portion in config.INGREDIENT_RECIPES.get(item, {}).items():
                ingredient_totals[ingredient] += production * qty_per_portion
            day_items.append({"item": item, "demand": round(demand, 1), "production": production})
        daily_actions.append({"date": day["date"], "day": d.strftime("%a"), "weather": day["category"], "items": day_items})

    ingredient_rows = []
    total_procurement_cost = 0.0
    alerts = 0
    for ingredient, required in ingredient_totals.items():
        info = config.INGREDIENT_INVENTORY[ingredient]
        stock = float(info["stock"])
        shortage = max(0.0, required - stock)
        order = shortage * (1 + config.PROCUREMENT_SAFETY_RATIO) if shortage > 0 else 0.0
        risk = "HIGH" if shortage > 0 else ("WATCH" if required > stock * 0.8 else "OK")
        if shortage > 0:
            alerts += 1
        total_procurement_cost += order * float(info["unit_cost"])
        ingredient_rows.append({
            "ingredient": ingredient, "required": round(required, 3), "available": round(stock, 3),
            "shortage": round(shortage, 3), "recommended_order": round(order, 3),
            "unit": info["unit"], "risk": risk, "estimated_order_cost": round(order * float(info["unit_cost"]), 2)
        })

    ingredient_rows.sort(key=lambda r: (r["risk"] != "HIGH", -r["shortage"]))
    top_actions = []
    for row in ingredient_rows[:6]:
        if row["risk"] == "HIGH":
            top_actions.append({"type": "PROCURE", "title": f"Order {row['ingredient']}", "message": f"Need {row['required']} {row['unit']}; available {row['available']} {row['unit']}. Suggested order: {row['recommended_order']} {row['unit']}."})
        elif row["risk"] == "WATCH":
            top_actions.append({"type": "WATCH", "title": f"Watch {row['ingredient']}", "message": f"Projected 7-day usage reaches {row['required']} {row['unit']} against {row['available']} {row['unit']} in stock."})
    if not top_actions:
        top_actions.append({"type": "PRODUCTION", "title": "Inventory is sufficient", "message": "Current demo ingredient stock covers the projected 7-day production requirement."})

    today = daily_actions[0] if daily_actions else {"date": start_date.strftime("%Y-%m-%d"), "items": []}
    return jsonify({
        "city": city, "event": event, "holiday": holiday, "start_date": start_date.strftime("%Y-%m-%d"),
        "weather_source": weather_source, "days": daily_actions,
        "ingredient_requirements": ingredient_rows, "procurement_alerts": alerts,
        "estimated_procurement_cost": round(total_procurement_cost, 2),
        "today_action": today, "top_actions": top_actions,
        "menu_totals": menu_totals,
        "prototype_note": "Ingredient quantities, inventory and procurement costs are demo assumptions. Replace them with real recipe/BOM and stock data before operational use. Demand predictions are generated by the SmartServe prototype model."
    })

@app.route("/api/realtime-weather", methods=["POST"])
def api_realtime_weather():
    payload = request.get_json(force=True)
    city = str(payload.get("city", "Pune")).strip()
    date_str = payload.get("date") or datetime.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        result = fetch_live_weather(city, date_str)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc), "source": "Open-Meteo", "fallback_available": True}), 502



@app.route("/api/intelligence", methods=["POST"])
def api_intelligence():
    """MCA-level context intelligence: day, weather, seasonal and scenario effects."""
    payload = request.get_json(force=True) or {}
    item = payload.get("item", config.FOOD_ITEMS[0])
    weather = payload.get("weather", "Normal")
    event = payload.get("event", "None")
    holiday = bool(payload.get("holiday", False))
    try:
        selected = datetime.strptime(payload.get("date", datetime.today().strftime("%Y-%m-%d")), "%Y-%m-%d")
    except (ValueError, TypeError):
        selected = datetime.today()

    # Compare the same item across all days of the week.
    day_profile = []
    for dow in range(7):
        d = selected + timedelta(days=(dow - selected.weekday()) % 7)
        value = predict_demand(d, item, weather, event, holiday)
        day_profile.append({"day": d.strftime("%A"), "short": d.strftime("%a"), "demand": round(value), "index": dow})

    # Compare the same date/item under each weather condition.
    weather_profile = []
    normal = predict_demand(selected, item, "Normal", event, holiday)
    for wx in config.WEATHER_OPTIONS:
        value = predict_demand(selected, item, wx, event, holiday)
        impact = ((value - normal) / normal * 100) if normal else 0
        weather_profile.append({"weather": wx, "demand": round(value), "impact_pct": round(impact, 1)})

    # Context contribution is a scenario comparison, deliberately described as
    # decision-support impact rather than causal attribution.
    baseline = predict_demand(selected, item, "Normal", "None", False)
    context_value = predict_demand(selected, item, weather, event, holiday)
    total_impact = ((context_value - baseline) / baseline * 100) if baseline else 0
    components = []
    weather_base = predict_demand(selected, item, weather, "None", False)
    if baseline:
        components.append({"label": "Weather effect", "impact_pct": round((weather_base - baseline) / baseline * 100, 1)})
    event_base = predict_demand(selected, item, weather, event, False)
    if weather_base:
        components.append({"label": "Event effect", "impact_pct": round((event_base - weather_base) / weather_base * 100, 1)})
    holiday_base = predict_demand(selected, item, weather, event, holiday)
    if event_base:
        components.append({"label": "Holiday effect", "impact_pct": round((holiday_base - event_base) / event_base * 100, 1)})
    dow_baseline = predict_demand(selected, item, "Normal", "None", False)
    day_effect = ((dow_baseline - baseline) / baseline * 100) if baseline else 0
    components.append({"label": "Day/temporal effect", "impact_pct": round(day_effect, 1)})

    # 7-day dynamic profile: weekday changes automatically; selected weather is
    # applied so the effect is visible without requiring a live weather service.
    seven = []
    for i in range(7):
        d = selected + timedelta(days=i)
        val = predict_demand(d, item, weather, event if i == 0 else "None", holiday if i == 0 else False)
        seven.append({"date": d.strftime("%Y-%m-%d"), "day": d.strftime("%a"), "demand": round(val)})

    # Historical weekday and seasonal summaries for evidence-based discussion.
    historical_weekday = []
    seasonal = []
    if _history_df is not None and not _history_df.empty:
        h = _history_df[_history_df["item"] == item].copy()
        if not h.empty:
            by_day = h.groupby("day_of_week")["demand"].mean()
            for dow in range(7):
                historical_weekday.append({"day": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][dow], "avg_demand": round(float(by_day.get(dow, 0)), 1)})
            h["month"] = pd.to_datetime(h["date"]).dt.month
            by_month = h.groupby("month")["demand"].mean()
            for month in range(1,13):
                seasonal.append({"month": datetime(2000, month, 1).strftime("%b"), "avg_demand": round(float(by_month.get(month, 0)), 1)})

    production = optimize_production(context_value)
    risk, surplus_pct = compute_waste_risk(context_value, production)
    return jsonify({
        "item": item,
        "date": selected.strftime("%Y-%m-%d"),
        "day_name": selected.strftime("%A"),
        "weather": weather,
        "event": event,
        "holiday": holiday,
        "baseline_demand": round(baseline),
        "context_demand": round(context_value),
        "total_context_impact_pct": round(total_impact, 1),
        "recommended_production": production,
        "waste_risk": risk,
        "surplus_pct": surplus_pct,
        "day_profile": day_profile,
        "weather_profile": weather_profile,
        "components": components,
        "seven_day": seven,
        "historical_weekday": historical_weekday,
        "seasonal": seasonal,
        "model_metrics": _metrics or {},
        "prototype_note": "Context impacts are scenario-based decision-support signals from the trained model and demonstration data; they are not causal estimates."
    })

@app.route("/api/db-status", methods=["GET"])
def api_db_status():
    status = db.check_status()
    return jsonify({
        "ai_model": _model is not None,
        "model_path": config.MODEL_PATH,
        "dataset": _history_df is not None and not _history_df.empty,
        "database": status["connected"],
        "database_reason": status["reason"],
    })



# ----------------------------------------------------------------------
# Persistent operational extensions: inventory, suppliers, finance, Ollama
# ----------------------------------------------------------------------
from extensions import init_store, connection as local_connection, rows as local_rows
init_store()

def _clean_text(value, limit=160):
    value = str(value or '').strip()
    if not value or len(value) > limit:
        raise ValueError(f'Please provide a value between 1 and {limit} characters.')
    return value

@app.route('/api/inventory', methods=['GET','POST'])
def api_inventory():
    if request.method == 'GET':
        with local_connection() as c: return jsonify(local_rows(c, 'SELECT * FROM inventory ORDER BY ingredient'))
    data=request.get_json(silent=True) or {}
    try:
        name=_clean_text(data.get('ingredient'),100); unit=_clean_text(data.get('unit'),20)
        qty=float(data.get('quantity',0)); cost=float(data.get('unit_cost',0))
        if qty < 0 or cost < 0: raise ValueError('Quantity and cost cannot be negative.')
        with local_connection() as c:
            c.execute('INSERT INTO inventory(ingredient,quantity,unit,unit_cost) VALUES(?,?,?,?) ON CONFLICT(ingredient) DO UPDATE SET quantity=excluded.quantity,unit=excluded.unit,unit_cost=excluded.unit_cost,updated_at=CURRENT_TIMESTAMP',(name,qty,unit,cost))
        return jsonify({'ok':True,'message':'Inventory saved.'})
    except (ValueError,TypeError) as e: return jsonify({'error':str(e)}),400

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
def api_inventory_delete(item_id):
    with local_connection() as c: cur=c.execute('DELETE FROM inventory WHERE id=?',(item_id,))
    return (jsonify({'ok':True}) if cur.rowcount else (jsonify({'error':'Ingredient not found'}),404))

@app.route('/api/suppliers', methods=['GET','POST'])
def api_suppliers():
    if request.method=='GET':
        with local_connection() as c: return jsonify(local_rows(c,'SELECT * FROM suppliers ORDER BY name'))
    d=request.get_json(silent=True) or {}
    try:
        name=_clean_text(d.get('name'),120); contact=str(d.get('contact','')).strip()[:60]; email=str(d.get('email','')).strip()[:160]; category=str(d.get('category','')).strip()[:100]
        with local_connection() as c: c.execute('INSERT INTO suppliers(name,contact,email,category) VALUES(?,?,?,?)',(name,contact,email,category))
        return jsonify({'ok':True})
    except ValueError as e: return jsonify({'error':str(e)}),400

@app.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def api_supplier_delete(supplier_id):
    with local_connection() as c: cur=c.execute('DELETE FROM suppliers WHERE id=?',(supplier_id,))
    return (jsonify({'ok':True}) if cur.rowcount else (jsonify({'error':'Supplier not found'}),404))

@app.route('/api/purchase-orders', methods=['GET','POST'])
def api_purchase_orders():
    if request.method=='GET':
        with local_connection() as c: return jsonify(local_rows(c,'SELECT p.*,s.name AS supplier_name FROM purchase_orders p LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.id DESC'))
    d=request.get_json(silent=True) or {}
    try:
        supplier=int(d.get('supplier_id')); ingredient=_clean_text(d.get('ingredient'),100); qty=float(d.get('quantity')); price=float(d.get('unit_price'))
        if qty<=0 or price<0: raise ValueError('Quantity must be positive and price cannot be negative.')
        with local_connection() as c:
            if not c.execute('SELECT id FROM suppliers WHERE id=?',(supplier,)).fetchone(): raise ValueError('Select a valid supplier first.')
            c.execute('INSERT INTO purchase_orders(supplier_id,ingredient,quantity,unit_price,total) VALUES(?,?,?,?,?)',(supplier,ingredient,qty,price,round(qty*price,2)))
        return jsonify({'ok':True,'message':'Purchase order draft saved.'})
    except (ValueError,TypeError) as e: return jsonify({'error':str(e)}),400

@app.route('/api/finance', methods=['GET','POST'])
def api_finance():
    if request.method=='GET':
        with local_connection() as c:
            data=local_rows(c,'SELECT * FROM sales_records ORDER BY sale_date DESC,id DESC LIMIT 250')
            totals=c.execute('SELECT COALESCE(SUM(revenue),0) revenue,COALESCE(SUM(cost),0) cost,COALESCE(SUM(gross_profit),0) gross_profit,COALESCE(SUM(quantity),0) units FROM sales_records').fetchone()
        return jsonify({'records':data,'totals':dict(totals)})
    d=request.get_json(silent=True) or {}
    try:
        item=_clean_text(d.get('item'),100); qty=int(d.get('quantity')); price=float(d.get('selling_price')); cost=float(d.get('unit_cost')); dt=str(d.get('sale_date') or date.today().isoformat())
        from datetime import datetime as _dt
        _dt.strptime(dt,'%Y-%m-%d')
        if qty<0 or price<0 or cost<0: raise ValueError('Quantity and prices cannot be negative.')
        revenue=qty*price; total_cost=qty*cost
        with local_connection() as c: c.execute('INSERT INTO sales_records(sale_date,item,quantity,selling_price,unit_cost,revenue,cost,gross_profit) VALUES(?,?,?,?,?,?,?,?)',(dt,item,qty,price,cost,revenue,total_cost,revenue-total_cost))
        return jsonify({'ok':True})
    except (ValueError,TypeError) as e: return jsonify({'error':str(e)}),400

@app.route('/api/waste-analysis', methods=['GET'])
def api_waste_analysis():
    item=request.args.get('item','')
    if _history_df is None or _history_df.empty: return jsonify({'error':'Historical dataset is unavailable.'}),503
    h=_history_df[_history_df['item']==item] if item else _history_df
    prepared=float(h['prepared'].sum()) if 'prepared' in h else 0
    sold=float(h['sold'].sum()) if 'sold' in h else 0
    waste=max(0,prepared-sold); rate=(waste/prepared*100) if prepared else 0
    return jsonify({'item':item or 'All menu items','prepared':int(prepared),'sold':int(sold),'waste':int(waste),'waste_rate':round(rate,2),'observations':int(len(h)),'source':'Historical demonstration dataset','note':'Waste is estimated as prepared minus sold; it is not a direct food-waste measurement.'})

@app.route('/api/assistant', methods=['POST'])
def api_assistant():
    d=request.get_json(silent=True) or {}; question=str(d.get('question','')).strip(); model=str(d.get('model') or config.OLLAMA_MODEL).strip() or config.OLLAMA_MODEL
    if not question: return jsonify({'error':'Enter a question.'}),400
    if len(question)>3000: return jsonify({'error':'Question is too long (maximum 3000 characters).'}),400
    prompt=('You are SmartServe AI, an assistant for a restaurant demand forecasting and production planning project. '
            'Explain clearly and do not invent live business data. If data is not supplied, say so.\n\nUser: '+question)
    body=json.dumps({'model':model,'prompt':prompt,'stream':False}).encode()
    req=urllib.request.Request(os.environ.get('OLLAMA_URL','http://localhost:11434').rstrip('/')+'/api/generate',data=body,headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=90) as response: result=json.loads(response.read().decode())
        return jsonify({'answer':result.get('response',''),'model':model,'provider':'Ollama'})
    except Exception as e:
        return jsonify({'error':'Could not reach Ollama. Start Ollama, run `ollama pull '+model+'`, and verify OLLAMA_URL. Details: '+str(e)[:240]}),503

@app.route('/api/model/metrics', methods=['GET'])
def api_model_metrics():
    metrics=_metrics if isinstance(_metrics,dict) else {}
    has_metrics=bool(metrics) and any(k in metrics for k in ('mae','MAE','r2','r2_score','R2','rmse','RMSE'))
    return jsonify({'model_loaded':_model is not None,'dataset_loaded':_history_df is not None and not _history_df.empty,'model_path':os.path.basename(config.MODEL_PATH),'metrics_available':has_metrics,'metrics':metrics if has_metrics else {},'status':'Evaluation metrics loaded' if has_metrics else 'Evaluation metrics have not been generated or saved for this model.','evaluation_note':'Metrics are shown only when present in models/metrics.json.'})

if __name__ == "__main__":
    # debug=False so this also runs cleanly under process supervisors / containers
    # where the debug reloader's file-watcher can misbehave. Set debug=True locally
    # if you want auto-reload during development.
    app.run(debug=False, port=5000)
