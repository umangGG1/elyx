#!/usr/bin/env python3
"""Fix duplicate activity IDs in generated data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_activities, save_json


def main():
    """Fix duplicate IDs by renumbering activities sequentially."""
    data_dir = Path("data/generated")

    print("Loading activities...")
    activities = load_activities(data_dir / "activities.json")

    print(f"Found {len(activities)} activities")

    # Renumber with unique IDs
    for i, activity in enumerate(activities, start=1):
        activity.id = f"act_{i:03d}"  # act_001, act_002, ..., act_114

    # Save back
    print(f"Saving {len(activities)} activities with unique IDs...")
    save_json(activities, data_dir / "activities.json")

    print("✓ Done! All activities now have unique IDs (act_001 to act_114)")


if __name__ == "__main__":
    main()
