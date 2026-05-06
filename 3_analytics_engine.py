"""
3_analytics_engine.py
All three dashboard features:
    Feature 1 — Patient Flow Monitor      (historical + real-time trends)
    Feature 2 — ER Wait Time Predictor    (ML classification + regression)
    Feature 3 — Bed Occupancy Forecast    (time-series with Prophet / ARIMA)

"""

import os
import warnings
import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# ── Optional ML / forecasting imports
try:
    from sklearn.ensemble          import GradientBoostingRegressor, RandomForestClassifier
    from sklearn.model_selection   import train_test_split
    from sklearn.preprocessing     import LabelEncoder
    from sklearn.metrics           import mean_absolute_error, accuracy_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False
    warnings.warn("scikit-learn not installed — ML features disabled.")

try:
    from prophet import Prophet
    PROPHET_OK = True
except ImportError:
    PROPHET_OK = False
    warnings.warn("prophet not installed — falling back to rolling average forecast.")

load_dotenv()
warnings.filterwarnings("ignore")

# DB config 
DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", "reeti2212"),
    "database": "hospital_analytics",
}



def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()
    return df


#PATIENT FLOW MONITOR

class PatientFlowMonitor:
    """
    Analyses historical appointment data and computes patient flow KPIs.
    Powers the 'Patient Flow Monitor' dashboard panel.
    """

    # 1a. Monthly no-show trend by state 
    def monthly_noshow_trend(self,
                             state_code: str | None = None,
                             start_year: int = 2015,
                             end_year:   int = 2023) -> pd.DataFrame:
        """
        Returns month-by-month appointment volume and no-show rate.
        Filter by state_code or leave None for nationwide.

        Returns DataFrame columns:
            state_name, year, month, total_appointments,
            no_shows, no_show_rate_pct, avg_wait_days
        """
        where = "WHERE dt.year BETWEEN %s AND %s"
        params: list = [start_year, end_year]
        if state_code:
            where += " AND dl.state_code = %s"
            params.append(state_code.upper())

        sql = f"""
            SELECT
                dl.state_name,
                dt.year,
                dt.month,
                COUNT(*)                                       AS total_appointments,
                SUM(fa.no_show)                                AS no_shows,
                ROUND(SUM(fa.no_show) / COUNT(*) * 100, 2)    AS no_show_rate_pct,
                ROUND(AVG(fa.wait_days), 1)                    AS avg_wait_days
            FROM fact_appointments fa
            JOIN dim_location dl ON fa.location_id = dl.location_id
            JOIN dim_time     dt ON fa.time_id     = dt.time_id
            {where}
            GROUP BY dl.state_name, dt.year, dt.month
            ORDER BY dt.year, dt.month;
        """
        df = query_df(sql, tuple(params))
        df["period"] = pd.to_datetime(
            df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
        )
        return df

    # 1b. Regional flow summary 
    def regional_flow_summary(self, year: int = 2022) -> pd.DataFrame:
        """
        Aggregated patient flow KPIs grouped by US region.

        Returns DataFrame columns:
            region, total_appointments, no_show_rate_pct,
            avg_wait_days, sms_effectiveness_pct
        """
        sql = """
            SELECT
                dl.region,
                COUNT(*)                                        AS total_appointments,
                ROUND(SUM(fa.no_show) / COUNT(*) * 100, 2)     AS no_show_rate_pct,
                ROUND(AVG(fa.wait_days), 1)                     AS avg_wait_days,
                ROUND(
                    (1 - SUM(CASE WHEN fa.sms_received = 1 AND fa.no_show = 1
                                  THEN 1 ELSE 0 END)
                         / NULLIF(SUM(fa.sms_received), 0)) * 100, 2
                )                                               AS sms_effectiveness_pct
            FROM fact_appointments fa
            JOIN dim_location dl ON fa.location_id = dl.location_id
            JOIN dim_time     dt ON fa.time_id     = dt.time_id
            WHERE dt.year = %s
            GROUP BY dl.region
            ORDER BY no_show_rate_pct DESC;
        """
        return query_df(sql, (year,))

    # 1c. Age-group breakdown
    def age_group_noshow(self, year: int = 2022) -> pd.DataFrame:
        """
        No-show rates segmented into 10-year age bands.

        Returns DataFrame columns:
            age_group, total_appointments, no_show_rate_pct
        """
        sql = """
            SELECT
                CONCAT(
                    FLOOR(fa.age / 10) * 10, '-',
                    FLOOR(fa.age / 10) * 10 + 9
                )                                              AS age_group,
                COUNT(*)                                       AS total_appointments,
                ROUND(SUM(fa.no_show) / COUNT(*) * 100, 2)    AS no_show_rate_pct
            FROM fact_appointments fa
            JOIN dim_time dt ON fa.time_id = dt.time_id
            WHERE dt.year = %s AND fa.age IS NOT NULL AND fa.age BETWEEN 0 AND 100
            GROUP BY age_group
            ORDER BY MIN(fa.age);
        """
        return query_df(sql, (year,))

    # 1d. Real-time snapshot (last 30 days equivalent)
    def realtime_snapshot(self) -> dict:
        """
        Returns a dict of scalar KPIs for a 'live' top-bar summary card.
        Uses the most recent month available in the database.
        """
        sql = """
            SELECT
                COUNT(*)                                        AS appointments_this_month,
                SUM(fa.no_show)                                 AS no_shows_this_month,
                ROUND(SUM(fa.no_show) / COUNT(*) * 100, 2)     AS no_show_rate,
                ROUND(AVG(fa.wait_days), 1)                     AS avg_wait_days,
                SUM(fa.sms_received)                            AS sms_sent
            FROM fact_appointments fa
            JOIN dim_time dt ON fa.time_id = dt.time_id
            WHERE dt.year  = (SELECT MAX(year)  FROM dim_time)
              AND dt.month = (SELECT MAX(month) FROM dim_time
                              WHERE year = (SELECT MAX(year) FROM dim_time));
        """
        df = query_df(sql)
        return df.iloc[0].to_dict() if not df.empty else {}


