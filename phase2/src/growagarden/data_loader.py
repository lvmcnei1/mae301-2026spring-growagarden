from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
RAW_PLANT_PATH = DATA_DIR / 'raw' / 'garden_vegetables.csv'
ZIP_PATH = DATA_DIR / 'raw' / 'zipcodes.csv'
OVERRIDE_PATH = DATA_DIR / 'manual' / 'plant_profile_overrides.csv'
ZONE_FROST_PATH = DATA_DIR / 'manual' / 'zone_frost_heuristics.csv'
PROCESSED_PROFILE_PATH = DATA_DIR / 'processed' / 'plant_profiles.csv'


def _ensure_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f'Missing required data file: {path}')


def load_raw_plant_dataset() -> pd.DataFrame:
    _ensure_exists(RAW_PLANT_PATH)
    return pd.read_csv(RAW_PLANT_PATH)


def load_manual_overrides() -> pd.DataFrame:
    _ensure_exists(OVERRIDE_PATH)
    return pd.read_csv(OVERRIDE_PATH)


def load_zone_frost_heuristics() -> pd.DataFrame:
    _ensure_exists(ZONE_FROST_PATH)
    return pd.read_csv(ZONE_FROST_PATH)


def load_zipcodes() -> pd.DataFrame:
    _ensure_exists(ZIP_PATH)
    df = pd.read_csv(ZIP_PATH, dtype={'zipcode': str})
    df['zipcode'] = df['zipcode'].str.zfill(5)
    return df


def lookup_zip_metadata(zipcode: str) -> Optional[dict[str, Any]]:
    zipcode = str(zipcode).zfill(5)
    df = load_zipcodes()
    match = df.loc[df['zipcode'] == zipcode]
    if match.empty:
        return None
    row = match.iloc[0]
    return {
        'zipcode': zipcode,
        'city': row.get('city'),
        'state': row.get('state'),
        'latitude': float(row['latitude']),
        'longitude': float(row['longitude']),
    }


def build_plant_profiles(save: bool = True) -> pd.DataFrame:
    raw_df = load_raw_plant_dataset()
    raw_subset = raw_df[
        [
            'name',
            'description',
            'optimal_sun',
            'optimal_soil',
            'when_to_plant',
            'watering',
            'harvesting',
            'spacing',
            'growing_from_seed',
            'transplanting',
            'other_care',
        ]
    ].copy()

    manual_df = load_manual_overrides()
    profile_df = manual_df.merge(raw_subset, on='name', how='left', validate='one_to_one')
    profile_df['slug'] = profile_df['name'].str.lower().str.replace(' ', '_', regex=False)
    profile_df = profile_df.sort_values(['category', 'name']).reset_index(drop=True)

    numeric_cols = [
        'zone_min',
        'zone_max',
        'min_sun_hours',
        'space_sqft_per_plant',
        'base_water_inches_per_week',
        'hot_water_inches_per_week',
        'days_to_maturity',
        'spring_direct_start_offset_days',
        'spring_direct_end_offset_days',
        'spring_transplant_start_offset_days',
        'spring_transplant_end_offset_days',
        'fall_direct_start_offset_days',
        'fall_direct_end_offset_days',
        'fall_transplant_start_offset_days',
        'fall_transplant_end_offset_days',
        'indoor_seed_start_offset_days',
        'indoor_seed_end_offset_days',
    ]
    for col in numeric_cols:
        profile_df[col] = pd.to_numeric(profile_df[col], errors='coerce')

    if save:
        PROCESSED_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        profile_df.to_csv(PROCESSED_PROFILE_PATH, index=False)
    return profile_df


def load_plant_profiles(auto_build: bool = True) -> pd.DataFrame:
    if not PROCESSED_PROFILE_PATH.exists():
        if not auto_build:
            raise FileNotFoundError(f'Processed plant profiles not found: {PROCESSED_PROFILE_PATH}')
        return build_plant_profiles(save=True)
    return pd.read_csv(PROCESSED_PROFILE_PATH)
