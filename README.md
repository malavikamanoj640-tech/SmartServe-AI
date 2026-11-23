# 🍽️ SmartServe AI — Restaurant Demand Forecasting & Kitchen Intelligence

**Predict. Prepare. Prevent Waste.**

SmartServe AI is an intelligent restaurant management and demand forecasting system designed to help restaurants make data-driven operational decisions. It combines machine learning-based demand prediction, production planning, inventory intelligence, waste analysis, contextual insights, and a local AI assistant to improve kitchen efficiency and reduce unnecessary food preparation.

The system provides a centralized dashboard where restaurant operators can forecast demand, analyze operational scenarios, monitor production, and make smarter decisions.

---

## 🚀 Project Overview

Traditional restaurant operations often rely on manual estimation of customer demand, which can lead to overproduction, food waste, shortages, and inefficient resource utilization.

SmartServe AI addresses these challenges by analyzing historical demand patterns and contextual factors to generate forecasts and operational recommendations.

### 🎯 Objectives

- Forecast restaurant food-item demand using machine learning.
- Optimize food production quantities based on predicted demand.
- Reduce food waste and production surplus.
- Analyze the impact of weather, events, holidays, and operational conditions.
- Improve inventory and ingredient planning.
- Support restaurant decision-making through AI-driven insights.
- Provide an AI assistant for system guidance and analytical support.

---

## ✨ Key Features

### 📊 1. Demand Forecasting
- Predict demand for individual menu items.
- Analyze historical sales patterns.
- Generate recommended production quantities.
- Identify surplus and potential waste risks.

### 📅 2. 7-Day Demand Forecast
- Forecast demand for the upcoming seven days.
- View day-wise demand and production recommendations.
- Identify high-risk days.
- Support advance kitchen planning.

### 🧪 3. What-If Simulation Lab
Simulate operational scenarios by changing factors such as:
- Demand percentage
- Operational delays
- Demand variations

Compare baseline predictions with scenario-based outcomes before making decisions.

### 🍳 4. Production Planner
- Plan production based on predicted demand.
- Compare forecast demand with planned production.
- Calculate surplus quantities.
- Identify potential production mismatches.

### 🤖 5. AI Optimization
- Generate data-driven operational recommendations.
- Identify potential inefficiencies.
- Support waste reduction and production planning decisions.

### 🎛️ 6. Kitchen Control Tower
A centralized operational dashboard providing an overview of:
- Demand forecasts
- Production quantities
- Surplus indicators
- Waste risks
- Operational insights

### 🌦️ 7. Context Intelligence
Analyze contextual influences on restaurant demand, including:
- Weather conditions
- Events
- Holidays
- Day of the week
- Historical patterns

### 📈 8. Analytics Dashboard
Visualize restaurant operational data through interactive charts, trend analysis, demand comparisons, and performance indicators.

### 📆 9. Daily Analysis
Analyze daily restaurant performance, including:
- Demand
- Production
- Sales
- Waste
- Waste percentage
- Production-demand gap

### ♻️ 10. Waste & Sustainability Center
- Analyze food waste.
- Calculate waste percentage.
- Estimate waste-related cost.
- Monitor production and sales differences.
- Support sustainability-oriented kitchen decisions.

### 📦 11. Ingredient Inventory Management
- Track ingredient quantities.
- Monitor stock availability.
- Manage inventory records.
- Support ingredient planning.

### 🏪 12. Supplier Management
- Maintain supplier information.
- Organize supplier records.
- Support ingredient procurement workflows.

### 🧾 13. Purchase Order Management
- Create purchase order drafts.
- Organize purchasing requirements.
- Support inventory replenishment workflows.

### 💰 14. Revenue & Profit Analytics
- Analyze revenue and cost inputs.
- Estimate gross profit.
- Calculate profit margins.
- Support financial decision-making.

### 🧠 15. SmartServe AI Assistant (Ollama + Qwen)
Integrated local AI assistant powered by Ollama using:

**Model: `qwen2.5:0.5b`**

The assistant is designed to help with:
- SmartServe system guidance
- Restaurant operations questions
- Demand forecasting explanations
- Production planning support
- Waste and inventory insights

The AI model runs locally through Ollama, rather than requiring a cloud AI API key.

### 📉 16. AI Model Monitoring
- View model evaluation information when available.
- Monitor forecasting performance metrics.
- Support model evaluation and improvement.

---

