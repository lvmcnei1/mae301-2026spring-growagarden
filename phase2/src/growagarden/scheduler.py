from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

import pandas as pd

from .data_loader import load_plant_profiles, load_zone_frost_heuristics
from .weather import summarize_weather


WATERING_CAPACITY = {
    'low': 1.0,
    'medium': 1.4,
    'high': 2.1,
}


@dataclass
class Context:
    planning_date: date
    zone: str
    zone_numeric: float
    last_frost: date
    first_frost: date
    garden_area_sqft: float
    sun_hours: float
    watering_preference: str


WINDOW_SPECS = [
    ('indoor_seed', 'indoor_seed_start_offset_days', 'indoor_seed_end_offset_days', 'last_frost', 'Start indoors'),
    ('spring_direct', 'spring_direct_start_offset_days', 'spring_direct_end_offset_days', 'last_frost', 'Direct sow outdoors'),
    ('spring_transplant', 'spring_transplant_start_offset_days', 'spring_transplant_end_offset_days', 'last_frost', 'Transplant outdoors'),
    ('fall_direct', 'fall_direct_start_offset_days', 'fall_direct_end_offset_days', 'first_frost', 'Direct sow for fall'),
    ('fall_transplant', 'fall_transplant_start_offset_days', 'fall_transplant_end_offset_days', 'first_frost', 'Transplant for fall'),
]


def _to_date(value: str | date | datetime) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), '%Y-%m-%d').date()


def normalize_zone(zone: str) -> str:
    zone = str(zone).strip().lower().replace(' ', '')
    if not zone:
        raise ValueError('Zone cannot be empty.')
    if zone[-1].isalpha():
        return zone
    return f'{zone}a'


def zone_to_numeric(zone: str) -> float:
    zone = normalize_zone(zone)
    base = float(zone[:-1])
    return base if zone.endswith('a') else base + 0.5


def resolve_frost_dates(
    zone: str,
    year: int,
    last_frost_date: Optional[str | date] = None,
    first_frost_date: Optional[str | date] = None,
) -> tuple[date, date]:
    if last_frost_date and first_frost_date:
        return _to_date(last_frost_date), _to_date(first_frost_date)

    heuristics = load_zone_frost_heuristics()
    zone = normalize_zone(zone)
    row = heuristics.loc[heuristics['zone'].str.lower() == zone]
    if row.empty:
        raise ValueError(f'No frost heuristic found for zone {zone}.')
    mmdd_last = row.iloc[0]['avg_last_spring_frost_mmdd']
    mmdd_first = row.iloc[0]['avg_first_fall_frost_mmdd']
    resolved_last = _to_date(f'{year}-{mmdd_last}') if not last_frost_date else _to_date(last_frost_date)
    resolved_first = _to_date(f'{year}-{mmdd_first}') if not first_frost_date else _to_date(first_frost_date)
    return resolved_last, resolved_first


def _window_from_offsets(base_date: date, start_offset: float, end_offset: float) -> tuple[date, date]:
    start = base_date + timedelta(days=int(start_offset))
    end = base_date + timedelta(days=int(end_offset))
    if start <= end:
        return start, end
    return end, start


def _build_windows(profile: pd.Series, context: Context, for_next_year: bool = False) -> list[dict[str, Any]]:
    year = context.planning_date.year + (1 if for_next_year else 0)
    last_frost, first_frost = resolve_frost_dates(context.zone, year)
    windows: list[dict[str, Any]] = []

    for stage, start_col, end_col, ref_col, action_label in WINDOW_SPECS:
        start_offset = profile.get(start_col)
        end_offset = profile.get(end_col)
        if pd.isna(start_offset) or pd.isna(end_offset):
            continue

        # Keep warm-season fall planting windows only for hotter regions.
        if stage.startswith('fall') and str(profile.get('season')) == 'warm' and context.zone_numeric < 8.0:
            continue

        reference_date = last_frost if ref_col == 'last_frost' else first_frost
        start_date, end_date = _window_from_offsets(reference_date, float(start_offset), float(end_offset))
        windows.append(
            {
                'stage': stage,
                'action_label': action_label,
                'reference': ref_col,
                'start_date': start_date,
                'end_date': end_date,
                'year': year,
            }
        )

    # For next-year search we only need indoor + spring windows.
    if for_next_year:
        windows = [w for w in windows if w['stage'].startswith('indoor') or w['stage'].startswith('spring')]
    return sorted(windows, key=lambda item: (item['start_date'], item['end_date']))


