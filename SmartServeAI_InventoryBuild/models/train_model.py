"""
Trains the SmartServe AI demand forecasting model and saves it with Joblib.

Pipeline:
    food_demand.csv -> preprocessing -> feature engineering ->
    one-hot encoding -> RandomForestRegressor -> smartserve_demand_model.pkl

Run once (or whenever the dataset changes):
    python models/train_model.py
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, r2_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATASET_PATH, MODEL_PATH, METRICS_PATH  # noqa: E402

print("Loading dataset...")
df = pd.read_csv(DATASET_PATH, parse_dates=["date"])

# --- Feature engineering ---
df["month"] = df["date"].dt.month
df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

NUMERIC_FEATURES = ["day_of_week", "holiday", "month", "week_of_year"]
CATEGORICAL_FEATURES = ["item", "weather", "event"]

X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
y = df["demand"]

# Time-ordered holdout: train on earlier observations and evaluate on later ones.
df = df.sort_values("date").reset_index(drop=True)
split_idx = max(1, int(len(df) * 0.8))
X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
y = df["demand"]
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ],
    remainder="passthrough",  # numeric features pass through untouched
)

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "regressor",
            RandomForestRegressor(
                n_estimators=80,
                max_depth=12,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=1,
            ),
        ),
    ]
)

print("Training RandomForestRegressor (80 trees, single process)...")
model.fit(X_train, y_train)

# --- Evaluate ---
preds = model.predict(X_test)
mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)
mape = float(np.mean(np.abs((y_test.values - preds) / y_test.values)) * 100)

print(f"MAE:  {mae:.2f} units")
print(f"MAPE: {mape:.2f}%")
print(f"R2:   {r2:.4f}")

# --- Save with Joblib ---
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(model, MODEL_PATH)
print(f"Model saved -> {MODEL_PATH}")

metrics = {
    "mae": round(mae, 2),
    "mape": round(mape, 2),
    "r2": round(r2, 4),
    "n_train": len(X_train),
    "n_test": len(X_test),
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "training_scikit_learn": __import__("sklearn").__version__,
    "training_python": sys.version.split()[0],
    "split_method": "time_ordered_80_20",
}
with open(METRICS_PATH, "w") as f:
    json.dump(metrics, f, indent=2)
print(f"Metrics saved -> {METRICS_PATH}")
