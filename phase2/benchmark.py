from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from growagarden.data_loader import build_plant_profiles, load_plant_profiles
from growagarden.scheduler import plan_garden, zone_to_numeric


BENCHMARK_PATH = PROJECT_ROOT / 'data' / 'manual' / 'scenario_benchmark.csv'
OUTPUT_DIR = PROJECT_ROOT / 'artifacts'


def main() -> None:
    build_plant_profiles(save=True)
    profiles = load_plant_profiles()
    benchmark_df = pd.read_csv(BENCHMARK_PATH)

    rows = []
    for _, row in benchmark_df.iterrows():
        crop_plan = plan_garden(
            planning_date=row['planning_date'],
            zone=row['zone'],
            garden_area_sqft=row['garden_area_sqft'],
            sun_hours=row['sun_hours'],
            watering_preference=row['watering_preference'],
            selected_crops=[row['crop_name']],
            profiles_df=profiles,
        )['recommendations'].iloc[0]

        profile = profiles.loc[profiles['name'] == row['crop_name']].iloc[0]
        baseline_pred = int(
            float(profile['zone_min']) <= zone_to_numeric(row['zone']) <= float(profile['zone_max'])
            and float(row['sun_hours']) >= float(profile['min_sun_hours'])
        )
        improved_pred = int(crop_plan['action_class'] in {'plant_outdoors_now', 'start_indoors_now'})

        rows.append(
            {
                **row.to_dict(),
                'baseline_pred': baseline_pred,
                'improved_pred': improved_pred,
                'improved_action': crop_plan['action_now'],
                'score': crop_plan['score'],
            }
        )

    result_df = pd.DataFrame(rows)
    baseline_accuracy = (result_df['baseline_pred'] == result_df['expected_can_plant_now']).mean()
    improved_accuracy = (result_df['improved_pred'] == result_df['expected_can_plant_now']).mean()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_DIR / 'benchmark_results.csv', index=False)

    summary_lines = [
        '# Scenario Benchmark Summary',
        '',
        f'- Cases: {len(result_df)}',
        f'- Baseline accuracy (ignores planting windows): {baseline_accuracy:.2%}',
        f'- Improved scheduler accuracy: {improved_accuracy:.2%}',
        '',
        '## Notes',
        '',
        '- Baseline = zone/sun filter only.',
        '- Improved scheduler = zone + planting windows + stage-aware actions.',
    ]
    (OUTPUT_DIR / 'benchmark_summary.md').write_text('\n'.join(summary_lines), encoding='utf-8')
    print('\n'.join(summary_lines))


if __name__ == '__main__':
    main()