# FEATURE 2 — ER WAIT TIME PREDICTOR

class ERWaitPredictor:
    """
    Trains a GradientBoosting regressor to predict ER wait times,
    and a RandomForest classifier to flag high-congestion risk.
    Powers the 'ER Wait Time Predictor' dashboard panel.
    """

    FEATURE_COLS = [
        "age", "gender_enc", "sms_received", "wait_days", "month",
        "season_enc", "region_enc", "bed_occupancy_rate", "total_er_visits",
    ]

    def __init__(self):
        self.reg_model   = None   # predicts exact wait minutes
        self.clf_model   = None   # classifies high / low congestion
        self.label_encs  = {}
        self.is_trained  = False

    # 2a. Fetch training data
    def _fetch_training_data(self) -> pd.DataFrame:
        sql = """
            SELECT
                fa.age,
                fa.gender,
                fa.sms_received,
                fa.wait_days,
                dt.month,
                dt.season,
                dl.region,
                hm.bed_occupancy_rate,
                hm.total_er_visits,
                hm.er_wait_minutes         AS target_er_wait
            FROM fact_appointments fa
            JOIN dim_location         dl ON fa.location_id = dl.location_id
            JOIN dim_time             dt ON fa.time_id     = dt.time_id
            LEFT JOIN (
                SELECT location_id, time_id,
                       AVG(bed_occupancy_rate)  AS bed_occupancy_rate,
                       SUM(total_er_visits)     AS total_er_visits,
                       AVG(er_wait_minutes)     AS er_wait_minutes
                FROM fact_hospital_metrics
                GROUP BY location_id, time_id
            ) hm ON hm.location_id = fa.location_id
                 AND hm.time_id    = fa.time_id
            WHERE fa.age IS NOT NULL
              AND hm.er_wait_minutes IS NOT NULL
            LIMIT 100000;
        """
        return query_df(sql)

    # 2b. Pre-process features
    def _preprocess(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        df = df.copy()
        for col in ["gender", "season", "region"]:
            enc_col = col + "_enc"
            if fit:
                le = LabelEncoder()
                df[enc_col] = le.fit_transform(df[col].fillna("Unknown"))
                self.label_encs[col] = le
            else:
                le = self.label_encs.get(col)
                if le:
                    df[enc_col] = df[col].fillna("Unknown").apply(
                        lambda x: le.transform([x])[0]
                        if x in le.classes_ else -1
                    )
                else:
                    df[enc_col] = 0

        num_cols = ["age", "sms_received", "wait_days", "month",
                    "bed_occupancy_rate", "total_er_visits"]
        df[num_cols] = df[num_cols].fillna(df[num_cols].median())
        return df

    # 2c. Train models 
    def train(self) -> dict:
        """
        Trains regressor (predict wait minutes) and classifier (high/low risk).
        Returns a dict of evaluation metrics.

        Returns:
            {
                "reg_mae":    float,   # mean absolute error in minutes
                "clf_acc":    float,   # classification accuracy (0-1)
                "n_samples":  int,
            }
        """
        if not SKLEARN_OK:
            return {"error": "scikit-learn not installed"}

        print("[ML] Fetching training data ...")
        df = self._fetch_training_data()
        if df.empty:
            return {"error": "No training data found. Run ETL first."}

        df = self._preprocess(df, fit=True)
        X  = df[self.FEATURE_COLS].values
        y_reg = df["target_er_wait"].values

        # Binary label: wait > 120 min = high congestion
        y_clf = (y_reg > 120).astype(int)

        X_tr, X_te, yr_tr, yr_te, yc_tr, yc_te = train_test_split(
            X, y_reg, y_clf, test_size=0.2, random_state=42
        )

        print("[ML] Training GradientBoostingRegressor ...")
        self.reg_model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42
        )
        self.reg_model.fit(X_tr, yr_tr)
        reg_mae = mean_absolute_error(yr_te, self.reg_model.predict(X_te))

        print("[ML] Training RandomForestClassifier ...")
        self.clf_model = RandomForestClassifier(
            n_estimators=150, max_depth=6, random_state=42
        )
        self.clf_model.fit(X_tr, yc_tr)
        clf_acc = accuracy_score(yc_te, self.clf_model.predict(X_te))

        self.is_trained = True
        metrics = {
            "reg_mae":   round(reg_mae, 2),
            "clf_acc":   round(clf_acc, 4),
            "n_samples": len(df),
        }
        print(f"[ML] Regressor MAE = {reg_mae:.1f} min | Classifier Acc = {clf_acc:.2%}")
        return metrics

    # 2d. Predict for a single scenario 
    def predict(self, scenario: dict) -> dict:
        """
        Predict ER wait time and congestion risk for a given scenario.

        Args:
            scenario: dict with keys matching FEATURE_COLS (raw, un-encoded)
                Example:
                    {
                        "age": 45, "gender": "F", "sms_received": 1,
                        "wait_days": 3, "month": 7, "season": "Summer",
                        "region": "South", "bed_occupancy_rate": 82.0,
                        "total_er_visits": 50000
                    }

        Returns:
            {
                "predicted_wait_minutes": float,
                "congestion_risk":        str,   # "High" | "Low"
                "risk_probability":       float,
            }
        """
        if not self.is_trained:
            return {"error": "Model not trained. Call .train() first."}

        row = pd.DataFrame([scenario])
        row = self._preprocess(row, fit=False)

        wait_mins = float(self.reg_model.predict(row[self.FEATURE_COLS])[0])
        risk_prob = float(self.clf_model.predict_proba(
            row[self.FEATURE_COLS])[0][1])
        congestion = "High" if risk_prob >= 0.5 else "Low"

        return {
            "predicted_wait_minutes": round(max(0, wait_mins), 1),
            "congestion_risk":        congestion,
            "risk_probability":       round(risk_prob, 4),
        }

    # 2e. State-level ER wait heatmap data
    def state_er_heatmap(self, year: int = 2022) -> pd.DataFrame:
        """
        Returns average ER wait time per state for a choropleth map.

        Returns DataFrame columns:
            state_code, state_name, avg_er_wait_minutes,
            avg_bed_occupancy, total_er_visits
        """
        sql = """
            SELECT
                dl.state_code,
                dl.state_name,
                ROUND(AVG(hm.er_wait_minutes),   1) AS avg_er_wait_minutes,
                ROUND(AVG(hm.bed_occupancy_rate), 2) AS avg_bed_occupancy,
                SUM(hm.total_er_visits)              AS total_er_visits
            FROM fact_hospital_metrics hm
            JOIN dim_location dl ON hm.location_id = dl.location_id
            JOIN dim_time     dt ON hm.time_id     = dt.time_id
            WHERE dt.year = %s
              AND hm.er_wait_minutes IS NOT NULL
            GROUP BY dl.state_code, dl.state_name
            ORDER BY avg_er_wait_minutes DESC;
        """
        return query_df(sql, (year,))

    # 2f. Feature importance
    def feature_importance(self) -> pd.DataFrame:
        """Returns a ranked DataFrame of feature importances from the regressor."""
        if not self.is_trained:
            return pd.DataFrame()
        imp = self.reg_model.feature_importances_
        return (pd.DataFrame({"feature": self.FEATURE_COLS, "importance": imp})
                  .sort_values("importance", ascending=False)
                  .reset_index(drop=True))


