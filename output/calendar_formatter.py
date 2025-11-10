"""Calendar formatters for human-readable schedule output."""

from datetime import date as date_type, timedelta
from typing import List, Dict
from collections import defaultdict

from models import Activity, TimeSlot


class CalendarFormatter:
    """Format schedules as readable calendars."""

    def __init__(self, activities: List[Activity], slots: List[TimeSlot]):
        """Initialize formatter with activities and time slots.

        Args:
            activities: List of all activities
            slots: List of scheduled time slots
        """
        self.activities = {a.id: a for a in activities}
        self.slots = sorted(slots, key=lambda s: (s.date, s.start_time))

        # Group slots by date
        self.slots_by_date: Dict[date_type, List[TimeSlot]] = defaultdict(list)
        for slot in slots:
            self.slots_by_date[slot.date].append(slot)

    def format_weekly_view(self, start_date: date_type, weeks: int = 1) -> str:
        """Generate weekly calendar view.

        Args:
            start_date: First day of the week (should be Monday)
            weeks: Number of weeks to display

        Returns:
            Formatted weekly calendar string
        """
        output = []
        output.append("=" * 100)
        output.append(f"WEEKLY CALENDAR VIEW - {start_date.strftime('%B %Y')}")
        output.append("=" * 100)

        for week_num in range(weeks):
            week_start = start_date + timedelta(weeks=week_num)
            output.append(f"\nWeek {week_num + 1}: {week_start.strftime('%b %d')} - {(week_start + timedelta(days=6)).strftime('%b %d, %Y')}")
            output.append("-" * 100)

            # Header
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            header = " | ".join([f"{day:12s}" for day in days])
            output.append(header)
            output.append("-" * 100)

            # Get all time slots for this week
            week_slots = defaultdict(list)
            for day_offset in range(7):
                current_date = week_start + timedelta(days=day_offset)
                if current_date in self.slots_by_date:
                    week_slots[day_offset] = self.slots_by_date[current_date]

            # Display activities (max 5 rows per week)
            max_activities = max([len(slots) for slots in week_slots.values()] or [0])
            for row in range(min(max_activities, 5)):
                row_output = []
                for day_offset in range(7):
                    day_slots = week_slots.get(day_offset, [])
                    if row < len(day_slots):
                        slot = day_slots[row]
                        activity = self.activities.get(slot.activity_id)
                        if activity:
                            cell = f"{slot.start_time.strftime('%H:%M')} {activity.name[:8]}"
                            row_output.append(f"{cell:12s}")
                        else:
                            row_output.append(f"{'':12s}")
                    else:
                        row_output.append(f"{'':12s}")

                output.append(" | ".join(row_output))

            # Show count if more activities exist
            for day_offset in range(7):
                day_slots = week_slots.get(day_offset, [])
                if len(day_slots) > 5:
                    output.append(f"\n{days[day_offset]}: +{len(day_slots) - 5} more activities")

        return "\n".join(output)

    def format_daily_view(self, date: date_type) -> str:
        """Generate detailed daily schedule.

        Args:
            date: The date to display

        Returns:
            Formatted daily schedule string
        """
        output = []
        output.append("=" * 80)
        output.append(f"DAILY SCHEDULE - {date.strftime('%A, %B %d, %Y')}")
        output.append("=" * 80)

        day_slots = self.slots_by_date.get(date, [])

        if not day_slots:
            output.append("\nNo activities scheduled for this day.")
            return "\n".join(output)

        # Sort by start time
        day_slots = sorted(day_slots, key=lambda s: s.start_time)

        output.append(f"\nTotal activities: {len(day_slots)}\n")

        for slot in day_slots:
            activity = self.activities.get(slot.activity_id)
            if not activity:
                continue

            # Calculate end time
            from datetime import datetime, timedelta
            start_dt = datetime.combine(date, slot.start_time)
            end_dt = start_dt + timedelta(minutes=slot.duration_minutes)
            end_time = end_dt.time()

            output.append(f"{slot.start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}  |  {activity.name}")
            output.append(f"{'':19}   Type: {activity.type.value} | Priority: {activity.priority} | {slot.duration_minutes} min")

            if activity.location:
                output.append(f"{'':19}   Location: {activity.location}")

            if slot.specialist_id:
                output.append(f"{'':19}   Specialist: {slot.specialist_id}")

            if slot.equipment_ids:
                output.append(f"{'':19}   Equipment: {', '.join(slot.equipment_ids)}")

            output.append("")

        return "\n".join(output)

    def format_monthly_overview(self, year: int, month: int) -> str:
        """Generate monthly overview with activity counts.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Formatted monthly overview string
        """
        import calendar

        output = []
        output.append("=" * 80)
        output.append(f"MONTHLY OVERVIEW - {calendar.month_name[month]} {year}")
        output.append("=" * 80)

        # Get calendar for the month
        cal = calendar.monthcalendar(year, month)

        # Count activities per day
        activity_counts = {}
        for day in range(1, 32):
            try:
                date = date_type(year, month, day)
                activity_counts[day] = len(self.slots_by_date.get(date, []))
            except ValueError:
                break

        # Display calendar
        output.append("\nMon  Tue  Wed  Thu  Fri  Sat  Sun")
        output.append("-" * 35)

        for week in cal:
            week_output = []
            for day in week:
                if day == 0:
                    week_output.append("    ")
                else:
                    count = activity_counts.get(day, 0)
                    if count == 0:
                        week_output.append(f"{day:2d}  ")
                    else:
                        week_output.append(f"{day:2d}({count})")

            output.append(" ".join(week_output))

        # Summary statistics
        output.append("\n" + "-" * 35)
        total_activities = sum(activity_counts.values())
        days_with_activities = sum(1 for count in activity_counts.values() if count > 0)
        busiest_day = max(activity_counts.items(), key=lambda x: x[1]) if activity_counts else (0, 0)

        output.append(f"\nTotal activities: {total_activities}")
        output.append(f"Days with activities: {days_with_activities}/{len(activity_counts)}")
        if busiest_day[1] > 0:
            output.append(f"Busiest day: {busiest_day[0]} ({busiest_day[1]} activities)")

        return "\n".join(output)

    def format_summary(self, start_date: date_type, end_date: date_type) -> str:
        """Generate schedule summary statistics.

        Args:
            start_date: First day of schedule
            end_date: Last day of schedule

        Returns:
            Formatted summary string
        """
        output = []
        output.append("=" * 80)
        output.append("SCHEDULE SUMMARY")
        output.append("=" * 80)

        output.append(f"\nPeriod: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
        output.append(f"Duration: {(end_date - start_date).days + 1} days")

        # Activity type distribution
        type_counts = defaultdict(int)
        for slot in self.slots:
            activity = self.activities.get(slot.activity_id)
            if activity:
                type_counts[activity.type.value] += 1

        output.append(f"\nTotal scheduled slots: {len(self.slots)}")
        output.append("\nActivity Distribution:")
        for activity_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            percentage = (count / len(self.slots) * 100) if self.slots else 0
            output.append(f"  {activity_type:15s}: {count:4d} ({percentage:5.1f}%)")

        # Daily averages
        if self.slots_by_date:
            avg_per_day = len(self.slots) / len(self.slots_by_date)
            output.append(f"\nAverage activities per day: {avg_per_day:.1f}")

        return "\n".join(output)
