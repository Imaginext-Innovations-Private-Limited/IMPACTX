
import csv
from datetime import datetime, timezone
from pathlib import Path

from app.database import db


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data" / "water_quality"

CHEMICAL_FILE = (
    DATA_DIR / "swq_chemical_parameter_manual_cpcb_ka_2021_2025.csv"
)

PHYSICAL_FILE = (
    DATA_DIR / "swq_physical_parameter_manual_cpcb_ka_2021_2025.csv"
)


def number(value):
    """Convert a CSV value to a number, or None if missing."""
    if value is None or not value.strip():
        return None

    try:
        return float(value)
    except ValueError:
        return None


def read_csv_file(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def make_key(row):
    station = (row.get("Station") or "").strip().upper()
    date_text = (row.get("Data Acquisition Time") or "").strip()

    if not station or not date_text:
        return None

    try:
        measurement_date = datetime.strptime(
            date_text,
            "%d-%m-%Y %H:%M"
        )
    except ValueError:
        return None

    return station, measurement_date


def main():
    print("Reading CPCB Karnataka datasets...")

    chemical_rows = read_csv_file(CHEMICAL_FILE)
    physical_rows = read_csv_file(PHYSICAL_FILE)

    print(f"Chemical records: {len(chemical_rows)}")
    print(f"Physical records: {len(physical_rows)}")

    # Match physical records by station and measurement date.
    physical_lookup = {}

    for row in physical_rows:
        key = make_key(row)

        if key:
            physical_lookup[key] = row

    collection = db["water_readings"]

    imported = 0
    skipped = 0

    for chemical in chemical_rows:
        key = make_key(chemical)

        if not key:
            skipped += 1
            continue

        station, measurement_date = key

        physical = physical_lookup.get(key, {})

        latitude = number(chemical.get("Latitude"))
        longitude = number(chemical.get("Longitude"))

        if latitude is None or longitude is None:
            skipped += 1
            continue

        # Store verified historical measurements.
        reading = {
            "lake_name": (
                chemical.get("Station") or ""
            ).strip(),

            "station": station,
            "agency": chemical.get("Agency"),
            "state": chemical.get("State"),
            "district": chemical.get("District"),

            "latitude": latitude,
            "longitude": longitude,

            "ph": number(
                chemical.get("Potential of Hydrogen (pH)")
            ),

            "dissolved_oxygen": number(
                chemical.get("Dissolved oxygen (mg/L)")
            ),

            "turbidity": number(
                physical.get("Turbidity (NTU)")
            ),

            "temperature": number(
                physical.get("Temperature (ºC)")
            ),

            "electrical_conductivity": number(
                physical.get("Electric Conductivity (μS/cm)")
            ),

            "total_dissolved_solids": number(
                chemical.get("Total Dissolved Solids (mg/L)")
            ),

            "measurement_date": measurement_date,

            "source": "CPCB",
            "data_type": "historical",
            "dataset_year": 2021,

            "created_at": datetime.now(timezone.utc)
        }

        # Avoid inserting the same historical record twice.
        collection.update_one(
            {
                "source": "CPCB",
                "station": station,
                "measurement_date": measurement_date
            },
            {
                "$set": reading
            },
            upsert=True
        )

        imported += 1

    print("\nCPCB import completed.")
    print(f"Records processed: {imported}")
    print(f"Records skipped: {skipped}")
    print("MongoDB collection: water_readings")


if __name__ == "__main__":
    main()
