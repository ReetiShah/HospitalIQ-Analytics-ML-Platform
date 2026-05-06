# 🏥 HospitalIQ: Smart Hospital Resource & Patient Flow Analytics System

> An end-to-end healthcare analytics platform integrating multi-source data via a scalable ETL pipeline and MySQL star schema. Featuring ML models for ER wait time prediction, congestion risk analysis, and time-series forecasting for bed occupancy—all deployed through an interactive Streamlit dashboard.

---

## Key Features

| Feature | Description | Use Case |
|---------|-------------|----------|
| 📊 **Patient Flow Monitor** | Real-time patient appointment trends, no-show analysis, and regional flow patterns | Track patient behavior and optimize scheduling |
| ⏱️ **ER Wait Time Predictor** | ML-powered predictions for emergency room wait times with feature importance analysis | Reduce patient wait times and improve satisfaction |
| 🛏️ **Bed Occupancy Forecast** | Time-series forecasting for hospital bed availability across multiple states | Optimize resource allocation and capacity planning |

---

## Project Structure

```
hospital_analytics/
├── 1_db_setup.py              # Creates MySQL database + all tables
├── 2_etl_pipeline.py          # Cleans & loads all datasets into MySQL
├── 3_analytics_engine.py      # Analytics engine (all 3 dashboard features)
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment configuration
└── data/                      # Input data directory
    ├── appointments.csv       # Kaggle Medical Appointments No-Show Dataset
    ├── hcahps.csv             # CMS Hospital Consumer Assessment
    ├── hcup.csv               # AHRQ Hospital Utilization Project
    ├── cdc_chronic.csv        # CDC Chronic Disease Indicators
    └── us_mortality.csv       # Kaggle US Chronic Disease & Mortality
```

---

##  Quick Start

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- Kaggle & CMS datasets

### Installation Steps

```bash
# 1️⃣ Clone and install dependencies
git clone https://github.com/ReetiShah/HospitalIQ-Analytics-ML-Platform.git
cd hospital_analytics
pip install -r requirements.txt

# 2️⃣ Configure database
cp .env.example .env
# Edit .env with your MySQL credentials:
# DB_HOST=localhost
# DB_USER=your_username
# DB_PASSWORD=your_password

# 3️⃣ Initialize database
python 1_db_setup.py

# 4️⃣ Load and process datasets
# (Make sure CSV files are in ./data/ directory first)
python 2_etl_pipeline.py

# 5️⃣ Run analytics engine
python 3_analytics_engine.py
```

---

##  Usage Examples

###Feature 1: Patient Flow Monitor
Track patient appointment patterns and no-show trends across regions.

```python
from analytics_engine import PatientFlowMonitor

pfm = PatientFlowMonitor()

# Analyze monthly no-show trends for a specific state
pfm.monthly_noshow_trend(state_code="TX", start_year=2020, end_year=2023)

# Get regional summary statistics
pfm.regional_flow_summary(year=2022)

# Analyze no-show patterns by age group
pfm.age_group_noshow(year=2022)

# View real-time system snapshot
pfm.realtime_snapshot()
```

### Feature 2: ER Wait Time Predictor
Predict emergency room wait times using machine learning.

```python
from analytics_engine import ERWaitPredictor

predictor = ERWaitPredictor()
predictor.train()

# Make a prediction
prediction = predictor.predict({
    "age": 52,
    "gender": "M",
    "sms_received": 1,
    "wait_days": 2,
    "month": 8,
    "season": "Summer",
    "region": "South",
    "bed_occupancy_rate": 88.5,
    "total_er_visits": 65000,
})

# Generate state-level heatmap
predictor.state_er_heatmap(year=2022)

# View feature importance
predictor.feature_importance()
```

### Feature 3: Bed Occupancy Forecast
Forecast hospital bed availability using time-series analysis.

```python
from analytics_engine import BedOccupancyForecaster

forecaster = BedOccupancyForecaster()

# Single state forecast (6 months ahead)
forecaster.forecast(state_code="CA", periods=6)

# Multi-state forecast
forecaster.multi_state_forecast(["CA", "TX", "NY", "FL"], periods=6)

# Get capacity alerts
forecaster.capacity_alerts(year=2023)
```

---

## Data Schema

### Input Data Files & Columns

#### `appointments.csv` — Kaggle Medical Appointments No-Show Dataset
```
PatientId, AppointmentID, Gender, ScheduledDay, AppointmentDay, 
Age, Neighbourhood, SMS_received, No-show
```

#### `hcahps.csv` — CMS Hospital Consumer Assessment
```
state, year, overall_rating
```

#### `hcup.csv` — AHRQ Hospital Utilization Project (Synthetic)
```
state, year, er_visits, admissions, avg_los, bed_occupancy_rate, er_wait_minutes
```

#### `cdc_chronic.csv` — CDC Chronic Disease Indicators
```
state, year, disease_category, prevalence_rate
```

#### `us_mortality.csv` — Kaggle US Chronic Disease & Mortality
```
state, year, disease_category, mortality_rate
```

---

## Technical Stack

- **Backend**: Python 3.x
- **Database**: MySQL (Star Schema)
- **Data Processing**: Pandas, NumPy
- **ML Framework**: Scikit-learn
- **Time-Series**: Statsmodels / Prophet
- **Visualization**: Streamlit, Matplotlib, Seaborn

---

##  Pipeline Overview

```
Raw Data (CSV) 
    ↓
[ETL Pipeline] → Data Cleaning & Validation
    ↓
[MySQL Database] → Star Schema (Fact & Dimension Tables)
    ↓
[Analytics Engine] → 3 Core Features
    ↓
[Streamlit Dashboard] → Interactive Visualizations
```

---

##  Contributing

Feel free to fork this repository, create a feature branch, and submit pull requests for improvements!
