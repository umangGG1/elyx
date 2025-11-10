#!/usr/bin/env python3
"""
Simple scheduling example with minimal dataset.

This script demonstrates basic scheduler usage with:
- 5 activities
- 2 specialists
- 1 equipment item
- 7-day period
"""

import sys
from pathlib import Path
from datetime import date

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.activity import Activity
from models.constraints import Specialist, Equipment, TravelPeriod
from scheduler.greedy import GreedyScheduler
from output.calendar_formatter import format_daily_calendar
from output.metrics import calculate_success_metrics
from utils.io import load_json, save_json


def load_sample_data():
    """Load sample data from the sample_data directory."""
    sample_dir = Path(__file__).parent / "sample_data"

    activities = [Activity(**a) for a in load_json(sample_dir / "activities.json")]
    specialists = [Specialist(**s) for s in load_json(sample_dir / "specialists.json")]
    equipment = [Equipment(**e) for e in load_json(sample_dir / "equipment.json")]
    travel_periods = [TravelPeriod(**t) for t in load_json(sample_dir / "travel.json")]

    return activities, specialists, equipment, travel_periods


def main():
    """Run simple scheduling example."""
    print("=" * 80)
    print("SIMPLE SCHEDULING EXAMPLE")
    print("=" * 80)
    print()

    # Define 7-day scheduling period
    start_date = date(2025, 12, 9)
    end_date = date(2025, 12, 15)

    print(f"Scheduling Period: {start_date} to {end_date} (7 days)")
    print()

    # Load sample data
    print("Loading sample data...")
    activities, specialists, equipment, travel_periods = load_sample_data()

    print(f"  - {len(activities)} activities")
    print(f"  - {len(specialists)} specialists")
    print(f"  - {len(equipment)} equipment items")
    print(f"  - {len(travel_periods)} travel periods")
    print()

    # Create scheduler
    print("Creating scheduler...")
    scheduler = GreedyScheduler(
        activities=activities,
        specialists=specialists,
        equipment=equipment,
        travel_periods=travel_periods,
        start_date=start_date,
        end_date=end_date
    )
    print()

    # Run scheduling
    print("Running scheduler...")
    schedule = scheduler.schedule()
    print()

    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    # Calculate metrics
    metrics = calculate_success_metrics(schedule, activities, start_date, end_date)

    print(f"Overall Success Rate: {metrics['overall_success_rate']:.1f}%")
    print(f"Scheduled Slots: {metrics['total_scheduled']}")
    print(f"Failed Occurrences: {metrics['total_failed']}")
    print()

    # Priority breakdown
    print("Priority Breakdown:")
    print("-" * 80)
    print(f"{'Priority':<12} {'Count':<8} {'Required':<10} {'Scheduled':<10} {'Success %':<10}")
    print("-" * 80)

    for priority in range(1, 6):
        p_key = f"P{priority}"
        if p_key in metrics['by_priority']:
            p_data = metrics['by_priority'][p_key]
            print(
                f"P{priority:<11} "
                f"{p_data['activity_count']:<8} "
                f"{p_data['required_slots']:<10} "
                f"{p_data['scheduled_slots']:<10} "
                f"{p_data['success_rate']:<10.1f}"
            )
    print()

    # Daily calendar
    print("=" * 80)
    print("DAILY SCHEDULE")
    print("=" * 80)
    print()
    print(format_daily_calendar(schedule, activities, start_date, end_date))
    print()

    # Failed activities
    if schedule.failed:
        print("=" * 80)
        print("FAILED ACTIVITIES")
        print("=" * 80)
        print()

        # Group failures by activity
        failures_by_activity = {}
        for failure in schedule.failed:
            if failure.activity_id not in failures_by_activity:
                failures_by_activity[failure.activity_id] = []
            failures_by_activity[failure.activity_id].append(failure)

        for activity_id, failures in failures_by_activity.items():
            # Find activity
            activity = next((a for a in activities if a.id == activity_id), None)
            if activity:
                print(f"{activity.name} (P{activity.priority}):")
                print(f"  Failed: {len(failures)} occurrences")
                print(f"  Reason: {failures[0].reason}")
                print()
    else:
        print("✓ All activities scheduled successfully!")
        print()

    print("=" * 80)
    print("Example complete!")
    print()
    print("Next steps:")
    print("  1. Modify sample_data/*.json to test different scenarios")
    print("  2. Run generate_data.py for a realistic 100+ activity dataset")
    print("  3. Run run_scheduler.py for the full 90-day scheduling workflow")
    print("  4. Launch web_app.py to visualize schedules in the browser")
    print("=" * 80)


if __name__ == "__main__":
    main()
