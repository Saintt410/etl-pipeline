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
    df = df[["city", "date", "temp_min", "temp_max", "temp_avg", "rain_mm", "is_rainy"]]
    return df


end = date.today() - timedelta(days=2)
start = end - timedelta(days=30)
frames = [extract(c, lat, lon, start, end) for c, (lat, lon) in CITIES.items()]
raw = pd.concat(frames, ignore_index=True)
clean = transform(raw)
print(clean.groupby("city").head(3))
print("Rows per city:")
print(clean["city"].value_counts())

