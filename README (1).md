# Smart Hospital Resource & Patient Flow Analytics System

## Project structure

```
hospital_analytics/
├── 1_db_setup.py          ← Creates MySQL database + all tables
├── 2_etl_pipeline.py      ← Cleans & loads all datasets into MySQL
├── 3_analytics_engine.py  ← Analytics engine (all 3 dashboard features)
├── requirements.txt
├── .env.example           ← Copy to .env and add your MySQL password
└── data/                  ← Put your CSV files here
    ├── appointments.csv   ← Kaggle Medical Appointments No-Show
    ├── hcahps.csv         ← CMS HCAHPS
    ├── hcup.csv           ← AHRQ HCUP
    ├── cdc_chronic.csv    ← CDC Chronic Disease Indicators
    └── us_mortality.csv   ← Kaggle US Chronic Disease & Mortality
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure database
cp .env.example .env
# Edit .env with your MySQL host/user/password

# 3. Create database and tables
python 1_db_setup.py

# 4. Load datasets (put CSVs in ./data/ first)
python 2_etl_pipeline.py

# 5. Test all three dashboard features
python 3_analytics_engine.py
```


## Dashboard features

### Feature 1 — Patient Flow Monitor
```python
from analytics_engine import PatientFlowMonitor
pfm = PatientFlowMonitor()

pfm.monthly_noshow_trend(state_code="TX", start_year=2020, end_year=2023)
pfm.regional_flow_summary(year=2022)
pfm.age_group_noshow(year=2022)
pfm.realtime_snapshot()
```

### Feature 2 — ER Wait Time Predictor
```python
from analytics_engine import ERWaitPredictor
predictor = ERWaitPredictor()
predictor.train()

predictor.predict({
    "age": 52, "gender": "M", "sms_received": 1,
    "wait_days": 2, "month": 8, "season": "Summer",
    "region": "South", "bed_occupancy_rate": 88.5,
    "total_er_visits": 65000,
})
predictor.state_er_heatmap(year=2022)
predictor.feature_importance()
```

### Feature 3 — Bed Occupancy Forecast
```python
from analytics_engine import BedOccupancyForecaster
forecaster = BedOccupancyForecaster()

forecaster.forecast(state_code="CA", periods=6)
forecaster.multi_state_forecast(["CA", "TX", "NY", "FL"], periods=6)
forecaster.capacity_alerts(year=2023)
```

## Expected CSV column names

### appointments.csv (Kaggle No-Show)
`PatientId, AppointmentID, Gender, ScheduledDay, AppointmentDay, Age, Neighbourhood, SMS_received, No-show`

### hcahps.csv (CMS)
`state, year, overall_rating`

### hcup.csv (AHRQ) -- synthetic data
`state, year, er_visits, admissions, avg_los, bed_occupancy_rate, er_wait_minutes`

### cdc_chronic.csv (CDC Open Data)
`state, year, disease_category, prevalence_rate`

### us_mortality.csv (Kaggle)
`state, year, disease_category, mortality_rate`
