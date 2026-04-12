from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from growagarden.data_loader import PROCESSED_PROFILE_PATH, build_plant_profiles


if __name__ == '__main__':
    df = build_plant_profiles(save=True)
    print(f'Built {len(df)} processed plant profiles at {PROCESSED_PROFILE_PATH}')
