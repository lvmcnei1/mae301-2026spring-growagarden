from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import requests


OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'


def load_weather_csv(path: str | Path) -> pd.DataFrame:
    weather_df = pd.read_csv(path)
    weather_df['date'] = pd.to_datetime(weather_df['date']).dt.date
    return weather_df


def fetch_open_meteo_forecast(
    latitude: float,
    longitude: float,
    days: int = 7,
    timezone: str = 'auto',
    timeout: int = 20,
) -> pd.DataFrame:
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'daily': 'temperature_2m_mean,precipitation_sum,et0_fao_evapotranspiration',
        'timezone': timezone,
        'forecast_days': days,
    }
    response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if 'daily' not in payload:
        raise ValueError('Open-Meteo response missing daily forecast payload.')
    daily = payload['daily']
    weather_df = pd.DataFrame(
        {
            'date': pd.to_datetime(daily['time']).date,
            'temperature_2m_mean_c': daily['temperature_2m_mean'],
            'precipitation_sum_mm': daily['precipitation_sum'],
            'et0_fao_evapotranspiration_mm': daily['et0_fao_evapotranspiration'],
        }
    )
    return weather_df


def summarize_weather(weather_df: Optional[pd.DataFrame]) -> dict[str, float]:
    if weather_df is None or weather_df.empty:
        return {
            'avg_temp_c': 25.0,
            'rain_mm_week': 0.0,
            'et0_mm_week': 25.0,
        }
    week_df = weather_df.head(7).copy()
    return {
        'avg_temp_c': float(week_df['temperature_2m_mean_c'].mean()),
        'rain_mm_week': float(week_df['precipitation_sum_mm'].sum()),
        'et0_mm_week': float(week_df['et0_fao_evapotranspiration_mm'].sum()),
    }
