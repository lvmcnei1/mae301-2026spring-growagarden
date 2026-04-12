from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from growagarden.data_loader import build_plant_profiles, lookup_zip_metadata
from growagarden.scheduler import format_markdown_summary, plan_garden
from growagarden.weather import fetch_open_meteo_forecast, load_weather_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate a planting and watering plan.')
    parser.add_argument('--planning-date', default='2026-04-12')
    parser.add_argument('--zone', default=None)
    parser.add_argument('--zipcode', default=None)
    parser.add_argument('--garden-area-sqft', type=float, default=48)
    parser.add_argument('--sun-hours', type=float, default=8)
    parser.add_argument('--watering-preference', choices=['low', 'medium', 'high'], default='medium')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--weather-csv', default=None)
    parser.add_argument('--use-live-weather', action='store_true')
    parser.add_argument('--selected-crops', nargs='*', default=None)
    parser.add_argument('--output-dir', default=str(PROJECT_ROOT / 'artifacts' / 'demo_run'))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_plant_profiles(save=True)

    zone = args.zone
    weather_df: pd.DataFrame | None = None
    location_meta = None

    if args.zipcode:
        location_meta = lookup_zip_metadata(args.zipcode)
        if location_meta is None:
            raise SystemExit(f'ZIP code {args.zipcode} not found in local ZIP metadata file.')

    if args.weather_csv:
        weather_df = load_weather_csv(args.weather_csv)
    elif args.use_live_weather:
        if location_meta is None:
            raise SystemExit('--use-live-weather requires --zipcode so latitude/longitude can be resolved.')
        weather_df = fetch_open_meteo_forecast(location_meta['latitude'], location_meta['longitude'])

    if zone is None:
        if args.zipcode is None:
            raise SystemExit('Provide --zone or --zipcode. For reproducible offline use, --zone is recommended.')
        raise SystemExit('Live ZIP-to-zone lookup is not used in the offline demo. Pass --zone explicitly for Phase 2 reproducibility.')

    result = plan_garden(
        planning_date=args.planning_date,
        zone=zone,
        garden_area_sqft=args.garden_area_sqft,
        sun_hours=args.sun_hours,
        watering_preference=args.watering_preference,
        selected_crops=args.selected_crops,
        weather_df=weather_df,
        top_k=args.top_k,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result['recommendations'].to_csv(output_dir / 'recommendations.csv', index=False)
    result['schedule'].to_csv(output_dir / 'schedule.csv', index=False)
    (output_dir / 'summary.md').write_text(format_markdown_summary(result), encoding='utf-8')
    context_payload = dict(result['context'])
    context_payload['location_meta'] = location_meta
    (output_dir / 'context.json').write_text(json.dumps(context_payload, indent=2), encoding='utf-8')

    print(format_markdown_summary(result))
    print(f'\nSaved outputs to {output_dir}')


if __name__ == '__main__':
    main()
