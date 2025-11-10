"""Greedy scheduling algorithm for health activities.

This module implements the core scheduling algorithm that attempts to place
activities into time slots using a greedy approach:

1. Sort activities by priority (1=critical first) then by frequency (daily first)
2. For each activity, determine required occurrences based on frequency pattern
3. Generate candidate time slots across the scheduling horizon
4. For each occurrence, try slots in order of score (soft preferences)
5. Book the first valid slot (passes all hard constraints)

Algorithm guarantees:
- All hard constraints are satisfied (never violates specialist/equipment/travel/time windows)
- Greedy optimization of soft constraints (preference for better time slots)
- Deterministic output (no randomness or LLM involvement)
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Optional, Tuple
import logging

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot, FrequencyPattern
from .constraints import ConstraintChecker
from .scoring import SlotScorer
from .state import SchedulerState


logger = logging.getLogger(__name__)


class GreedyScheduler:
    """Greedy scheduler for health program activities."""

    def __init__(
        self,
        activities: List[Activity],
        specialists: List[Specialist],
        equipment: List[Equipment],
        travel_periods: List[TravelPeriod],
        start_date: date_type,
        duration_days: int = 90
    ):
        """Initialize scheduler with activities and constraints.

        Args:
            activities: List of activities to schedule
            specialists: List of specialists with availability
            equipment: List of equipment with maintenance windows
            travel_periods: List of client travel periods
            start_date: First day of scheduling horizon
            duration_days: Length of scheduling period (default 90 days)
        """
        self.activities = activities
        self.start_date = start_date
        self.end_date = start_date + timedelta(days=duration_days - 1)
        self.duration_days = duration_days

        # Initialize components
        self.checker = ConstraintChecker(specialists, equipment, travel_periods)
        self.scorer = SlotScorer()
        self.state = SchedulerState()

    def schedule(self) -> SchedulerState:
        """Execute greedy scheduling algorithm with backfill.

        Returns:
            SchedulerState with all successful bookings and failures
        """
        logger.info(f"Starting greedy scheduler for {len(self.activities)} activities")
        logger.info(f"Scheduling horizon: {self.start_date} to {self.end_date}")

        # Sort activities: priority ASC (1=critical first), then frequency DESC (daily first)
        sorted_activities = self._sort_activities(self.activities)

        # Phase 1: Normal greedy scheduling
        logger.info("Phase 1: Main scheduling pass...")
        for activity in sorted_activities:
            self._schedule_activity(activity)

        stats_phase1 = self.state.get_statistics()
        logger.info(f"Phase 1 complete: {stats_phase1['total_slots']} slots booked")

        # Phase 2: Backfill failed activities on light/empty days
        logger.info("Phase 2: Backfilling failed activities on light days...")
        backfilled = self._backfill_failed_activities(sorted_activities)
        logger.info(f"Phase 2 complete: {backfilled} additional slots scheduled")

        # Log summary
        stats = self.state.get_statistics()
        logger.info(f"Scheduling complete: {stats['total_slots']} slots booked, {stats['failed_count']} activities failed")

        return self.state

    def _sort_activities(self, activities: List[Activity]) -> List[Activity]:
        """Sort activities by priority (ASC) then frequency importance (DESC).

        Frequency importance: Daily > Weekly > Monthly > Custom
        """
        def frequency_importance(activity: Activity) -> int:
            if activity.frequency.pattern == FrequencyPattern.DAILY:
                return 3
            elif activity.frequency.pattern == FrequencyPattern.WEEKLY:
                return 2
            elif activity.frequency.pattern == FrequencyPattern.MONTHLY:
                return 1
            else:  # Custom
                return 0

        return sorted(
            activities,
            key=lambda a: (a.priority, -frequency_importance(a))
        )

    def _schedule_activity(self, activity: Activity) -> None:
        """Schedule all required occurrences of an activity.

        Args:
            activity: The activity to schedule
        """
        required_count = self._calculate_required_occurrences(activity)
        logger.debug(f"Scheduling {activity.name} ({activity.id}): {required_count} occurrences required")

        successful_count = 0

        for occurrence_index in range(required_count):
            slot = self._find_best_slot(activity, occurrence_index)

            if slot:
                self.state.add_booking(slot)
                self.scorer.record_booking(activity, slot.date)
                successful_count += 1
                logger.debug(f"  ✓ Occurrence {occurrence_index + 1}/{required_count} scheduled: {slot.date} at {slot.start_time}")
            else:
                logger.debug(f"  ✗ Occurrence {occurrence_index + 1}/{required_count} failed to schedule")

        if successful_count < required_count:
            logger.warning(
                f"Activity {activity.id} only scheduled {successful_count}/{required_count} occurrences "
                f"(priority {activity.priority})"
            )

    def _calculate_required_occurrences(self, activity: Activity) -> int:
        """Calculate how many times an activity should be scheduled.

        Args:
            activity: The activity to calculate for

        Returns:
            Number of required occurrences over the scheduling horizon
        """
        freq = activity.frequency

        if freq.pattern == FrequencyPattern.DAILY:
            return self.duration_days

        elif freq.pattern == FrequencyPattern.WEEKLY:
            weeks = self.duration_days // 7
            return weeks * freq.count

        elif freq.pattern == FrequencyPattern.MONTHLY:
            months = self.duration_days // 30  # Approximate
            return months * freq.count

        elif freq.pattern == FrequencyPattern.CUSTOM:
            if freq.interval_days:
                return self.duration_days // freq.interval_days
            else:
                return freq.count  # Fallback

        return 0

    def _find_best_slot(
        self,
        activity: Activity,
        occurrence_index: int
    ) -> Optional[TimeSlot]:
        """Find the best available time slot for an activity occurrence.

        Args:
            activity: The activity to schedule
            occurrence_index: Which occurrence (0-indexed)

        Returns:
            TimeSlot if successful, None if no valid slot found
        """
        candidate_slots = self._generate_candidate_slots(activity, occurrence_index)

        # Score all candidates
        scored_slots = []
        for date, start_time in candidate_slots:
            # Check hard constraints
            violation = self.checker.check_time_slot(
                activity, date, start_time, self.state.booked_slots
            )

            if violation is None:  # Valid slot
                score = self.scorer.score_slot(
                    activity, date, start_time, self.state.booked_slots
                )
                scored_slots.append((score, date, start_time))
            else:
                # Record violation for failure tracking
                self.state.record_failure(activity, violation)

        if not scored_slots:
            logger.debug(f"    No valid slots found for {activity.id} occurrence {occurrence_index}")
            return None

        # Sort by score (descending) and take best
        scored_slots.sort(reverse=True, key=lambda x: x[0])
        best_score, best_date, best_time = scored_slots[0]

        logger.debug(f"    Selected slot with score {best_score:.1f}: {best_date} at {best_time}")

        # Create TimeSlot
        return TimeSlot(
            activity_id=activity.id,
            date=best_date,
            start_time=best_time,
            duration_minutes=activity.duration_minutes,
            specialist_id=activity.specialist_id,
            equipment_ids=activity.equipment_ids or []
        )

    def _generate_candidate_slots(
        self,
        activity: Activity,
        occurrence_index: int
    ) -> List[Tuple[date_type, time_type]]:
        """Generate candidate (date, time) pairs for an activity occurrence.

        IMPROVED STRATEGY with flexible date selection:
        - Generate primary candidates based on occurrence pattern
        - Add backup candidates across multiple weeks/months
        - Sort candidates to prefer lighter days for lower priorities

        Args:
            activity: The activity to generate slots for
            occurrence_index: Which occurrence (0-indexed)

        Returns:
            List of (date, start_time) tuples to try
        """
        freq = activity.frequency
        candidates = []
        candidate_dates = []

        # Generate candidate dates based on frequency pattern
        if freq.pattern == FrequencyPattern.DAILY:
            # For Daily: use the specific day
            candidate_date = self.start_date + timedelta(days=occurrence_index)
            if candidate_date <= self.end_date:
                candidate_dates.append(candidate_date)

        elif freq.pattern == FrequencyPattern.WEEKLY:
            # PRIMARY: Use normal logic for preferred week
            week_number = occurrence_index // freq.count
            within_week_index = occurrence_index % freq.count

            if freq.preferred_days:
                target_weekday = freq.preferred_days[within_week_index % len(freq.preferred_days)]
            else:
                target_weekday = within_week_index % 5

            week_start = self.start_date + timedelta(weeks=week_number)
            days_to_add = (target_weekday - week_start.weekday()) % 7
            primary_date = week_start + timedelta(days=days_to_add)

            if primary_date <= self.end_date:
                candidate_dates.append(primary_date)

            # BACKUP: Add same weekday from OTHER weeks (flexible scheduling)
            total_weeks = self.duration_days // 7
            for alt_week in range(total_weeks):
                if alt_week == week_number:
                    continue  # Skip primary week
                alt_week_start = self.start_date + timedelta(weeks=alt_week)
                alt_date = alt_week_start + timedelta(days=days_to_add)
                if self.start_date <= alt_date <= self.end_date:
                    candidate_dates.append(alt_date)

        elif freq.pattern == FrequencyPattern.MONTHLY:
            # PRIMARY: Use normal logic
            month_number = occurrence_index // freq.count
            primary_date = self.start_date + timedelta(days=30 * month_number)
            if primary_date <= self.end_date:
                candidate_dates.append(primary_date)

            # BACKUP: Try other months
            total_months = self.duration_days // 30
            for alt_month in range(total_months):
                if alt_month == month_number:
                    continue
                alt_date = self.start_date + timedelta(days=30 * alt_month)
                if self.start_date <= alt_date <= self.end_date:
                    candidate_dates.append(alt_date)

        elif freq.pattern == FrequencyPattern.CUSTOM:
            if freq.interval_days:
                primary_date = self.start_date + timedelta(days=occurrence_index * freq.interval_days)
                if primary_date <= self.end_date:
                    candidate_dates.append(primary_date)

        # Sort candidate dates: For P3-P5, prefer lighter days
        if activity.priority >= 3:
            candidate_dates = self._sort_dates_by_lightness(candidate_dates)

        # Generate time slots for all candidate dates
        for candidate_date in candidate_dates:
            candidates.extend(self._generate_times_for_date(activity, candidate_date))

        return candidates

    def _generate_times_for_date(
        self,
        activity: Activity,
        date: date_type
    ) -> List[Tuple[date_type, time_type]]:
        """Generate candidate times for a specific date.

        Args:
            activity: The activity to generate times for
            date: The date to generate times on

        Returns:
            List of (date, time) pairs
        """
        times = []

        # If activity has time window, generate times within it
        if activity.time_window_start and activity.time_window_end:
            start_hour = activity.time_window_start.hour
            end_hour = activity.time_window_end.hour

            # Generate hourly slots within window
            for hour in range(start_hour, end_hour + 1):
                for minute in [0, 30]:  # Try on the hour and half-hour
                    candidate_time = time_type(hour, minute)

                    # Check if this time fits within window
                    if activity.time_window_start <= candidate_time:
                        # Check if activity finishes before window end
                        end_time = self._add_minutes_to_time(candidate_time, activity.duration_minutes)
                        if end_time <= activity.time_window_end:
                            times.append((date, candidate_time))

        else:
            # No time window - generate times across reasonable hours (6 AM - 8 PM)
            for hour in range(6, 21):  # 6 AM to 8 PM
                for minute in [0, 30]:
                    times.append((date, time_type(hour, minute)))

        return times

    def _add_minutes_to_time(self, t: time_type, minutes: int) -> time_type:
        """Add minutes to a time object."""
        dt = datetime.combine(date_type.today(), t)
        dt += timedelta(minutes=minutes)
        return dt.time()

    def _sort_dates_by_lightness(self, dates: List[date_type]) -> List[date_type]:
        """Sort dates by how many activities are already scheduled (ascending).

        Lighter days (fewer activities) come first.

        Args:
            dates: List of dates to sort

        Returns:
            Sorted list with lightest days first
        """
        from collections import Counter

        # Count activities per day
        activity_counts = Counter(slot.date for slot in self.state.booked_slots)

        # Sort dates by count (ascending - lightest first)
        return sorted(dates, key=lambda d: activity_counts.get(d, 0))

    def _backfill_failed_activities(self, sorted_activities: List[Activity]) -> int:
        """Attempt to schedule failed activities on the lightest days.

        This second pass targets activities that failed in the main pass
        and tries to place them on days with fewer scheduled activities.

        Args:
            sorted_activities: Activities in priority order

        Returns:
            Number of additional slots scheduled
        """
        backfilled_count = 0

        # Find days with few/no activities (sorted lightest first)
        light_days = self._find_light_days(max_activities=15)

        # For each activity, check if it has missing occurrences
        for activity in sorted_activities:
            required = self._calculate_required_occurrences(activity)
            scheduled = self.state.get_occurrence_count(activity.id)
            missing = required - scheduled

            if missing <= 0:
                continue  # Activity fully scheduled

            logger.debug(f"Backfilling {activity.id}: {missing} occurrences missing")

            # Try to schedule missing occurrences on light days
            for _ in range(missing):
                # Generate candidates from light days only
                candidates = []
                for light_day in light_days:
                    candidates.extend(self._generate_times_for_date(activity, light_day))

                # Try to book best valid slot
                scored_slots = []
                for date, start_time in candidates:
                    violation = self.checker.check_time_slot(
                        activity, date, start_time, self.state.booked_slots
                    )

                    if violation is None:
                        score = self.scorer.score_slot(
                            activity, date, start_time, self.state.booked_slots
                        )
                        scored_slots.append((score, date, start_time))

                if scored_slots:
                    # Book best slot
                    scored_slots.sort(reverse=True, key=lambda x: x[0])
                    _, best_date, best_time = scored_slots[0]

                    slot = TimeSlot(
                        activity_id=activity.id,
                        date=best_date,
                        start_time=best_time,
                        duration_minutes=activity.duration_minutes,
                        specialist_id=activity.specialist_id,
                        equipment_ids=activity.equipment_ids or []
                    )

                    self.state.add_booking(slot)
                    self.scorer.record_booking(activity, slot.date)
                    backfilled_count += 1
                    logger.debug(f"  ✓ Backfilled on {best_date} at {best_time}")

                    # Update light_days list to reflect new booking
                    light_days = self._find_light_days(max_activities=15)
                else:
                    # No valid slot found on light days
                    break

        return backfilled_count

    def _find_light_days(self, max_activities: int = 15) -> List[date_type]:
        """Find days with fewer than max_activities scheduled.

        Args:
            max_activities: Maximum number of activities to consider "light"

        Returns:
            List of dates sorted by activity count (lightest first)
        """
        from collections import Counter

        # Count activities per day
        activity_counts = Counter(slot.date for slot in self.state.booked_slots)

        # Generate all days in horizon
        all_days = []
        current_date = self.start_date
        while current_date <= self.end_date:
            all_days.append(current_date)
            current_date += timedelta(days=1)

        # Filter to light days and sort by lightness
        light_days = [
            day for day in all_days
            if activity_counts.get(day, 0) < max_activities
        ]

        # Sort by activity count (ascending - lightest first)
        return sorted(light_days, key=lambda d: activity_counts.get(d, 0))
