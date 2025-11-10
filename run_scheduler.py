#!/usr/bin/env python3
"""Main script to run the complete health activity scheduler."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_activities, load_specialists, load_equipment, load_travel, load_json, save_json
from scheduler import GreedyScheduler
from output import CalendarFormatter, MetricsCalculator

# Optional LLM summary generation
try:
    from output.summary_generator import generate_schedule_summary, generate_failure_analysis
    SUMMARY_AVAILABLE = True
except ImportError:
    SUMMARY_AVAILABLE = False


def main():
    """Run complete scheduling workflow with all outputs."""
    print("\n" + "=" * 80)
    print("HEALTH ACTIVITY SCHEDULER - COMPLETE WORKFLOW")
    print("=" * 80)

    # 1. Load data
    print("\n📂 STEP 1: Loading Data")
    print("-" * 80)

    data_dir = Path("data/generated")
    metadata = load_json(data_dir / "metadata.json")
    start_date_str = metadata.get("start_date")
    start_date = datetime.fromisoformat(start_date_str).date()

    activities = load_activities(data_dir / "activities.json")
    specialists = load_specialists(data_dir / "specialists.json")
    equipment = load_equipment(data_dir / "equipment.json")
    travel = load_travel(data_dir / "travel.json")

    print(f"✓ Loaded {len(activities)} activities")
    print(f"✓ Loaded {len(specialists)} specialists")
    print(f"✓ Loaded {len(equipment)} equipment items")
    print(f"✓ Loaded {len(travel)} travel periods")
    print(f"✓ Scheduling period: {start_date} to {metadata['end_date']}")

    # 2. Run scheduler
    print(f"\n⚙️  STEP 2: Running Greedy Scheduler")
    print("-" * 80)

    scheduler = GreedyScheduler(
        activities=activities,
        specialists=specialists,
        equipment=equipment,
        travel_periods=travel,
        start_date=start_date,
        duration_days=90
    )

    state = scheduler.schedule()

    # Calculate required occurrences for metrics
    required_occurrences = {
        activity.id: scheduler._calculate_required_occurrences(activity)
        for activity in activities
    }

    print(f"✓ Scheduling complete")
    print(f"  {len(state.booked_slots)} time slots scheduled")
    print(f"  {state.get_statistics()['unique_activities']} unique activities")

    # 3. Calculate metrics
    print(f"\n📊 STEP 3: Calculating Metrics")
    print("-" * 80)

    calculator = MetricsCalculator(activities, state)
    metrics_report = calculator.generate_full_report(required_occurrences, specialists, equipment)

    success_rate = metrics_report["success_metrics"]["overall"]["success_rate"]
    print(f"✓ Overall success rate: {success_rate:.1f}%")

    for priority in range(1, 6):
        priority_metrics = metrics_report["success_metrics"]["by_priority"].get(f"priority_{priority}", {})
        if priority_metrics.get("required", 0) > 0:
            rate = priority_metrics["success_rate"]
            status = "✓" if rate >= 90 else "⚠" if rate >= 70 else "✗"
            print(f"  {status} Priority {priority}: {rate:.1f}%")

    # 4. Generate calendar views
    print(f"\n📅 STEP 4: Generating Calendar Views")
    print("-" * 80)

    formatter = CalendarFormatter(activities, state.booked_slots)

    # Weekly view (first week)
    weekly_view = formatter.format_weekly_view(start_date, weeks=2)

    # Daily view (first day)
    daily_view = formatter.format_daily_view(start_date)

    # Monthly overview
    monthly_view = formatter.format_monthly_overview(start_date.year, start_date.month)

    # Summary
    end_date = start_date + __import__('datetime').timedelta(days=89)
    summary = formatter.format_summary(start_date, end_date)

    print(f"✓ Generated weekly view (2 weeks)")
    print(f"✓ Generated daily view ({start_date.strftime('%B %d')})")
    print(f"✓ Generated monthly overview ({start_date.strftime('%B %Y')})")
    print(f"✓ Generated schedule summary")

    # 5. Save outputs
    print(f"\n💾 STEP 5: Saving Outputs")
    print("-" * 80)

    output_dir = Path("output/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON outputs
    save_json(state.booked_slots, output_dir / "schedule.json")
    save_json(metrics_report, output_dir / "metrics.json")
    save_json(state.get_failure_report(), output_dir / "failures.json")

    # Save text outputs
    with open(output_dir / "weekly_calendar.txt", "w") as f:
        f.write(weekly_view)

    with open(output_dir / "daily_schedule.txt", "w") as f:
        f.write(daily_view)

    with open(output_dir / "monthly_overview.txt", "w") as f:
        f.write(monthly_view)

    with open(output_dir / "summary.txt", "w") as f:
        f.write(summary)

    print(f"✓ schedule.json ({len(state.booked_slots)} slots)")
    print(f"✓ metrics.json")
    print(f"✓ failures.json ({len(state.get_failure_report())} failed activities)")
    print(f"✓ weekly_calendar.txt")
    print(f"✓ daily_schedule.txt")
    print(f"✓ monthly_overview.txt")
    print(f"✓ summary.txt")

    # 6. Generate LLM summaries (optional)
    if SUMMARY_AVAILABLE:
        print(f"\n🤖 STEP 6: Generating LLM Summaries (Optional)")
        print("-" * 80)

        try:
            # Calculate end date
            end_date = start_date + __import__('datetime').timedelta(days=89)

            # Generate overall summary
            llm_summary = generate_schedule_summary(state, activities, start_date, end_date)

            # Generate failure analysis if there are failures
            llm_failure_analysis = ""
            if state.failed_activities:
                llm_failure_analysis = generate_failure_analysis(state, activities)

            # Save LLM summaries
            with open(output_dir / "llm_summary.txt", "w") as f:
                f.write("OVERALL SCHEDULE SUMMARY\n")
                f.write("=" * 80 + "\n\n")
                f.write(llm_summary)
                f.write("\n\n")

                if llm_failure_analysis:
                    f.write("FAILURE ANALYSIS\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(llm_failure_analysis)

            print(f"✓ llm_summary.txt (AI-generated natural language summary)")

        except Exception as e:
            print(f"⚠ LLM summary generation failed: {str(e)}")
            print(f"  Set GOOGLE_API_KEY environment variable to enable LLM summaries")

    # 7. Display sample outputs
    print(f"\n📋 STEP 7: Sample Outputs")
    print("-" * 80)

    print(f"\n{summary}\n")

    print(f"\nFirst Day Schedule Preview:")
    print("-" * 40)
    day_slots = [s for s in state.booked_slots if s.date == start_date][:5]
    for slot in day_slots:
        activity = next((a for a in activities if a.id == slot.activity_id), None)
        if activity:
            print(f"  {slot.start_time.strftime('%H:%M')} - {activity.name} ({slot.duration_minutes}min)")
    if len([s for s in state.booked_slots if s.date == start_date]) > 5:
        print(f"  ... and {len([s for s in state.booked_slots if s.date == start_date]) - 5} more")

    # Final summary
    print(f"\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 80)

    print(f"\nResults Summary:")
    print(f"  Success Rate: {success_rate:.1f}%")
    print(f"  Scheduled: {len(state.booked_slots)} / {sum(required_occurrences.values())} required occurrences")
    print(f"  Failed Activities: {len(state.get_failure_report())}")

    print(f"\nOutputs saved to: {output_dir}/")
    print(f"  - schedule.json (machine-readable schedule)")
    print(f"  - metrics.json (detailed metrics)")
    print(f"  - failures.json (failure analysis)")
    print(f"  - *.txt (human-readable calendars)")

    if success_rate < 85:
        print(f"\n⚠️  Note: Success rate below 85% target")
        most_common = metrics_report["failure_analysis"].get("most_common_issue")
        if most_common:
            print(f"  Most common issue: {most_common}")
        print(f"  Check failures.json for detailed analysis")
    else:
        print(f"\n🎉 Success! Achieved target success rate")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