# FEATURE 3 — BED OCCUPANCY FORECAST

class BedOccupancyForecaster:
    """
    Forecasts bed occupancy rates for the next N months using Prophet
    (or a rolling-average fallback if Prophet is not installed).
    Powers the 'Bed Occupancy Forecast' dashboard panel.
    """

    # 3a. Fetch historical occupancy
    def _fetch_occupancy(self, state_code: str | None = None) -> pd.DataFrame:
        where  = ""
        params: list = []
        if state_code:
            where  = "AND dl.state_code = %s"
            params = [state_code.upper()]

        sql = f"""
            SELECT
                dt.full_date                             AS ds,
                ROUND(AVG(hm.bed_occupancy_rate), 2)     AS y
            FROM fact_hospital_metrics hm
            JOIN dim_location dl ON hm.location_id = dl.location_id
            JOIN dim_time     dt ON hm.time_id     = dt.time_id
            WHERE hm.bed_occupancy_rate IS NOT NULL
              {where}
            GROUP BY dt.full_date
            ORDER BY dt.full_date;
        """
        df = query_df(sql, tuple(params))
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"]  = pd.to_numeric(df["y"], errors="coerce")
        return df.dropna()

    # 3b. Forecast with Prophet
    def _prophet_forecast(self, df: pd.DataFrame,
                          periods: int) -> pd.DataFrame:
        m = Prophet(
            yearly_seasonality  = True,
            weekly_seasonality  = False,
            daily_seasonality   = False,
            seasonality_mode    = "additive",
            changepoint_prior_scale = 0.05,
        )
        m.fit(df[["ds", "y"]])
        future   = m.make_future_dataframe(periods=periods, freq="MS")
        forecast = m.predict(future)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

    # 3c. Rolling-average fallback 
    def _rolling_forecast(self, df: pd.DataFrame,
                          periods: int) -> pd.DataFrame:
        last_val  = df["y"].rolling(6).mean().iloc[-1]
        std_val   = df["y"].std()
        last_date = df["ds"].max()
        dates  = pd.date_range(last_date, periods=periods + 1, freq="MS")[1:]
        noise  = np.random.normal(0, std_val * 0.1, periods)
        yhat   = np.clip(last_val + noise, 0, 100)
        return pd.DataFrame({
            "ds":         dates,
            "yhat":       yhat.round(2),
            "yhat_lower": np.clip(yhat - std_val * 0.5, 0, 100).round(2),
            "yhat_upper": np.clip(yhat + std_val * 0.5, 0, 100).round(2),
        })

    #  3d. Main forecast entry point
    def forecast(self,
                 state_code: str | None = None,
                 periods:    int        = 6) -> pd.DataFrame:
        """
        Forecast bed occupancy for the next `periods` months.

        Args:
            state_code: two-letter US state code, or None for nationwide.
            periods:    number of months to forecast.

        Returns DataFrame columns:
            ds (date), yhat (forecast), yhat_lower, yhat_upper,
            is_forecast (bool), alert_level (str)
        """
        df_hist = self._fetch_occupancy(state_code)

        if df_hist.empty:
            print("[WARN] No occupancy data — returning empty forecast.")
            return pd.DataFrame()

        if PROPHET_OK and len(df_hist) >= 24:
            print(f"[Prophet] Forecasting {periods} months ...")
            df_fore = self._prophet_forecast(df_hist, periods)
        else:
            print(f"[Fallback] Rolling forecast for {periods} months ...")
            df_fore = self._rolling_forecast(df_hist, periods)

        # Tag rows
        df_hist_out = df_hist.rename(columns={"y": "yhat"}).copy()
        df_hist_out["yhat_lower"] = df_hist_out["yhat"]
        df_hist_out["yhat_upper"] = df_hist_out["yhat"]
        df_hist_out["is_forecast"] = False

        df_fore["is_forecast"] = True

        result = pd.concat([df_hist_out, df_fore], ignore_index=True)

        # Alert levels
        result["alert_level"] = pd.cut(
            result["yhat"],
            bins  = [0,   70,    85,    95,   100],
            labels= ["Normal", "Elevated", "High", "Critical"],
            right = True,
        )
        return result

    # 3e. Multi-state forecast comparison
    def multi_state_forecast(self,
                             state_codes: list[str],
                             periods:     int = 6) -> pd.DataFrame:
        """
        Run forecasts for multiple states and return a combined DataFrame.

        Returns DataFrame columns:
            state_code + all columns from forecast()
        """
        frames = []
        for sc in state_codes:
            df = self.forecast(sc, periods)
            if not df.empty:
                df["state_code"] = sc
                frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # 3f. Capacity alert summary
    def capacity_alerts(self, year: int = 2023) -> pd.DataFrame:
        """
        Returns states with average bed occupancy > 85% (high risk) for a year.

        Returns DataFrame columns:
            state_code, state_name, avg_occupancy,
            months_above_85, risk_tier
        """
        sql = """
            SELECT
                dl.state_code,
                dl.state_name,
                ROUND(AVG(hm.bed_occupancy_rate), 2)           AS avg_occupancy,
                SUM(CASE WHEN hm.bed_occupancy_rate > 85
                         THEN 1 ELSE 0 END)                    AS months_above_85,
                CASE
                    WHEN AVG(hm.bed_occupancy_rate) >= 95 THEN 'Critical'
                    WHEN AVG(hm.bed_occupancy_rate) >= 85 THEN 'High'
                    WHEN AVG(hm.bed_occupancy_rate) >= 70 THEN 'Elevated'
                    ELSE 'Normal'
                END                                            AS risk_tier
            FROM fact_hospital_metrics hm
            JOIN dim_location dl ON hm.location_id = dl.location_id
            JOIN dim_time     dt ON hm.time_id     = dt.time_id
            WHERE dt.year = %s
              AND hm.bed_occupancy_rate IS NOT NULL
            GROUP BY dl.state_code, dl.state_name
            ORDER BY avg_occupancy DESC;
        """
        return query_df(sql, (year,))


