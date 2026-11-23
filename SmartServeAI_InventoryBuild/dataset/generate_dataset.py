"""
Generates a synthetic but realistic food_demand.csv for SmartServe AI.

Run once:
    python dataset/generate_dataset.py

This creates ~2 years of daily demand history for each food item, with
believable effects from day-of-week, holidays, weather, and events, plus
some noise -- so the trained model has real patterns to learn instead of
pure randomness.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FOOD_ITEMS, WEATHER_OPTIONS, EVENT_OPTIONS  # noqa: E402

np.random.seed(42)

START_DATE = datetime(2024, 1, 1)
NUM_DAYS = 730  # 2 years

# Base daily demand per item (units)
BASE_DEMAND = {
    "Veg Thali": 90,
    "Paneer Rice": 70,
    "Biryani": 110,
    "Sandwich": 60,
    "Idli": 80,
    "Masala Dosa": 95,
}

# Weekend / weekday multiplier (Fri-Sun busier for a campus food court)
DOW_MULTIPLIER = {
    0: 1.00,  # Monday
    1: 0.95,  # Tuesday
    2: 0.97,  # Wednesday
    3: 1.00,  # Thursday
    4: 1.15,  # Friday
    5: 1.30,  # Saturday
    6: 1.05,  # Sunday
}

WEATHER_MULTIPLIER = {
    "Normal": 1.00,
    "Hot": 1.10,     # people eat out more / order cold-friendly items
    "Rainy": 0.85,   # footfall drops
    "Cold": 1.05,
}

EVENT_MULTIPLIER = {
    "None": 1.00,
    "College Event": 1.35,
    "Festival": 1.45,
    "Sports Day": 1.25,
    "Exam Season": 0.80,  # fewer people around, lighter meals
}

HOLIDAY_MULTIPLIER = 0.65  # most people off-campus / not eating there

rows = []
current_date = START_DATE

for day_idx in range(NUM_DAYS):
    date = current_date + timedelta(days=day_idx)
    dow = date.weekday()

    # Randomly assign weather / event / holiday per day (shared across items that day)
    weather = np.random.choice(WEATHER_OPTIONS, p=[0.55, 0.20, 0.15, 0.10])
    event = np.random.choice(EVENT_OPTIONS, p=[0.72, 0.10, 0.06, 0.06, 0.06])
    holiday = 1 if np.random.random() < 0.05 else 0

    for item in FOOD_ITEMS:
        base = BASE_DEMAND[item]
        multiplier = (
            DOW_MULTIPLIER[dow]
            * WEATHER_MULTIPLIER[weather]
            * EVENT_MULTIPLIER[event]
            * (HOLIDAY_MULTIPLIER if holiday else 1.0)
        )

        # slow seasonal drift + noise
        seasonal = 1 + 0.05 * np.sin(2 * np.pi * day_idx / 365)
        noise = np.random.normal(1.0, 0.08)

        demand = max(5, round(base * multiplier * seasonal * noise))

        # historical kitchen behavior: usually over-prepared a bit, sometimes short
        prepared_noise = np.random.normal(1.05, 0.07)
        prepared = max(demand, round(demand * prepared_noise))
        sold = min(demand, prepared)

        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "item": item,
                "day_of_week": dow,
                "holiday": holiday,
                "weather": weather,
                "event": event,
                "demand": int(demand),
                "prepared": int(prepared),
                "sold": int(sold),
            }
        )

df = pd.DataFrame(rows)
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "food_demand.csv")
df.to_csv(out_path, index=False)
print(f"Generated {len(df)} rows -> {out_path}")