## 🏗️ System Architecture

```text
                    SMARTSERVE AI
                          │
                          ▼
              ┌──────────────────────┐
              │   Web Dashboard UI   │
              │ HTML / CSS / JS     │
              │ Interactive Charts   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    Flask Backend     │
              │   Routes & APIs      │
              └──────────┬───────────┘
                         │
          ┌──────────────┼───────────────────┐
          ▼              ▼                   ▼
 ┌──────────────┐ ┌──────────────┐  ┌────────────────┐
 │ ML Forecast │ │ Operational  │  │ Local AI       │
 │ Engine      │ │ Intelligence │  │ Assistant      │
 │             │ │              │  │ Ollama/Qwen   │
 └──────────────┘ └──────────────┘  └────────────────┘
          │              │                   │
          └──────────────┼───────────────────┘
                         ▼
              ┌──────────────────────┐
              │   Data Management   │
              │ Dataset / SQLite    │
              └──────────────────────┘
```

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | Flask |
| Machine Learning | Scikit-learn, Pandas, NumPy |
| Data Visualization | Plotly, JavaScript |
| Frontend | HTML5, CSS3, JavaScript |
| Database | SQLite |
| AI Assistant | Ollama |
| LLM | Qwen 2.5 – 0.5B |
| Data Processing | Pandas, NumPy |
| Development Tools | VS Code, Git, GitHub |

---

## 📂 Project Structure

```text
SmartServe-AI/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
│
├── dataset/
│
├── models/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│
├── pull_qwen_model.bat
└── run_smartserve.bat
```

*The exact folders and filenames may vary depending on the project version.*

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/https://github.com/malavikamanoj640-tech/SmartServe-AI/SmartServe-AI.git
```

### 2. Navigate to the project folder

```bash
cd SmartServe-AI
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Install Ollama

Download and install Ollama:

https://ollama.com/download

### 7. Download the Qwen model

```bash
ollama pull qwen2.5:0.5b
```

### 8. Run SmartServe AI

```bash
python app.py
```

Or use the provided Windows launcher if available:

```text
run_smartserve.bat
```

### 9. Open the application

Navigate to:

```text
http://127.0.0.1:5000
```

---

## 🧠 AI Model Configuration

SmartServe AI uses a local LLM through Ollama.

| Setting | Value |
|---|---|
| AI Framework | Ollama |
| Model | Qwen 2.5 |
| Model Tag | `qwen2.5:0.5b` |
| Hosting | Local machine |
| API | Ollama local API |
| Cloud API key | Not required |

Ensure Ollama is running before using the AI assistant.

---

## 📊 Machine Learning Workflow

```text
Historical Restaurant Data
          │
          ▼
    Data Preprocessing
          │
          ▼
 Feature Engineering
          │
          ▼
   ML Model Training
          │
          ▼
   Demand Prediction
          │
          ▼
 Production Recommendation
          │
          ▼
 Waste & Surplus Analysis
          │
          ▼
 Operational Insights
```

---

## 🌍 Sustainable Development Goals (SDGs)

### SDG 12 – Responsible Consumption and Production
Supports more efficient food production planning and aims to reduce unnecessary food preparation and waste.

### SDG 9 – Industry, Innovation and Infrastructure
Demonstrates the use of machine learning, AI, digital analytics, and intelligent automation in restaurant operations.

### SDG 8 – Decent Work and Economic Growth
Supports operational efficiency, resource utilization, and data-driven decision-making.

---

## 🔬 Project Scope

SmartServe AI is developed as an academic MCA project demonstrating the application of machine learning and AI to restaurant operational planning.

The system can be extended in the future to integrate:
- Live POS systems
- Real-time sales tracking
- IoT kitchen sensors
- Advanced inventory forecasting
- Automated procurement
- Multi-branch restaurant analytics
- Cloud deployment
- Advanced model explainability

---

## ⚠️ Disclaimer

This project is an academic prototype. Forecasts and recommendations depend on the available dataset, model performance, and configured integrations. AI-generated responses should be treated as assistance and not as guaranteed operational decisions.

---

## 👩‍💻 Developed By

**Malavika Manoj**
**Master of Computer Applications (MCA)**

*SmartServe AI: Restaurant Demand Forecasting & Kitchen Intelligence System*

---

## ⭐ If you find this project interesting

Feel free to explore, fork, or improve the project.

**Predict smarter. Prepare better. Waste less.**
