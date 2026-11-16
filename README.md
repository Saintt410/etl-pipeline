# Weather ETL Pipeline

A small data pipeline that pulls daily weather for four cities, cleans it, saves it to a SQLite database, and answers questions with SQL.

## What it does

1. **Extract** — downloads daily temperature and rainfall for Tallinn, London, New York and Tokyo from the free Open-Meteo API.
2. **Transform** — renames columns, drops rows with missing values, and adds two derived columns: `temp_avg` and `is_rainy`.
3. **Load** — writes the data into a SQLite database, using `(city, date)` as the primary key so rerunning the script never creates duplicates.
4. **Analyse** — runs SQL queries for average temperature per city, total rainfall, rainy days, the wettest day, and a 7-day rolling average.

## Why I built it

I wanted to practise the full pipeline rather than just cleaning a CSV someone else prepared. The interesting parts for me were the API request, deciding which rows to drop, and making the load step safe to run twice.

## Tech used

- Python 3
- `requests` for the API call
- `pandas` for cleaning and shaping the data
- SQLite for storage
- SQL for the analysis

## How to run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 etl.py
```

To pull a different length of history:

```bash
python3 etl.py --days 14
```

The database file `weather.db` is created locally and is not committed to Git.

## What it found

From the most recent run:

- Tokyo had the highest average temperature.
- Tokyo had the most total rainfall.
- London had the most rainy days.

Run the script to see the exact numbers in your own output.

## Project structure

```text
etl-pipeline/
├── etl.py            # extract, transform, load and analyse
├── requirements.txt  # dependencies
├── .gitignore        # keeps .venv and the database out of Git
└── README.md
```

## Possible next steps

- Add more cities or a humidity column.
- Schedule the script with GitHub Actions so it updates automatically.
- Plot the 7-day rolling average as a chart.
- Write tests for the transform step.
