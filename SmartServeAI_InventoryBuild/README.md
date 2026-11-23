# 🍽️ SmartServe AI

**Predict. Prepare. Prevent Waste.**

An AI-powered decision-support system for food-service operations. It converts
demand forecasts into production recommendations, estimates waste risk, and lets
operators test demand and operational scenarios before preparing food.

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the demo dataset (only needed once)
python dataset/generate_dataset.py

# 4. Train the model (only needed once, or whenever the dataset changes)
python models/train_model.py

# 5. Run the app
python app.py
```

Then open **http://localhost:5000** in your browser.

- `/` — Landing page (problem → solution overview)
- `/dashboard` — The Control Tower: Forecast, 7-Day Forecast, What-If Lab, Analytics

## What's inside

| Path | Purpose |
|---|---|
| `app.py` | Flask app: page routes + all `/api/*` endpoints |
| `config.py` | Central config: food items, thresholds, paths |
| `dataset/generate_dataset.py` | Generates a realistic 2-year synthetic dataset |
| `models/train_model.py` | Trains a `RandomForestRegressor`, saves it with Joblib |
| `models/smartserve_demand_model.pkl` | The trained, serialized model |
| `templates/` | `index.html` (landing), `dashboard.html` (control tower) |
| `static/` | CSS + vanilla JS (no React/Node needed) |
| `database/` | Optional MySQL persistence — the app runs fully without it |

## API Endpoints

- `POST /api/forecast` — single-day demand + production + waste risk
- `POST /api/forecast-week` — 7-day forecast for one item
- `POST /api/what-if` — scenario simulation (demand change % + delay hours)
- `GET /api/analytics` — historical totals, top waste items, weekly trend
- `GET /api/db-status` — reports whether the model/dataset/DB are available

## How the numbers are calculated

**Production Optimizer**
```
recommended_production = predicted_demand × (1 + 6% buffer)
```

**Waste Risk**
```
surplus_ratio = (recommended_production - predicted_demand) / predicted_demand

< 8%   → LOW
8–18%  → MEDIUM
≥ 18%  → HIGH
```
These thresholds are prototype heuristics for the demo, not scientifically
validated universal thresholds — tune them in `config.py` for a real deployment.

## Optional: MySQL persistence

The app works fully with **no database at all**. If you want to persist
forecasts:

```bash
pip install mysqlclient
mysql -u root -p < database/schema.sql
```

Set connection details via environment variables (or edit `config.py` directly):
`SMARTSERVE_DB_HOST`, `SMARTSERVE_DB_USER`, `SMARTSERVE_DB_PASSWORD`, `SMARTSERVE_DB_NAME`.

If MySQL isn't installed or reachable, `/api/db-status` simply reports it as
offline and every write silently no-ops — nothing breaks.

## What was deliberately left out (for a 9-hour build)

React, Node.js, TensorFlow/PyTorch, Docker, complex auth, and microservices —
none of these improve this demo enough to justify the setup time. Plain
HTML/CSS/JS + Flask + scikit-learn covers the full pipeline end to end.


## Enhanced decision layer

The dashboard also includes an AI Decision Summary, estimated demand drivers, production-balance score, Smart Alerts, Menu Intelligence and trend detection. These are decision-support heuristics built on the demonstration dataset and should be validated with real POS data.


## Latest UI & Planning Features
- Light professional Control Tower UI with responsive cards and motion effects
- Multi-item Production Planner for all menu items
- Forecast uncertainty range (prototype planning band)
- Total demand, recommended production, surplus and high-risk item summary
- One-click CSV production-plan export
- Animated planner table and KPI reveal

> Forecast ranges and risk signals are prototype decision-support heuristics. For real deployment, calibrate uncertainty and optimization using real POS, inventory and operational data.


## Real-Time Weather Intelligence

SmartServe can now fetch live weather context from Open-Meteo using a city name and selected date. The backend uses Open-Meteo geocoding plus its forecast endpoint, then maps weather conditions into the project's `Normal`, `Hot`, `Rainy`, or `Cold` categories. This requires internet access when the **Fetch Live Weather** button is used; no API key is required for the public non-commercial API.

If the weather service is unavailable, the existing manual weather selector remains usable. Weather-derived demand effects are still scenario/model signals and should not be treated as causal attribution.

## MySQL Auto-Setup (New)

SmartServe AI now **automatically checks and initializes MySQL at Flask startup**.

If MySQL is running and the configured credentials are valid, the application will:

1. Check whether `smartserve_db` exists.
2. Create `smartserve_db` automatically if it does not exist.
3. Create the `forecasts` table if missing.
4. Create the `sales_history` table if missing.
5. Keep all existing data intact (`CREATE ... IF NOT EXISTS` is used).
6. Print a confirmation such as:
   `"[SmartServe] MySQL ready: Database 'smartserve_db' and required tables are ready."`

If MySQL is stopped, credentials are incorrect, or the MySQL driver is unavailable, SmartServe continues in its existing demo/offline mode instead of crashing.

### Check database status

While Flask is running, open:
`http://127.0.0.1:5000/api/database-status`

Or run:
`check_mysql.bat`

### XAMPP

Start **MySQL** in XAMPP before starting SmartServe if you want database persistence. No manual `CREATE DATABASE smartserve_db` step is required anymore.

## Kitchen Control Tower (New)
The latest build connects the existing forecast and optimization features into an end-to-end kitchen workflow:

`7-Day Demand Forecast → Recipe/Ingredient Requirements → Inventory Check → Procurement Alerts → Kitchen Action Plan`

### Included
- New **Kitchen Control Tower** dashboard tab.
- Recipe/BOM-style ingredient consumption mapping for all 6 demo menu items.
- Demo ingredient inventory with units and unit costs.
- 7-day ingredient requirement aggregation.
- Automatic shortage detection and suggested procurement quantity with an 8% prototype safety allowance.
- Procurement cost estimate.
- Today's menu-level production action plan.
- 7-day production timeline.
- Live Open-Meteo weather context when available, with a Normal-weather fallback if the service is unavailable.
- MySQL auto-setup now also creates `ingredient_inventory` and `procurement_alerts` tables.

### Important prototype note
Ingredient quantities, stock levels, recipe mappings and procurement costs are **demo assumptions**. They should be replaced by real recipes/BOM data, inventory transactions and supplier rules before operational use. The demand model is also a prototype and should be validated with real POS data.


## Model compatibility
SmartServe AI targets scikit-learn 1.9.0. The packaged legacy 1.8 model is retained only for reference and is not loaded by the application. If `models/smartserve_demand_model.pkl` is missing, the Flask app automatically runs `models/train_model.py` using the installed environment before serving forecasts. You can also run `rebuild_model.bat` manually.

The production planner no longer falls back to a hard-coded 100-unit demand for every menu item. If the ML model is unavailable, it uses an item-specific historical baseline with transparent context adjustments, so each menu item remains distinct.


## Model startup and scikit-learn 1.9.0

The application does **not** train the Random Forest during Flask startup. This prevents the server from appearing frozen while scikit-learn/SciPy initializes or while the model trains.

1. Start the application with `python app.py`.
2. If `models/smartserve_demand_model.pkl` is missing or incompatible, the dashboard still starts and uses an item-specific historical-demand fallback. It does not use a hard-coded 100-unit demand.
3. To create a model for the installed environment, run `rebuild_model.bat`. The script requires scikit-learn 1.9.0.
4. The training script uses 80 Random Forest trees and one process to reduce resource spikes on Windows/Python 3.13.

If `rebuild_model.bat` itself hangs, test the environment first:

```powershell
python -c "import sklearn, scipy; print(sklearn.__version__, scipy.__version__)"
```

The old scikit-learn 1.8 pickle is retained only as a legacy reference and is never loaded automatically.
## New visualization and daily analysis layer

The dashboard now includes a **Daily Analysis** workspace and a richer **Analytics** workspace.

- Day-level demand, prepared, sold, waste and sell-through KPIs
- 14-day operating trend chart
- Menu-item demand bar chart
- Waste-share donut chart
- Historical 12-week demand vs production line chart
- Historical waste-by-item chart
- Historical demand-vs-prepared chart
- Daily item scorecard with production gaps
- Historical context chips for weather, event and holiday
- Responsive charts rendered with native browser Canvas APIs; no chart CDN is required
- Daily analysis defaults to the latest date available in the demo dataset

The visualizations are decision-support views calculated from the supplied historical dataset; they should not be interpreted as real-world restaurant measurements.


## MCA Major Project Upgrade — Intelligence Hub
The latest build adds an **Explainable Demand Intelligence Hub** designed to make the project stronger as an MCA major project:

- Day-of-week demand comparison
- Weather sensitivity comparison
- Day × Weather scenario matrix
- Context impact decomposition (weather, event, holiday, temporal)
- Next 7-day demand timeline
- Historical weekday evidence
- Seasonal/monthly demand analysis
- Production recommendation + waste-risk signal
- Model evaluation cards (R², MAE, MAPE, train/test rows)
- Professional responsive UI integrated into the existing Control Tower

### Recommended MCA demonstration flow
`Historical Data → Feature Engineering → ML Forecast → Weather/Day/Event Context → Explainable Impact → Production Optimization → Waste Risk → AI Recommendation`

Context impact is a **scenario-based decision-support signal**, not a causal inference claim. Replace the synthetic dataset with real POS/weather/event data for production research.

## Operational extensions (MCA project build)

This build adds six integrated dashboard workspaces:

- **Waste & Sustainability:** reads the packaged historical dataset and estimates waste as prepared minus sold. The screen labels this as an estimate, not a direct waste measurement.
- **Ingredient Inventory:** create/update/delete ingredient stock records. Data is persisted in `database/smartserve_local.sqlite3`.
- **Suppliers & Purchase:** persist supplier contacts and purchase-order drafts. Drafts are not transmitted to suppliers and do not trigger payments.
- **Revenue & Profit:** save daily item sales, selling price and unit cost; revenue, cost and gross profit are calculated and persisted.
- **Ollama Assistant:** calls the local Ollama `/api/generate` endpoint. Install Ollama, run `ollama pull qwen2.5:0.5b`, start the Ollama service, the dashboard defaults to qwen2.5:0.5b; you can change the model field if needed. Set `OLLAMA_URL` if Ollama is not at `http://localhost:11434`.
- **Model Monitoring:** reports whether the model and dataset are loaded and displays only metrics actually present in `models/metrics.json`. It explicitly reports when evaluation metrics are unavailable.

### Local persistence and configuration

The new operational modules use SQLite by default and initialize their tables automatically on app startup. The database location can be changed with `SMARTSERVE_LOCAL_DB`. This is independent of the optional MySQL integration used by the existing application. Back up `database/smartserve_local.sqlite3` to preserve inventory, supplier, purchase-order and sales records.

### Ollama setup (optional)

```bash
# Install Ollama from https://ollama.com, then in a terminal:
ollama pull qwen2.5:0.5b
ollama serve
```

Run the Flask application in another terminal. Ollama is optional; all other dashboard modules remain usable if it is not installed or running.

### Important project limitations

- The included food-demand dataset and ingredient/recipe assumptions are demonstration data. Replace them with restaurant POS, recipe and stock records before making operational decisions.
- Waste is estimated from the historical prepared/sold fields.
- Purchase orders are drafts only; no email, supplier portal, payment or delivery integration is implemented.
- Profit is gross profit based on user-entered sales and unit costs; it excludes labour, rent, tax, delivery fees and other overheads.
- Model monitoring does not invent evaluation scores. Run the model training/evaluation workflow and ensure `models/metrics.json` is produced to display real metrics.
- Authentication, role-based access and production deployment hardening are not included in this academic prototype.


### Default Ollama model: Qwen 2.5 (0.5B)

SmartServe AI is configured to use `qwen2.5:0.5b` by default. After installing Ollama, run `ollama pull qwen2.5:0.5b` once. Keep the Ollama service running while using the assistant. To override the default model, set the `OLLAMA_MODEL` environment variable before starting Flask. The Ollama server URL can be configured with `OLLAMA_URL` (default `http://localhost:11434`).
