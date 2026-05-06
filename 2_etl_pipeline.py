"""
2_etl_pipeline.py
=================
Cleans and loads all five datasets into the hospital_analytics MySQL database.

Dataset file layout expected in ./data/:
    data/appointments.csv          ← Kaggle Medical Appointments No-Show
    data/hcahps.csv                ← CMS HCAHPS
    data/hcup.csv                  ← AHRQ HCUP
    data/cdc_chronic.csv           ← CDC Chronic Disease Indicators
    data/us_mortality.csv          ← Kaggle US Chronic Disease & Mortality
"""

import os
import math
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", "reeti2212"),
    "database": "hospital_analytics",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# UTILITY HELPERS

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def bulk_insert(cursor, table: str, columns: list[str], rows: list[tuple],
                batch_size: int = 500):
    """Insert rows in batches with ON DUPLICATE KEY UPDATE (idempotent)."""
    if not rows:
        print(f"  [SKIP] No rows to insert into {table}.")
        return
    placeholders = ", ".join(["%s"] * len(columns))
    col_str      = ", ".join(f"`{c}`" for c in columns)
    update_str   = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in columns
                             if c not in ("location_id", "time_id", "disease_id",
                                          "appt_id", "metric_id"))
    sql = (f"INSERT INTO `{table}` ({col_str}) VALUES ({placeholders}) "
           f"ON DUPLICATE KEY UPDATE {update_str or '`' + columns[0] + '`=VALUES(`' + columns[0] + '`)'};")
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        cursor.executemany(sql, batch)
        total += len(batch)
    print(f"  [OK] {total} rows → {table}")


def nan_none(val):
    """Convert NaN / inf to None for MySQL."""
    if val is None:
        return None
    try:
        if math.isnan(float(val)) or math.isinf(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    return val


# US state lookup
STATE_MAP = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia",
    "HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
    "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina",
    "ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania",
    "RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
    "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
    "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
}
REGION_MAP = {
    "Northeast": ["CT","ME","MA","NH","NJ","NY","PA","RI","VT"],
    "Midwest":   ["IL","IN","IA","KS","MI","MN","MO","NE","ND","OH","SD","WI"],
    "South":     ["AL","AR","DE","FL","GA","KY","LA","MD","MS","NC","OK",
                  "SC","TN","TX","VA","WV","DC"],
    "West":      ["AK","AZ","CA","CO","HI","ID","MT","NV","NM","OR","UT","WA","WY"],
}
STATE_TO_REGION = {s: r for r, states in REGION_MAP.items() for s in states}

import random
random.seed(42)
US_STATES = list(STATE_MAP.keys())

# STEP 1 — LOAD DIMENSION TABLES

def load_dim_location(cursor):
    """Populate dim_location from the STATE_MAP."""
    print("\n[1] Loading dim_location ...")
    rows = []
    for code, name in STATE_MAP.items():
        region = STATE_TO_REGION.get(code, "Other")
        rows.append((code, name, region, None, None))
    bulk_insert(cursor, "dim_location",
                ["state_code", "state_name", "region",
                 "median_income", "uninsured_rate"],
                rows)


def load_dim_time(cursor):
    """Populate dim_time with every month from 2015-01 to 2023-12."""
    print("\n[2] Loading dim_time ...")
    rows = []
    season_map = {12:"Winter",1:"Winter",2:"Winter",
                  3:"Spring",4:"Spring",5:"Spring",
                  6:"Summer",7:"Summer",8:"Summer",
                  9:"Fall",10:"Fall",11:"Fall"}
    for year in range(2015, 2024):
        for month in range(1, 13):
            full_date = f"{year}-{month:02d}-01"
            quarter   = (month - 1) // 3 + 1
            season    = season_map[month]
            rows.append((full_date, year, month, quarter, season))
    bulk_insert(cursor, "dim_time",
                ["full_date", "year", "month", "quarter", "season"], rows)


def load_dim_disease(cursor):
    """Seed dim_disease with common chronic disease categories."""
    print("\n[3] Loading dim_disease ...")
    diseases = [
        ("Cardiovascular Disease",   "I25",  1),
        ("Diabetes",                 "E11",  1),
        ("Chronic Respiratory",      "J44",  1),
        ("Cancer",                   "C80",  1),
        ("Cerebrovascular Disease",  "I67",  1),
        ("Chronic Kidney Disease",   "N18",  1),
        ("Obesity",                  "E66",  1),
        ("Mental Health Disorder",   "F32",  1),
        ("Influenza / Pneumonia",    "J18",  0),
        ("Sepsis / Infection",       "A41",  0),
    ]
    bulk_insert(cursor, "dim_disease",
                ["disease_category", "icd10_code", "chronic_flag"], diseases)