# SELF-TEST  (python 3_analytics_engine.py)

def run_self_test():
    sep = "─" * 60

    # Feature 1 
    print(f"\n{sep}\nFEATURE 1 — Patient Flow Monitor\n{sep}")
    pfm = PatientFlowMonitor()

    trend = pfm.monthly_noshow_trend(start_year=2020, end_year=2022)
    print(f"monthly_noshow_trend(): {len(trend)} rows")
    print(trend.head(3).to_string(index=False))

    regional = pfm.regional_flow_summary(year=2022)
    print(f"\nregional_flow_summary(2022):\n{regional.to_string(index=False)}")

    age_grp = pfm.age_group_noshow(year=2022)
    print(f"\nage_group_noshow(2022):\n{age_grp.to_string(index=False)}")

    snapshot = pfm.realtime_snapshot()
    print(f"\nrealtime_snapshot(): {snapshot}")

    # Feature 2 
    print(f"\n{sep}\nFEATURE 2 — ER Wait Predictor\n{sep}")
    predictor = ERWaitPredictor()
    metrics   = predictor.train()
    print(f"train() metrics: {metrics}")

    scenario = {
        "age": 52, "gender": "M", "sms_received": 1,
        "wait_days": 2, "month": 8, "season": "Summer",
        "region": "South", "bed_occupancy_rate": 88.5,
        "total_er_visits": 65000,
    }
    result = predictor.predict(scenario)
    print(f"\npredict(scenario): {result}")

    heatmap = predictor.state_er_heatmap(year=2022)
    print(f"\nstate_er_heatmap(2022): {len(heatmap)} states")
    print(heatmap.head(5).to_string(index=False))

    fi = predictor.feature_importance()
    print(f"\nfeature_importance():\n{fi.to_string(index=False)}")

    # Feature 3 
    print(f"\n{sep}\nFEATURE 3 — Bed Occupancy Forecast\n{sep}")
    forecaster = BedOccupancyForecaster()

    fc = forecaster.forecast(state_code="CA", periods=6)
    print(f"forecast(CA, 6): {len(fc)} rows — future only:")
    future_rows = fc[fc["is_forecast"] == True]
    print(future_rows[["ds", "yhat", "yhat_lower", "yhat_upper",
                        "alert_level"]].to_string(index=False))

    alerts = forecaster.capacity_alerts(year=2022)
    print(f"\ncapacity_alerts(2022): {len(alerts)} states")
    print(alerts.head(8).to_string(index=False))

    print(f"\n{sep}\n[DONE] All three features operational.\n{sep}")


if __name__ == "__main__":
    run_self_test()
    