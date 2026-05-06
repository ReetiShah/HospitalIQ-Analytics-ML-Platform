"""
1_db_setup.py
=============
Creates the hospital_analytics MySQL database and all tables.
Run this FIRST before any other script.
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

# Connection config
DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", "3306")),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", "reeti2212"),
}
DB_NAME = "hospital_analytics"


# DDL statements
DDL = [

    # 1. Dimension: location
    """
    CREATE TABLE IF NOT EXISTS dim_location (
        location_id    INT AUTO_INCREMENT PRIMARY KEY,
        state_code     CHAR(2)        NOT NULL UNIQUE,
        state_name     VARCHAR(50)    NOT NULL,
        region         VARCHAR(20),
        median_income  DECIMAL(10,2),
        uninsured_rate DECIMAL(5,2),
        INDEX idx_state (state_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # 2. Dimension: time
    """
    CREATE TABLE IF NOT EXISTS dim_time (
        time_id    INT AUTO_INCREMENT PRIMARY KEY,
        full_date  DATE     NOT NULL UNIQUE,
        year       SMALLINT NOT NULL,
        month      TINYINT  NOT NULL,
        quarter    TINYINT  NOT NULL,
        season     VARCHAR(10),
        INDEX idx_year_month (year, month)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # 3. Dimension: disease
    """
    CREATE TABLE IF NOT EXISTS dim_disease (
        disease_id       INT AUTO_INCREMENT PRIMARY KEY,
        disease_category VARCHAR(100) NOT NULL,
        icd10_code       VARCHAR(10),
        chronic_flag     TINYINT(1)   DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # 4. Fact: appointments  (Kaggle No-Show dataset)
    """
    CREATE TABLE IF NOT EXISTS fact_appointments (
        appt_id      INT AUTO_INCREMENT PRIMARY KEY,
        location_id  INT           NOT NULL,
        time_id      INT           NOT NULL,
        age          TINYINT UNSIGNED,
        gender       CHAR(1),
        no_show      TINYINT(1)    NOT NULL DEFAULT 0,
        sms_received TINYINT(1)    DEFAULT 0,
        wait_days    SMALLINT,
        neighbourhood VARCHAR(100),
        FOREIGN KEY (location_id) REFERENCES dim_location(location_id),
        FOREIGN KEY (time_id)     REFERENCES dim_time(time_id),
        INDEX idx_noshow   (no_show),
        INDEX idx_loc_time (location_id, time_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    # 5. Fact: hospital metrics  (HCAHPS + HCUP + CDC + Mortality + CMS)
    """
    CREATE TABLE IF NOT EXISTS fact_hospital_metrics (
        metric_id           INT AUTO_INCREMENT PRIMARY KEY,
        location_id         INT          NOT NULL,
        time_id             INT          NOT NULL,
        disease_id          INT,
        hcahps_score        DECIMAL(5,2),
        er_wait_minutes     DECIMAL(6,1),
        total_er_visits     INT,
        bed_occupancy_rate  DECIMAL(5,2),
        total_admissions    INT,
        avg_length_of_stay  DECIMAL(4,1),
        mortality_rate      DECIMAL(6,2),
        chronic_prevalence  DECIMAL(5,2),
        FOREIGN KEY (location_id) REFERENCES dim_location(location_id),
        FOREIGN KEY (time_id)     REFERENCES dim_time(time_id),
        FOREIGN KEY (disease_id)  REFERENCES dim_disease(disease_id),
        INDEX idx_loc_time (location_id, time_id),
        INDEX idx_disease  (disease_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


#  Helpers 
def get_connection(database: str | None = None):
    cfg = dict(DB_CONFIG)
    if database:
        cfg["database"] = database
    return mysql.connector.connect(**cfg)


def create_database(cursor):
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    print(f"[OK] Database '{DB_NAME}' ready.")


def create_tables(cursor):
    for stmt in DDL:
        # extract table name for logging
        name = [w for w in stmt.split() if w.upper() not in
                ("CREATE", "TABLE", "IF", "NOT", "EXISTS", "")][0]
        cursor.execute(stmt)
        print(f"[OK] Table {name} created / verified.")


# ── Entry point
def main():
    try:
        # Step 1: create DB
        conn = get_connection()
        cur  = conn.cursor()
        create_database(cur)
        conn.commit()
        cur.close()
        conn.close()

        # Step 2: create tables
        conn = get_connection(DB_NAME)
        cur  = conn.cursor()
        create_tables(cur)
        conn.commit()
        print("\n[DONE] Schema setup complete.")

    except Error as e:
        print(f"[ERROR] {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()