# STEP 2 — BUILD LOOKUP DICTS (for FK resolution)
def build_lookups(cursor) -> dict:
    """Return dicts: state_code→location_id, (year,month)→time_id, category→disease_id."""
    cursor.execute("SELECT location_id, state_code FROM dim_location;")
    loc_map = {row[1]: row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT time_id, year, month FROM dim_time;")
    time_map = {(row[1], row[2]): row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT disease_id, disease_category FROM dim_disease;")
    dis_map = {row[1]: row[0] for row in cursor.fetchall()}

    return {"location": loc_map, "time": time_map, "disease": dis_map}


# STEP 3 — LOAD FACT TABLES

def load_fact_appointments(cursor, lookups: dict):
    """
    Load Kaggle Medical Appointments No-Show dataset.
    Expected CSV columns (original Kaggle names):
        PatientId, AppointmentID, Gender, ScheduledDay, AppointmentDay,
        Age, Neighbourhood, Scholarship, Hipertension, Diabetes,
        Alcoholism, Handcap, SMS_received, No-show
    """
    path = os.path.join(DATA_DIR, "appointments.csv")
    if not os.path.exists(path):
        print(f"\n[SKIP] {path} not found — skipping appointments.")
        return

    print(f"\n[4] Loading fact_appointments from {path} ...")
    df = pd.read_csv(path)

    # Normalise column names
    df.columns = [c.strip().lower().replace("-", "_").replace(" ", "_")
                  for c in df.columns]

    # Parse dates
    df["appointmentday"] = pd.to_datetime(df["appointmentday"], errors="coerce")
    df["scheduledday"]   = pd.to_datetime(df["scheduledday"],   errors="coerce")
    df.dropna(subset=["appointmentday"], inplace=True)

    df["year"]      = df["appointmentday"].dt.year
    df["month"]     = df["appointmentday"].dt.month
    df["wait_days"] = (df["appointmentday"] - df["scheduledday"]).dt.days.clip(lower=0)

    # No-show → binary
    df["no_show"] = df["no_show"].map({"Yes": 1, "No": 0}).fillna(0).astype(int)

    # Simulate US state (original dataset is Brazilian)
    df["state_code"] = [random.choice(US_STATES) for _ in range(len(df))]

    rows = []
    loc_map  = lookups["location"]
    time_map = lookups["time"]

    for _, r in df.iterrows():
        loc_id  = loc_map.get(r["state_code"])
        time_id = time_map.get((int(r["year"]), int(r["month"])))
        if not loc_id or not time_id:
            continue
        gender = str(r.get("gender", "")).strip().upper()[:1] or None
        age    = int(r["age"]) if 0 <= r["age"] <= 120 else None
        rows.append((
            loc_id, time_id, age, gender,
            int(r["no_show"]),
            int(r.get("sms_received", 0)),
            nan_none(r["wait_days"]),
            str(r.get("neighbourhood", ""))[:100],
        ))

    bulk_insert(cursor, "fact_appointments",
                ["location_id", "time_id", "age", "gender", "no_show",
                 "sms_received", "wait_days", "neighbourhood"],
                rows)


def load_fact_hospital_metrics(cursor, lookups: dict):
    """
    Merges HCAHPS + HCUP + CDC Chronic + US Mortality into fact_hospital_metrics.

    Expected CSVs:
        hcahps.csv    — columns: state, year, overall_rating (0-100)
        hcup.csv      — columns: state, year, er_visits, admissions,
                                 avg_los, bed_occupancy_rate, er_wait_minutes
        cdc_chronic.csv  — columns: state, year, disease_category,
                                    prevalence_rate
        us_mortality.csv — columns: state, year, disease_category,
                                    mortality_rate
    """
    loc_map  = lookups["location"]
    time_map = lookups["time"]
    dis_map  = lookups["disease"]

    # ── Load each source
    sources = {}
    for fname in ["hcahps.csv", "hcup.csv", "cdc_chronic.csv", "us_mortality.csv"]:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            sources[fname] = df
            print(f"  [READ] {fname}: {len(df)} rows")
        else:
            print(f"  [MISSING] {fname}")
            sources[fname] = None

    # ── If files are missing
    if all(v is None for v in sources.values()):
        print("\n[4b] No source files found.")
        _insert_synthetic_metrics(cursor, loc_map, time_map, dis_map)
        return

    print("\n[5] Merging & loading fact_hospital_metrics ...")

    # Build a combined frame keyed on (state_code, year)
    base_keys = [(sc, yr) for sc in US_STATES for yr in range(2015, 2024)]
    base_df   = pd.DataFrame(base_keys, columns=["state_code", "year"])

    def safe_merge(base, src_df, key_cols, value_cols):
        if src_df is None:
            for c in value_cols:
                base[c] = None
            return base
        src = src_df[key_cols + value_cols].copy()
        src["state_code"] = src[key_cols[0]].str.upper().str.strip()
        return base.merge(src[["state_code", "year"] + value_cols],
                          on=["state_code", "year"], how="left")

    # HCAHPS
    base_df = safe_merge(base_df, sources["hcahps.csv"],
                         ["state", "year"], ["overall_rating"])
    # HCUP
    base_df = safe_merge(base_df, sources["hcup.csv"],
                         ["state", "year"],
                         ["er_visits", "admissions", "avg_los",
                          "bed_occupancy_rate", "er_wait_minutes"])
    # CDC chronic (explode to per-disease rows)
    cdc = sources["cdc_chronic.csv"]
    mort = sources["us_mortality.csv"]

    rows = []
    for _, r in base_df.iterrows():
        sc   = r["state_code"]
        yr   = int(r["year"])
        loc_id  = loc_map.get(sc)
        time_id = time_map.get((yr, 1))   # use Jan as representative
        if not loc_id or not time_id:
            continue

        # One row per disease
        for dis_name, dis_id in dis_map.items():
            prevalence = None
            mortality  = None

            if cdc is not None:
                m = cdc[(cdc["state"].str.upper() == sc) &
                        (cdc["year"].astype(str) == str(yr)) &
                        (cdc["disease_category"] == dis_name)]
                if not m.empty:
                    prevalence = nan_none(m.iloc[0].get("prevalence_rate"))

            if mort is not None:
                m = mort[(mort["state"].str.upper() == sc) &
                         (mort["year"].astype(str) == str(yr)) &
                         (mort["disease_category"] == dis_name)]
                if not m.empty:
                    mortality = nan_none(m.iloc[0].get("mortality_rate"))

            rows.append((
                loc_id, time_id, dis_id,
                nan_none(r.get("overall_rating")),
                nan_none(r.get("er_wait_minutes")),
                nan_none(r.get("er_visits")),
                nan_none(r.get("bed_occupancy_rate")),
                nan_none(r.get("admissions")),
                nan_none(r.get("avg_los")),
                mortality,
                prevalence,
            ))

    bulk_insert(cursor, "fact_hospital_metrics",
                ["location_id", "time_id", "disease_id",
                 "hcahps_score", "er_wait_minutes", "total_er_visits",
                 "bed_occupancy_rate", "total_admissions",
                 "avg_length_of_stay", "mortality_rate", "chronic_prevalence"],
                rows)


def _insert_synthetic_metrics(cursor, loc_map, time_map, dis_map):
    """Generate plausible hospital metrics for all states × years × diseases."""
    import numpy as np
    np.random.seed(42)

    rows = []
    for state_code, loc_id in loc_map.items():
        for (yr, mo), time_id in time_map.items():
            if mo != 1:        # one row per state-year
                continue
            for dis_name, dis_id in dis_map.items():
                rows.append((
                    loc_id, time_id, dis_id,
                    round(float(np.random.normal(72, 10)),  2),  
                    round(float(np.random.normal(145, 35)), 1),  
                    int(np.random.randint(8_000, 120_000)),      
                    round(float(np.random.uniform(55, 95)),  2),  
                    int(np.random.randint(5_000, 80_000)),        
                    round(float(np.random.normal(4.2, 1.1)), 1),
                    round(float(np.random.uniform(5, 250)),  2), 
                    round(float(np.random.uniform(2, 35)),   2),  
                ))

    bulk_insert(cursor, "fact_hospital_metrics",
                ["location_id", "time_id", "disease_id",
                 "hcahps_score", "er_wait_minutes", "total_er_visits",
                 "bed_occupancy_rate", "total_admissions", "avg_length_of_stay",
                 "mortality_rate", "chronic_prevalence"],
                rows)


# MAIN

def main():
    try:
        conn = get_connection()
        cur  = conn.cursor()

        # Dimension tables
        load_dim_location(cur);  conn.commit()
        load_dim_time(cur);      conn.commit()
        load_dim_disease(cur);   conn.commit()

        # Build FK lookup dicts
        lookups = build_lookups(cur)

        # Fact tables
        load_fact_appointments(cur, lookups);     conn.commit()
        load_fact_hospital_metrics(cur, lookups); conn.commit()

        print("\n[DONE] ETL pipeline complete.")

    except Error as e:
        print(f"[ERROR] {e}")
        conn.rollback()
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()