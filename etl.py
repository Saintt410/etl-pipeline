"""Weather ETL pipeline: Extract from Open-Meteo, Transform with pandas, Load into SQLite."""
import argparse
import sqlite3
from datetime import date, timedelta

import pandas as pd
import requests

CITIES = {
    "Tallinn": (59.44, 24.75),
    "London": (51.51, -0.13),
    "New York": (40.71, -74.01),
    "Tokyo": (35.68, 139.69),
}
API = "https://archive-api.open-meteo.com/v1/archive"
DB_PATH = "weather.db"


# ---------- EXTRACT ----------
def extract(city, lat, lon, start, end):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
    }
    resp = requests.get(API, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["daily"])
    df["city"] = city
    return df


# ---------- TRANSFORM ----------
def transform(df):
    df = df.rename(columns={
        "time": "date",
        "temperature_2m_max": "temp_max",
        "temperature_2m_min": "temp_min",
        "precipitation_sum": "rain_mm",
    })
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df = df.dropna(subset=["temp_max", "temp_min"])
    df["rain_mm"] = df["rain_mm"].fillna(0)
    df["temp_avg"] = ((df["temp_max"] + df["temp_min"]) / 2).round(1)
    df["is_rainy"] = (df["rain_mm"] > 1).astype(int)
    return df[["city", "date", "temp_min", "temp_max", "temp_avg", "rain_mm", "is_rainy"]]


# ---------- LOAD ----------
def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            city      TEXT NOT NULL,
            date      TEXT NOT NULL,
            temp_min  REAL,
            temp_max  REAL,
            temp_avg  REAL,
            rain_mm   REAL,
            is_rainy  INTEGER,
            PRIMARY KEY (city, date)
        )
    """)


def load(df, conn):
    rows = list(df.itertuples(index=False, name=None))
    conn.executemany(
        "INSERT OR REPLACE INTO weather VALUES (?, ?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()
    return len(rows)


# ---------- ANALYZE (SQL) ----------
QUERIES = {
    "Average temperature and rainy days per city": """
        SELECT city,
               ROUND(AVG(temp_avg), 1) AS avg_temp,
               MAX(temp_max)           AS hottest,
               MIN(temp_min)           AS coldest,
               SUM(is_rainy)           AS rainy_days,
               ROUND(SUM(rain_mm), 1)  AS total_rain_mm
        FROM weather
        GROUP BY city
        ORDER BY avg_temp DESC
    """,
    "Wettest day in each city": """
        SELECT city, date, rain_mm
        FROM (
            SELECT city, date, rain_mm,
                   RANK() OVER (PARTITION BY city ORDER BY rain_mm DESC) AS rnk
            FROM weather
        )
        WHERE rnk = 1
    """,
    "7-day rolling average temperature (last 5 days per city)": """
        SELECT city, date, temp_avg, rolling_7d
        FROM (
            SELECT city, date, temp_avg,
                   ROUND(AVG(temp_avg) OVER (
                       PARTITION BY city ORDER BY date
                       ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                   ), 1) AS rolling_7d,
                   ROW_NUMBER() OVER (PARTITION BY city ORDER BY date DESC) AS rn
            FROM weather
        )
        WHERE rn <= 5
        ORDER BY city, date
    """,
}


def analyze(conn):
    for title, sql in QUERIES.items():
        print(f"\n=== {title} ===")
        print(pd.read_sql_query(sql, conn).to_string(index=False))


# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser(description="Weather ETL pipeline")
    parser.add_argument("--days", type=int, default=30, help="How many days of history to fetch")
    parser.add_argument("--db", default=DB_PATH, help="SQLite database file")
    args = parser.parse_args()

    end = date.today() - timedelta(days=2)   # archive API lags ~2 days
    start = end - timedelta(days=args.days)

    print(f"Extracting {start} to {end} for {len(CITIES)} cities...")
    raw = pd.concat(
        [extract(c, lat, lon, start, end) for c, (lat, lon) in CITIES.items()],
        ignore_index=True,
    )
    clean = transform(raw)
    print(f"Transformed {len(clean)} rows")

    with sqlite3.connect(args.db) as conn:
        create_table(conn)
        n = load(clean, conn)
        total = conn.execute("SELECT COUNT(*) FROM weather").fetchone()[0]
        print(f"Loaded {n} rows. Table now has {total} rows.")
        analyze(conn)


if __name__ == "__main__":
    main()
