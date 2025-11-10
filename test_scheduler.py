#!/usr/bin/env python3
"""Test the scheduler with generated data."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import load_activities, load_specialists, load_equipment, load_travel, load_json
from scheduler import GreedyScheduler


def main():
    """Test scheduler with generated data."""
    print("=" * 80)
    print("HEALTH ACTIVITY SCHEDULER - TEST RUN")
    print("=" * 80)

    # Load data
    print("\n📂 Loading generated data...")
    data_dir = Path("data/generated")

    metadata = load_json(data_dir / "metadata.json")
    start_date = metadata.get("start_date")

    activities = load_activities(data_dir / "activities.json")
    specialists = load_specialists(data_dir / "specialists.json")
    equipment = load_equipment(data_dir / "equipment.json")
    travel = load_travel(data_dir / "travel.json")

    print(f"   ✓ Loaded {len(activities)} activities")
    print(f"   ✓ Loaded {len(specialists)} specialists")
    print(f"   ✓ Loaded {len(equipment)} equipment items")
    print(f"   ✓ Loaded {len(travel)} travel periods")
    print(f"   ✓ Scheduling period: {metadata['start_date']} to {metadata['end_date']}")

    # Initialize scheduler
    print("\n🚀 Initializing greedy scheduler...")
    from datetime import datetime
    start_date_obj = datetime.fromisoformat(start_date).date()

    scheduler = GreedyScheduler(
        activities=activities,
        specialists=specialists,
        equipment=equipment,
        travel_periods=travel,
        start_date=start_date_obj,
        duration_days=90
    )

    # Run scheduler
    print("\n⚙️  Running scheduler (this may take 10-30 seconds)...\n")
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    state = scheduler.schedule()

    # Display results
    print("\n" + "=" * 80)
    print("SCHEDULING RESULTS")
    print("=" * 80)

    stats = state.get_statistics()

    print(f"\n📊 Overall Statistics:")
    print(f"   Total time slots booked: {stats['total_slots']}")
    print(f"   Unique activities scheduled: {stats['unique_activities']}")
    print(f"   Failed activities: {stats['failed_count']}")

    if stats['date_range']:
        print(f"   Date range: {stats['date_range'][0]} to {stats['date_range'][1]}")

    if stats['busiest_day']:
        busiest_date, count = stats['busiest_day']
        print(f"   Busiest day: {busiest_date} ({count} activities)")

    # Calculate success rate
    total_required = sum(
        scheduler._calculate_required_occurrences(activity)
        for activity in activities
    )
    success_rate = (stats['total_slots'] / total_required * 100) if total_required > 0 else 0

    print(f"\n✅ Success Rate: {success_rate:.1f}% ({stats['total_slots']}/{total_required} required occurrences)")

    # Priority breakdown
    print(f"\n📋 Priority Breakdown:")
    priority_stats = {i: {"scheduled": 0, "required": 0} for i in range(1, 6)}

    for activity in activities:
        priority = activity.priority
        required = scheduler._calculate_required_occurrences(activity)
        scheduled = state.get_occurrence_count(activity.id)

        priority_stats[priority]["required"] += required
        priority_stats[priority]["scheduled"] += scheduled

    for priority in range(1, 6):
        req = priority_stats[priority]["required"]
        sch = priority_stats[priority]["scheduled"]
        rate = (sch / req * 100) if req > 0 else 0
        print(f"   Priority {priority}: {sch}/{req} ({rate:.1f}%)")

    # Specialist usage
    if stats['specialist_usage']:
        print(f"\n👥 Specialist Usage:")
        for spec_id, count in sorted(stats['specialist_usage'].items(), key=lambda x: -x[1])[:5]:
            specialist = next((s for s in specialists if s.id == spec_id), None)
            name = specialist.name if specialist else spec_id
            print(f"   {name}: {count} sessions")

    # Equipment usage
    if stats['equipment_usage']:
        print(f"\n🏋️  Equipment Usage:")
        for equip_id, count in sorted(stats['equipment_usage'].items(), key=lambda x: -x[1])[:5]:
            equip_item = next((e for e in equipment if e.id == equip_id), None)
            name = equip_item.name if equip_item else equip_id
            print(f"   {name}: {count} uses")

    # Failure report
    if stats['failed_count'] > 0:
        print(f"\n❌ Failed Activities ({stats['failed_count']}):")
        failure_report = state.get_failure_report()

        for record in failure_report[:10]:  # Show top 10
            print(f"\n   {record['activity_name']} (Priority {record['priority']})")
            print(f"      Type: {record['activity_type']}")
            print(f"      Attempts: {record['attempts']}")
            print(f"      Main issues: {record['violation_types']}")
            if record['sample_reason']:
                print(f"      Example: {record['sample_reason']}")

        if len(failure_report) > 10:
            print(f"\n   ... and {len(failure_report) - 10} more failed activities")

    # Sample schedule (first 3 days)
    print(f"\n📅 Sample Schedule (First 3 Days):")
    for day_offset in range(3):
        day = start_date_obj + __import__('datetime').timedelta(days=day_offset)
        day_slots = state.get_slots_for_date(day)

        print(f"\n   {day.strftime('%A, %B %d, %Y')} ({len(day_slots)} activities):")

        if day_slots:
            # Sort by start time
            day_slots.sort(key=lambda s: s.start_time)

            for slot in day_slots[:5]:  # Show first 5
                activity = next((a for a in activities if a.id == slot.activity_id), None)
                if activity:
                    print(f"      {slot.start_time.strftime('%H:%M')} - {activity.name} ({slot.duration_minutes}min)")

            if len(day_slots) > 5:
                print(f"      ... and {len(day_slots) - 5} more activities")
        else:
            print("      (No activities scheduled)")

    print("\n" + "=" * 80)
    print(f"✅ Test complete! Achieved {success_rate:.1f}% scheduling success rate")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