def _find_current_and_next_windows(profile: pd.Series, context: Context) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], list[dict[str, Any]]]:
    windows = _build_windows(profile, context, for_next_year=False)
    next_year_windows = _build_windows(profile, context, for_next_year=True)
    all_windows = windows + next_year_windows

    current = None
    future = []
    for window in all_windows:
        if window['start_date'] <= context.planning_date <= window['end_date']:
            current = window
        elif window['start_date'] > context.planning_date:
            future.append(window)
    next_window = future[0] if future else None
    return current, next_window, all_windows


def _outdoor_anchor_window(all_windows: list[dict[str, Any]], active_or_next: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if active_or_next is None:
        return None
    if active_or_next['stage'] != 'indoor_seed':
        return active_or_next
    future_outdoor = [w for w in all_windows if w['start_date'] >= active_or_next['start_date'] and 'indoor' not in w['stage']]
    return future_outdoor[0] if future_outdoor else None


def _watering_adjustment(profile: pd.Series, weather_df: Optional[pd.DataFrame]) -> dict[str, float]:
    weather = summarize_weather(weather_df)
    base_inches = float(profile['base_water_inches_per_week'])
    hot_inches = float(profile['hot_water_inches_per_week'])

    if weather['avg_temp_c'] >= 29.5 or weather['et0_mm_week'] >= 38:
        target_inches = hot_inches
    elif weather['avg_temp_c'] <= 16 and str(profile['season']) == 'cool':
        target_inches = max(0.7, base_inches - 0.1)
    else:
        target_inches = base_inches

    rain_inches = weather['rain_mm_week'] / 25.4
    irrigation_inches = max(0.0, target_inches - 0.8 * rain_inches)
    if irrigation_inches <= 0.6:
        events_per_week = 2
    elif irrigation_inches <= 1.4:
        events_per_week = 3
    else:
        events_per_week = 4

    gallons_per_sqft = irrigation_inches * 0.623
    gallons_per_plant = gallons_per_sqft * float(profile['space_sqft_per_plant'])
    return {
        'target_inches_per_week': round(target_inches, 2),
        'irrigation_inches_per_week': round(irrigation_inches, 2),
        'events_per_week': float(events_per_week),
        'gallons_per_sqft_per_week': round(gallons_per_sqft, 2),
        'gallons_per_plant_per_week': round(gallons_per_plant, 2),
        'avg_temp_c': round(weather['avg_temp_c'], 1),
        'rain_mm_week': round(weather['rain_mm_week'], 1),
        'et0_mm_week': round(weather['et0_mm_week'], 1),
    }


def _suitability_score(
    profile: pd.Series,
    context: Context,
    current_window: Optional[dict[str, Any]],
    next_window: Optional[dict[str, Any]],
) -> float:
    score = 50.0

    if context.sun_hours >= float(profile['min_sun_hours']):
        score += min(12.0, (context.sun_hours - float(profile['min_sun_hours'])) * 3.0 + 8.0)
    else:
        score -= 25.0 + (float(profile['min_sun_hours']) - context.sun_hours) * 8.0

    if float(profile['zone_min']) <= context.zone_numeric <= float(profile['zone_max']):
        score += 10.0
    else:
        score -= 15.0

    water_limit = WATERING_CAPACITY.get(context.watering_preference, WATERING_CAPACITY['medium'])
    base_water = float(profile['base_water_inches_per_week'])
    if base_water <= water_limit:
        score += 8.0
    else:
        score -= (base_water - water_limit) * 15.0

    if current_window is not None:
        score += 25.0 if current_window['stage'] != 'indoor_seed' else 18.0
    elif next_window is not None:
        days_away = (next_window['start_date'] - context.planning_date).days
        if days_away <= 14:
            score += 12.0
        elif days_away <= 45:
            score += 5.0
        else:
            score -= min(15.0, days_away / 5.0)
    else:
        score -= 20.0

    return round(max(0.0, min(100.0, score)), 1)


def plan_single_crop(
    crop_name: str,
    context: Context,
    profiles_df: Optional[pd.DataFrame] = None,
    weather_df: Optional[pd.DataFrame] = None,
) -> dict[str, Any]:
    profiles = load_plant_profiles() if profiles_df is None else profiles_df
    match = profiles.loc[profiles['name'].str.lower() == crop_name.lower()]
    if match.empty:
        raise ValueError(f'Unknown crop: {crop_name}')
    profile = match.iloc[0]

    current_window, next_window, all_windows = _find_current_and_next_windows(profile, context)
    anchor = _outdoor_anchor_window(all_windows, current_window or next_window)
    score = _suitability_score(profile, context, current_window, next_window)
    watering = _watering_adjustment(profile, weather_df)

    if current_window is not None:
        if current_window['stage'] == 'indoor_seed':
            action_class = 'start_indoors_now'
            action_now = f"Start {profile['name']} indoors now."
        else:
            action_class = 'plant_outdoors_now'
            action_now = f"{current_window['action_label']} now."
    elif next_window is not None:
        action_class = 'wait_for_window'
        action_now = f"Wait until {next_window['start_date'].isoformat()} to {next_window['action_label'].lower()}."
    else:
        action_class = 'not_recommended_now'
        action_now = 'No suitable planting window found in the current planning horizon.'

    if current_window is not None and current_window['stage'] != 'indoor_seed':
        outdoor_date = context.planning_date
    else:
        outdoor_date = None if anchor is None else anchor['start_date']

    harvest_date = None
    if outdoor_date is not None:
        harvest_date = outdoor_date + timedelta(days=int(profile['days_to_maturity']))

    return {
        'name': profile['name'],
        'category': profile['category'],
        'season': profile['season'],
        'score': score,
        'action_class': action_class,
        'action_now': action_now,
        'current_window_stage': None if current_window is None else current_window['stage'],
        'next_window_stage': None if next_window is None else next_window['stage'],
        'current_window_start': None if current_window is None else current_window['start_date'].isoformat(),
        'current_window_end': None if current_window is None else current_window['end_date'].isoformat(),
        'next_window_start': None if next_window is None else next_window['start_date'].isoformat(),
        'next_window_end': None if next_window is None else next_window['end_date'].isoformat(),
        'outdoor_plant_date': None if outdoor_date is None else outdoor_date.isoformat(),
        'estimated_harvest_date': None if harvest_date is None else harvest_date.isoformat(),
        'water_inches_per_week': watering['irrigation_inches_per_week'],
        'water_events_per_week': int(watering['events_per_week']),
        'gallons_per_sqft_per_week': watering['gallons_per_sqft_per_week'],
        'gallons_per_plant_per_week': watering['gallons_per_plant_per_week'],
        'avg_temp_c_used': watering['avg_temp_c'],
        'rain_mm_used': watering['rain_mm_week'],
        'et0_mm_used': watering['et0_mm_week'],
        'min_sun_hours': float(profile['min_sun_hours']),
        'space_sqft_per_plant': float(profile['space_sqft_per_plant']),
        'days_to_maturity': int(profile['days_to_maturity']),
        'description': profile.get('description'),
        'when_to_plant_text': profile.get('when_to_plant'),
        'watering_text': profile.get('watering'),
        'raw_optimal_sun': profile.get('optimal_sun'),
        'raw_spacing': profile.get('spacing'),
        'notes': profile.get('notes'),
    }


def recommend_crops(
    context: Context,
    profiles_df: Optional[pd.DataFrame] = None,
    weather_df: Optional[pd.DataFrame] = None,
    top_k: int = 5,
) -> pd.DataFrame:
    profiles = load_plant_profiles() if profiles_df is None else profiles_df
    plans = [plan_single_crop(name, context, profiles_df=profiles, weather_df=weather_df) for name in profiles['name']]
    rec_df = pd.DataFrame(plans).sort_values(['score', 'name'], ascending=[False, True]).reset_index(drop=True)
    return rec_df.head(top_k)


def _estimated_plants_per_crop(space_sqft_per_plant: float, garden_area_sqft: float, num_crops: int) -> int:
    allocated_area = max(1.0, garden_area_sqft / max(1, num_crops))
    return max(1, int(allocated_area // max(space_sqft_per_plant, 0.1)))


def generate_schedule(
    crop_plans_df: pd.DataFrame,
    context: Context,
    weeks: int = 8,
) -> pd.DataFrame:
    events: list[dict[str, Any]] = []
    horizon_end = context.planning_date + timedelta(days=7 * weeks)

    for _, row in crop_plans_df.iterrows():
        plants = _estimated_plants_per_crop(float(row['space_sqft_per_plant']), context.garden_area_sqft, len(crop_plans_df))
        if row['action_class'] == 'start_indoors_now':
            events.append(
                {
                    'date': context.planning_date.isoformat(),
                    'crop': row['name'],
                    'task': 'start_indoors',
                    'details': f"Start {plants} plants indoors in trays. Keep seed starting mix lightly moist.",
                    'water_inches': None,
                    'gallons_per_sqft': None,
                    'gallons_per_plant': None,
                }
            )
        elif row['action_class'] == 'plant_outdoors_now':
            events.append(
                {
                    'date': context.planning_date.isoformat(),
                    'crop': row['name'],
                    'task': 'plant_outdoors',
                    'details': f"Plant outdoors this week. Estimated space: {plants} plants.",
                    'water_inches': None,
                    'gallons_per_sqft': None,
                    'gallons_per_plant': None,
                }
            )
        elif pd.notna(row['next_window_start']):
            next_date = _to_date(row['next_window_start'])
            if next_date <= horizon_end:
                events.append(
                    {
                        'date': next_date.isoformat(),
                        'crop': row['name'],
                        'task': 'next_planting_window',
                        'details': row['action_now'],
                        'water_inches': None,
                        'gallons_per_sqft': None,
                        'gallons_per_plant': None,
                    }
                )

        outdoor_date = None if pd.isna(row['outdoor_plant_date']) else _to_date(row['outdoor_plant_date'])
        if outdoor_date is None or outdoor_date > horizon_end:
            continue

        first_week = max(outdoor_date, context.planning_date)
        week_cursor = first_week
        while week_cursor <= horizon_end:
            events.append(
                {
                    'date': week_cursor.isoformat(),
                    'crop': row['name'],
                    'task': 'water',
                    'details': f"Water about {int(row['water_events_per_week'])} times this week.",
                    'water_inches': row['water_inches_per_week'],
                    'gallons_per_sqft': row['gallons_per_sqft_per_week'],
                    'gallons_per_plant': row['gallons_per_plant_per_week'],
                }
            )
            week_cursor += timedelta(days=7)

        harvest_date = None if pd.isna(row['estimated_harvest_date']) else _to_date(row['estimated_harvest_date'])
        if harvest_date is not None and harvest_date <= horizon_end:
            events.append(
                {
                    'date': harvest_date.isoformat(),
                    'crop': row['name'],
                    'task': 'harvest_estimate',
                    'details': 'Estimated first harvest window begins around this date.',
                    'water_inches': None,
                    'gallons_per_sqft': None,
                    'gallons_per_plant': None,
                }
            )

    schedule_df = pd.DataFrame(events)
    if schedule_df.empty:
        return pd.DataFrame(columns=['date', 'crop', 'task', 'details', 'water_inches', 'gallons_per_sqft', 'gallons_per_plant'])
    schedule_df = schedule_df.sort_values(['date', 'crop', 'task']).reset_index(drop=True)
    return schedule_df


def _context_from_inputs(
    planning_date: str | date,
    zone: str,
    garden_area_sqft: float,
    sun_hours: float,
    watering_preference: str,
    last_frost_date: Optional[str | date] = None,
    first_frost_date: Optional[str | date] = None,
) -> Context:
    resolved_date = _to_date(planning_date)
    normalized_zone = normalize_zone(zone)
    last_frost, first_frost = resolve_frost_dates(normalized_zone, resolved_date.year, last_frost_date, first_frost_date)
    return Context(
        planning_date=resolved_date,
        zone=normalized_zone,
        zone_numeric=zone_to_numeric(normalized_zone),
        last_frost=last_frost,
        first_frost=first_frost,
        garden_area_sqft=float(garden_area_sqft),
        sun_hours=float(sun_hours),
        watering_preference=str(watering_preference).lower(),
    )


def plan_garden(
    planning_date: str | date,
    zone: str,
    garden_area_sqft: float,
    sun_hours: float,
    watering_preference: str = 'medium',
    selected_crops: Optional[Iterable[str]] = None,
    weather_df: Optional[pd.DataFrame] = None,
    top_k: int = 5,
    last_frost_date: Optional[str | date] = None,
    first_frost_date: Optional[str | date] = None,
    profiles_df: Optional[pd.DataFrame] = None,
) -> dict[str, Any]:
    profiles = load_plant_profiles() if profiles_df is None else profiles_df
    context = _context_from_inputs(
        planning_date=planning_date,
        zone=zone,
        garden_area_sqft=garden_area_sqft,
        sun_hours=sun_hours,
        watering_preference=watering_preference,
        last_frost_date=last_frost_date,
        first_frost_date=first_frost_date,
    )

    if selected_crops:
        crop_names = list(selected_crops)
        plan_rows = [plan_single_crop(name, context, profiles_df=profiles, weather_df=weather_df) for name in crop_names]
        recommendations_df = pd.DataFrame(plan_rows).sort_values(['score', 'name'], ascending=[False, True]).reset_index(drop=True)
    else:
        recommendations_df = recommend_crops(context, profiles_df=profiles, weather_df=weather_df, top_k=top_k)

    schedule_df = generate_schedule(recommendations_df, context=context, weeks=8)
    return {
        'context': {
            'planning_date': context.planning_date.isoformat(),
            'zone': context.zone,
            'last_frost': context.last_frost.isoformat(),
            'first_frost': context.first_frost.isoformat(),
            'garden_area_sqft': context.garden_area_sqft,
            'sun_hours': context.sun_hours,
            'watering_preference': context.watering_preference,
        },
        'recommendations': recommendations_df,
        'schedule': schedule_df,
    }


def format_markdown_summary(result: dict[str, Any]) -> str:
    ctx = result['context']
    recommendations = result['recommendations']
    lines = []
    lines.append('# Grow A Garden Phase 2 Demo Output')
    lines.append('')
    lines.append(f"- Planning date: {ctx['planning_date']}")
    lines.append(f"- USDA zone: {ctx['zone']}")
    lines.append(f"- Frost heuristic: last frost {ctx['last_frost']}, first frost {ctx['first_frost']}")
    lines.append(f"- Garden size: {ctx['garden_area_sqft']} sq ft")
    lines.append(f"- Sun hours: {ctx['sun_hours']}")
    lines.append(f"- Watering preference: {ctx['watering_preference']}")
    lines.append('')
    lines.append('## Top recommendations')
    lines.append('')
    for _, row in recommendations.iterrows():
        lines.append(
            f"- **{row['name']}** — score {row['score']}; {row['action_now']} Estimated irrigation: {row['water_inches_per_week']} in/week."
        )
    return '\n'.join(lines)
