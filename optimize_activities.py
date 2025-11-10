#!/usr/bin/env python3
"""Post-process generated activities to improve schedulability."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_activities, save_json


def main():
    """Optimize activities for better scheduling success rate."""
    print("=" * 80)
    print("ACTIVITY OPTIMIZATION FOR SCHEDULABILITY")
    print("=" * 80)

    # Load activities
    activities = load_activities("data/generated/activities.json")
    print(f"\n📂 Loaded {len(activities)} activities")

    # Analysis before
    weekly_acts = [a for a in activities if a.frequency.pattern.value == "Weekly"]
    monthly_acts = [a for a in activities if a.frequency.pattern.value == "Monthly"]

    print(f"\nBefore Optimization:")
    print(f"  Weekly: {len(weekly_acts)}")
    print(f"    5+ x/week: {len([a for a in weekly_acts if a.frequency.count >= 5])}")
    print(f"    3-4 x/week: {len([a for a in weekly_acts if a.frequency.count in [3,4]])}")
    print(f"    1-2 x/week: {len([a for a in weekly_acts if a.frequency.count in [1,2]])}")
    print(f"  Monthly: {len(monthly_acts)}")
    print(f"  Activities with time windows: {len([a for a in activities if a.time_window_start])}")

    # Optimization 1: Reduce high-frequency weekly activities
    print(f"\n🔧 Optimization 1: Reducing high-frequency weekly activities...")
    count_reduced = 0

    for activity in weekly_acts:
        if activity.frequency.count >= 5:
            # 5-7x/week → 3x/week for P1, 2x/week for P2+
            if activity.priority == 1:
                activity.frequency.count = 3
            else:
                activity.frequency.count = 2
            count_reduced += 1
        elif activity.frequency.count == 4:
            # 4x/week → 2x/week
            activity.frequency.count = 2
            count_reduced += 1
        elif activity.frequency.count == 3 and activity.priority >= 3:
            # 3x/week → 2x/week for P3+
            activity.frequency.count = 2
            count_reduced += 1
        elif activity.frequency.count == 2 and activity.priority >= 4:
            # 2x/week → 1x/week for P4+
            activity.frequency.count = 1
            count_reduced += 1

    print(f"  ✓ Reduced frequency for {count_reduced} activities")

    # Optimization 2: Remove time windows from P3-P5
    print(f"\n🔧 Optimization 2: Removing time windows from P3-P5...")
    windows_removed = 0

    for activity in activities:
        if activity.priority >= 3 and activity.time_window_start:
            activity.time_window_start = None
            activity.time_window_end = None
            windows_removed += 1

    print(f"  ✓ Removed time windows from {windows_removed} P3-P5 activities")

    # Optimization 3: Remove specialists from P4-P5
    print(f"\n🔧 Optimization 3: Removing specialists from P4-P5...")
    specialists_removed = 0

    for activity in activities:
        if activity.priority >= 4 and activity.specialist_id:
            activity.specialist_id = None
            specialists_removed += 1

    print(f"  ✓ Removed specialist requirements from {specialists_removed} P4-P5 activities")

    # Optimization 4: Remove equipment from 50% of P4-P5 activities
    print(f"\n🔧 Optimization 4: Removing equipment from P4-P5...")
    equipment_removed = 0

    for activity in activities:
        if activity.priority >= 4 and activity.equipment_ids and activity.id[-1] in ['0', '2', '4', '6', '8']:
            activity.equipment_ids = []
            equipment_removed += 1

    print(f"  ✓ Removed equipment from {equipment_removed} P4-P5 activities")

    # Save optimized activities
    print(f"\n💾 Saving optimized activities...")
    save_json(activities, "data/generated/activities.json")

    # Analysis after
    weekly_acts = [a for a in activities if a.frequency.pattern.value == "Weekly"]

    print(f"\nAfter Optimization:")
    print(f"  Weekly:")
    print(f"    5+ x/week: {len([a for a in weekly_acts if a.frequency.count >= 5])}")
    print(f"    3-4 x/week: {len([a for a in weekly_acts if a.frequency.count in [3,4]])}")
    print(f"    1-2 x/week: {len([a for a in weekly_acts if a.frequency.count in [1,2]])}")
    print(f"  Activities with time windows: {len([a for a in activities if a.time_window_start])}")

    # Calculate new total slots required
    total_slots = 0
    for a in activities:
        if a.frequency.pattern.value == "Weekly":
            total_slots += (90 // 7) * a.frequency.count
        elif a.frequency.pattern.value == "Monthly":
            total_slots += (90 // 30) * a.frequency.count

    print(f"  Total required slots: {total_slots}")
    print(f"  Target for 70% success: {int(total_slots * 0.7)} slots")
    print(f"  Average per day: {total_slots / 90:.1f} required, {total_slots * 0.7 / 90:.1f} target")

    print(f"\n✅ Optimization complete! Run scheduler to see improvement.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
