# ==============================
# Grow A Garden Colab Demo (robust)
# ==============================

from pathlib import Path
import sys
import json
import subprocess

import pandas as pd

from google.colab import drive
drive.mount('/content/drive')

PROJECT_ROOT = Path("/content/drive/MyDrive/phase2")
print(f"PROJECT_ROOT = {PROJECT_ROOT}")

if not PROJECT_ROOT.exists():
    raise FileNotFoundError(f"PROJECT_ROOT does not exist: {PROJECT_ROOT}")

# Try both possible layouts:
# 1) src/growagarden/*.py
# 2) src/*.py
SRC_PATH = PROJECT_ROOT / "src"
PACKAGE_PATH = SRC_PATH / "growagarden"

if PACKAGE_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))
    import_style = "package"
elif SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))
    import_style = "flat"
else:
    raise FileNotFoundError(f"Could not find src folder inside {PROJECT_ROOT}")

print(f"Import style = {import_style}")

requirements = PROJECT_ROOT / "requirements.txt"
if requirements.exists():
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(requirements)])
else:
    print("No requirements.txt found, skipping install.")

if import_style == "package":
    from growagarden.data_loader import build_plant_profiles, lookup_zip_metadata
    from growagarden.scheduler import format_markdown_summary, plan_garden
    from growagarden.weather import fetch_open_meteo_forecast, load_weather_csv
else:
    from data_loader import build_plant_profiles, lookup_zip_metadata
    from scheduler import format_markdown_summary, plan_garden
    from weather import fetch_open_meteo_forecast, load_weather_csv

# ------------------------------
# Demo settings
# ------------------------------
PLANNING_DATE = "2026-04-12"
ZONE = "9b"
ZIPCODE = None
GARDEN_AREA_SQFT = 48
SUN_HOURS = 8
WATERING_PREFERENCE = "medium"
TOP_K = 5
SELECTED_CROPS = None
WEATHER_CSV = None
USE_LIVE_WEATHER = False

OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "demo_run"

# ------------------------------
# Build plant profiles
# ------------------------------
print("🌱 Building plant profiles...")
build_plant_profiles(save=True)

# ------------------------------
# Optional weather / location
# ------------------------------
weather_df = None
location_meta = None

if ZIPCODE:
    location_meta = lookup_zip_metadata(ZIPCODE)
    if location_meta is None:
        raise SystemExit(f"ZIP code {ZIPCODE} not found.")

if WEATHER_CSV:
    weather_df = load_weather_csv(WEATHER_CSV)
elif USE_LIVE_WEATHER:
    if location_meta is None:
        raise SystemExit("Live weather requires ZIPCODE.")
    weather_df = fetch_open_meteo_forecast(
        location_meta["latitude"],
        location_meta["longitude"]
    )

# ------------------------------
# Run planner
# ------------------------------
print("🌿 Generating garden plan...")

result = plan_garden(
    planning_date=PLANNING_DATE,
    zone=ZONE,
    garden_area_sqft=GARDEN_AREA_SQFT,
    sun_hours=SUN_HOURS,
    watering_preference=WATERING_PREFERENCE,
    selected_crops=SELECTED_CROPS,
    weather_df=weather_df,
    top_k=TOP_K,
)

# ------------------------------
# Save outputs
# ------------------------------
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

result["recommendations"].to_csv(OUTPUT_DIR / "recommendations.csv", index=False)
result["schedule"].to_csv(OUTPUT_DIR / "schedule.csv", index=False)
(OUTPUT_DIR / "summary.md").write_text(format_markdown_summary(result), encoding="utf-8")

context_payload = dict(result["context"])
context_payload["location_meta"] = location_meta
(OUTPUT_DIR / "context.json").write_text(
    json.dumps(context_payload, indent=2),
    encoding="utf-8"
)

# ------------------------------
# Display results
# ------------------------------
print("\n==============================")
print("GROW A GARDEN DEMO RESULT")
print("==============================\n")

print(format_markdown_summary(result))
print(f"\n💾 Saved outputs to: {OUTPUT_DIR}")

print("\n--- Recommendations ---")
display(result["recommendations"])

print("\n--- Schedule ---")
display(result["schedule"])
