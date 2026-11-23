"""
SmartServe AI - Configuration
Keep MySQL optional: the app must run fully (ML + dashboard) with zero DB setup.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Paths ---
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "food_demand.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "smartserve_demand_model.pkl")
METRICS_PATH = os.path.join(BASE_DIR, "models", "metrics.json")
MODEL_TRAINING_VERSION = "1.9.0"

# --- Food items available in the demo dataset ---
FOOD_ITEMS = [
    "Veg Thali",
    "Paneer Rice",
    "Biryani",
    "Sandwich",
    "Idli",
    "Masala Dosa",
]

WEATHER_OPTIONS = ["Normal", "Hot", "Rainy", "Cold"]
EVENT_OPTIONS = ["None", "College Event", "Festival", "Sports Day", "Exam Season"]

# --- Demo inventory + unit economics (editable prototype values) ---
INVENTORY = {
    "Veg Thali": {"stock": 28, "unit_cost": 55, "sell_price": 120},
    "Paneer Rice": {"stock": 22, "unit_cost": 48, "sell_price": 110},
    "Biryani": {"stock": 35, "unit_cost": 65, "sell_price": 150},
    "Sandwich": {"stock": 30, "unit_cost": 30, "sell_price": 80},
    "Idli": {"stock": 42, "unit_cost": 18, "sell_price": 50},
    "Masala Dosa": {"stock": 26, "unit_cost": 32, "sell_price": 90},
}
STOCKOUT_COVERAGE_WATCH = 0.35
STOCKOUT_COVERAGE_SAFE = 0.70

# --- Production optimization ---
# Safety buffer added on top of the raw ML demand prediction.
PRODUCTION_BUFFER_RATIO = 0.06  # 6% for standard production planning
AI_OPTIMIZATION_BUFFER_RATIO = 0.02  # 2% lean buffer for waste-aware optimization

# --- Waste risk thresholds (prototype heuristics, not scientifically validated) ---
WASTE_RISK_LOW_MAX = 0.08     # < 8%  -> LOW
WASTE_RISK_MEDIUM_MAX = 0.18  # 8-18% -> MEDIUM
                              # >= 18% -> HIGH

# --- MySQL (fully optional) ---
MYSQL_CONFIG = {
    "host": os.environ.get("SMARTSERVE_DB_HOST", "localhost"),
    "user": os.environ.get("SMARTSERVE_DB_USER", "root"),
    "password": os.environ.get("SMARTSERVE_DB_PASSWORD", ""),
    "database": os.environ.get("SMARTSERVE_DB_NAME", "smartserve_db"),
}

# --- Demo ingredient inventory + recipe mapping ---
# These are illustrative prototype values. Replace with real kitchen master data in deployment.
INGREDIENT_INVENTORY = {
    "Rice": {"stock": 25.0, "unit": "kg", "unit_cost": 55.0},
    "Paneer": {"stock": 8.0, "unit": "kg", "unit_cost": 280.0},
    "Chicken": {"stock": 12.0, "unit": "kg", "unit_cost": 220.0},
    "Potato": {"stock": 15.0, "unit": "kg", "unit_cost": 35.0},
    "Onion": {"stock": 10.0, "unit": "kg", "unit_cost": 32.0},
    "Dal": {"stock": 8.0, "unit": "kg", "unit_cost": 120.0},
    "Vegetables": {"stock": 14.0, "unit": "kg", "unit_cost": 70.0},
    "Roti Flour": {"stock": 10.0, "unit": "kg", "unit_cost": 55.0},
    "Bread": {"stock": 10.0, "unit": "pack", "unit_cost": 45.0},
    "Cheese": {"stock": 3.0, "unit": "kg", "unit_cost": 360.0},
    "Urad Dal": {"stock": 7.0, "unit": "kg", "unit_cost": 145.0},
    "Oil": {"stock": 12.0, "unit": "L", "unit_cost": 140.0},
    "Spices": {"stock": 3.0, "unit": "kg", "unit_cost": 260.0},
}

# Quantity consumed per prepared portion. Prototype assumptions for demonstration.
INGREDIENT_RECIPES = {
    "Veg Thali": {"Rice": 0.10, "Dal": 0.05, "Vegetables": 0.08, "Roti Flour": 0.06, "Oil": 0.012, "Spices": 0.006},
    "Paneer Rice": {"Rice": 0.10, "Paneer": 0.06, "Vegetables": 0.04, "Onion": 0.025, "Oil": 0.012, "Spices": 0.005},
    "Biryani": {"Rice": 0.10, "Chicken": 0.15, "Onion": 0.04, "Oil": 0.018, "Spices": 0.008},
    "Sandwich": {"Bread": 0.08, "Vegetables": 0.05, "Cheese": 0.025, "Oil": 0.004},
    "Idli": {"Rice": 0.07, "Urad Dal": 0.025, "Oil": 0.002},
    "Masala Dosa": {"Rice": 0.09, "Urad Dal": 0.025, "Potato": 0.07, "Onion": 0.02, "Oil": 0.012},
}
PROCUREMENT_SAFETY_RATIO = 0.08

# Default local LLM for the SmartServe AI assistant.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")
