#!/usr/bin/env python3
"""Generate health activity schedule and save results."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_activities, load_specialists, load_equipment, load_travel, load_json, save_json
from scheduler import GreedyScheduler


def main():
    """Generate schedule and save results."""
    print("=" * 80)
    print("HEALTH ACTIVITY SCHEDULER")
    print("=" * 80)

    # Load data
    print("\n📂 Loading data...")
    data_dir = Path("data/generated")

    metadata = load_json(data_dir / "metadata.json")
    start_date_str = metadata.get("start_date")
    start_date = datetime.fromisoformat(start_date_str).date()

    activities = load_activities(data_dir / "activities.json")
    specialists = load_specialists(data_dir / "specialists.json")
    equipment = load_equipment(data_dir / "equipment.json")
    travel = load_travel(data_dir / "travel.json")

    print(f"   ✓ {len(activities)} activities")
    print(f"   ✓ {len(specialists)} specialists")
    print(f"   ✓ {len(equipment)} equipment items")
    print(f"   ✓ {len(travel)} travel periods")

    # Run scheduler
    print(f"\n⚙️  Running greedy scheduler...")
    print(f"   Scheduling period: {start_date} to {metadata['end_date']}")

    scheduler = GreedyScheduler(
        activities=activities,
        specialists=specialists,
        equipment=equipment,
        travel_periods=travel,
        start_date=start_date,
        duration_days=90
    )

    state = scheduler.schedule()

    # Get statistics
    stats = state.get_statistics()

    # Calculate success metrics
    total_required = sum(
        scheduler._calculate_required_occurrences(activity)
        for activity in activities
    )
    success_rate = (stats['total_slots'] / total_required * 100) if total_required > 0 else 0

    # Priority breakdown
    priority_stats = {i: {"scheduled": 0, "required": 0} for i in range(1, 6)}
    for activity in activities:
        priority = activity.priority
        required = scheduler._calculate_required_occurrences(activity)
        scheduled = state.get_occurrence_count(activity.id)
        priority_stats[priority]["required"] += required
        priority_stats[priority]["scheduled"] += scheduled

    # Display results
    print(f"\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n📊 Overall:")
    print(f"   Success Rate: {success_rate:.1f}% ({stats['total_slots']}/{total_required} occurrences)")
    print(f"   Unique Activities Scheduled: {stats['unique_activities']}/{len(activities)}")
    print(f"   Date Range: {stats['date_range'][0]} to {stats['date_range'][1]}")

    print(f"\n📋 By Priority:")
    for priority in range(1, 6):
        req = priority_stats[priority]["required"]
        sch = priority_stats[priority]["scheduled"]
        rate = (sch / req * 100) if req > 0 else 0
        status = "✓" if rate >= 90 else "⚠" if rate >= 70 else "✗"
        print(f"   {status} Priority {priority}: {rate:5.1f}% ({sch}/{req})")

    # Save schedule
    output_dir = Path("data/schedules")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving schedule to {output_dir}/...")

    # Save time slots
    save_json(state.booked_slots, output_dir / "schedule.json")
    print(f"   ✓ schedule.json ({len(state.booked_slots)} time slots)")

    # Save statistics
    schedule_metadata = {
        "generation_date": str(datetime.now().date()),
        "start_date": str(start_date),
        "end_date": metadata["end_date"],
        "total_slots": stats["total_slots"],
        "total_required": total_required,
        "success_rate": round(success_rate, 2),
        "unique_activities_scheduled": stats["unique_activities"],
        "total_activities": len(activities),
        "priority_breakdown": {
            f"priority_{p}": {
                "scheduled": priority_stats[p]["scheduled"],
                "required": priority_stats[p]["required"],
                "success_rate": round((priority_stats[p]["scheduled"] / priority_stats[p]["required"] * 100) if priority_stats[p]["required"] > 0 else 0, 2)
            }
            for p in range(1, 6)
        },
        "busiest_day": {
            "date": str(stats["busiest_day"][0]),
            "activity_count": stats["busiest_day"][1]
        } if stats["busiest_day"] else None
    }

    save_json(schedule_metadata, output_dir / "schedule_metadata.json")
    print(f"   ✓ schedule_metadata.json")

    # Save failure report
    failure_report = state.get_failure_report()
    save_json(failure_report, output_dir / "failures.json")
    print(f"   ✓ failures.json ({len(failure_report)} failed activities)")

    print(f"\n✅ Schedule generation complete!")
    print(f"   {success_rate:.1f}% success rate")

    if success_rate < 85:
        print(f"\n⚠️  Note: Success rate below 85% target")
        print(f"   Main causes: {len(failure_report)} activities couldn't be fully scheduled")
        print(f"   Check failures.json for details")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
