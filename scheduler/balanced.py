"""Priority-balanced scheduling algorithm for health activities.

This module implements a modified greedy algorithm that ensures balanced
scheduling across all priority levels by reserving capacity:

1. Calculate required occurrences for each priority level
2. Reserve daily capacity quotas (e.g., P1 can use max 40% of slots per day)
3. Schedule activities in rounds, cycling through priorities
4. Enforce capacity limits to prevent high-priority activities from monopolizing calendar
5. Allow spillover capacity in later rounds if quotas not met

This addresses the core limitation of pure greedy scheduling where
P1-P2 activities fill the calendar before P3-P4 get scheduled.
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Optional, Tuple, Dict
from collections import defaultdict
import logging

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot, FrequencyPattern
from .constraints import ConstraintChecker
from .scoring import SlotScorer
from .state import SchedulerState


logger = logging.getLogger(__name__)


class BalancedScheduler:
    """Priority-balanced scheduler for health program activities."""

    # Daily capacity quotas by priority (% of max daily slots)
    # These are soft limits for Round 1 - Round 2 allows unlimited
    PRIORITY_QUOTAS = {
        1: 0.55,  # P1 can use up to 55% of daily capacity
        2: 0.50,  # P2 can use up to 50%
        3: 0.35,  # P3 can use up to 35%
        4: 0.25,  # P4 can use up to 25%
        5: 0.15,  # P5 can use up to 15%
    }

    MAX_DAILY_SLOTS = 30  # Maximum activities per day (reasonable limit)

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

        # Track daily capacity usage by priority
        self.daily_capacity: Dict[date_type, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def schedule(self) -> SchedulerState:
        """Execute priority-balanced scheduling algorithm.

        Returns:
            SchedulerState with all successful bookings and failures
        """
        logger.info(f"Starting balanced scheduler for {len(self.activities)} activities")
        logger.info(f"Scheduling horizon: {self.start_date} to {self.end_date}")

        # Group activities by priority
        activities_by_priority = self._group_by_priority(self.activities)

        # Round 1: Schedule each priority with quota enforcement
        logger.info("Round 1: Scheduling with capacity quotas...")
        for priority in sorted(activities_by_priority.keys()):
            priority_activities = activities_by_priority[priority]
            logger.info(f"  Priority {priority}: {len(priority_activities)} activities")

            for activity in self._sort_by_frequency(priority_activities):
                self._schedule_activity(activity, enforce_quota=True)

        # Round 2: Fill remaining capacity (no quotas, prioritize higher priorities)
        logger.info("Round 2: Filling remaining capacity without quotas...")

        # In round 2, still prioritize by priority but allow unlimited capacity
        all_activities = []
        for priority in sorted(activities_by_priority.keys()):
            all_activities.extend(activities_by_priority[priority])

        # Sort by priority, then by how many occurrences are still missing
        def missing_occurrences(activity):
            required = self._calculate_required_occurrences(activity)
            scheduled = self.state.get_occurrence_count(activity.id)
            return required - scheduled

        all_activities.sort(key=lambda a: (a.priority, -missing_occurrences(a)))

        for activity in all_activities:
            required = self._calculate_required_occurrences(activity)
            scheduled = self.state.get_occurrence_count(activity.id)

            if scheduled < required:
                remaining = required - scheduled
                logger.debug(f"  Retrying {activity.id} (P{activity.priority}): {remaining} occurrences remaining")
                self._schedule_activity(activity, enforce_quota=False, max_occurrences=remaining)

        # Log summary
        stats = self.state.get_statistics()
        logger.info(f"Scheduling complete: {stats['total_slots']} slots booked, {stats['failed_count']} activities failed")

        return self.state

    def _group_by_priority(self, activities: List[Activity]) -> Dict[int, List[Activity]]:
        """Group activities by priority level."""
        groups = defaultdict(list)
        for activity in activities:
            groups[activity.priority].append(activity)
        return dict(groups)

    def _sort_by_frequency(self, activities: List[Activity]) -> List[Activity]:
        """Sort activities by frequency importance (DESC).

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

        return sorted(activities, key=lambda a: -frequency_importance(a))

    def _schedule_activity(
        self,
        activity: Activity,
        enforce_quota: bool = True,
        max_occurrences: Optional[int] = None
    ) -> None:
        """Schedule all required occurrences of an activity.

        Args:
            activity: The activity to schedule
            enforce_quota: Whether to enforce daily capacity quotas
            max_occurrences: Maximum occurrences to schedule (for retry logic)
        """
        required_count = self._calculate_required_occurrences(activity)

        # If this is a retry, only schedule remaining occurrences
        if max_occurrences is not None:
            already_scheduled = self.state.get_occurrence_count(activity.id)
            required_count = min(max_occurrences, required_count - already_scheduled)

        logger.debug(f"Scheduling {activity.name} ({activity.id}): {required_count} occurrences required")

        successful_count = 0

        for occurrence_index in range(required_count):
            slot = self._find_best_slot(activity, occurrence_index, enforce_quota)

            if slot:
                self.state.add_booking(slot)
                self.scorer.record_booking(activity, slot.date)

                # Track daily capacity usage
                self.daily_capacity[slot.date][activity.priority] += 1

                successful_count += 1
                logger.debug(f"  ✓ Occurrence {occurrence_index + 1}/{required_count} scheduled: {slot.date} at {slot.start_time}")
            else:
                logger.debug(f"  ✗ Occurrence {occurrence_index + 1}/{required_count} failed to schedule")

        if successful_count < required_count:
            logger.debug(
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
        occurrence_index: int,
        enforce_quota: bool = True
    ) -> Optional[TimeSlot]:
        """Find the best available time slot for an activity occurrence.

        Args:
            activity: The activity to schedule
            occurrence_index: Which occurrence (0-indexed)
            enforce_quota: Whether to enforce daily capacity quotas

        Returns:
            TimeSlot if successful, None if no valid slot found
        """
        candidate_slots = self._generate_candidate_slots(activity, occurrence_index)

        # Score all candidates
        scored_slots = []
        for date, start_time in candidate_slots:
            # Check capacity quota
            if enforce_quota and not self._check_quota(date, activity.priority):
                continue

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

    def _check_quota(self, date: date_type, priority: int) -> bool:
        """Check if scheduling on this date would exceed capacity quota.

        Args:
            date: The date to check
            priority: Priority level of activity

        Returns:
            True if quota allows scheduling, False otherwise
        """
        current_usage = self.daily_capacity[date][priority]
        quota_limit = int(self.MAX_DAILY_SLOTS * self.PRIORITY_QUOTAS[priority])

        return current_usage < quota_limit

    def _generate_candidate_slots(
        self,
        activity: Activity,
        occurrence_index: int
    ) -> List[Tuple[date_type, time_type]]:
        """Generate candidate (date, time) pairs for an activity occurrence.

        Strategy:
        - For Daily: spread evenly across all days
        - For Weekly: spread across weeks, prefer same day of week
        - For Monthly: spread across months
        - For Custom: follow interval_days

        Args:
            activity: The activity to generate slots for
            occurrence_index: Which occurrence (0-indexed)

        Returns:
            List of (date, start_time) tuples to try
        """
        freq = activity.frequency
        candidates = []

        # Generate candidate dates based on frequency pattern
        if freq.pattern == FrequencyPattern.DAILY:
            candidate_date = self.start_date + timedelta(days=occurrence_index)
            if candidate_date <= self.end_date:
                candidates.extend(self._generate_times_for_date(activity, candidate_date))

        elif freq.pattern == FrequencyPattern.WEEKLY:
            # Spread across weeks
            week_number = occurrence_index // freq.count
            within_week_index = occurrence_index % freq.count

            # Try to schedule on preferred days if specified
            if freq.preferred_days:
                target_weekday = freq.preferred_days[within_week_index % len(freq.preferred_days)]
            else:
                # Default: spread across weekdays (0-4)
                target_weekday = within_week_index % 5

            # Find the target date
            week_start = self.start_date + timedelta(weeks=week_number)
            days_to_add = (target_weekday - week_start.weekday()) % 7
            candidate_date = week_start + timedelta(days=days_to_add)

            if candidate_date <= self.end_date:
                candidates.extend(self._generate_times_for_date(activity, candidate_date))

        elif freq.pattern == FrequencyPattern.MONTHLY:
            # Spread across months
            month_number = occurrence_index // freq.count
            candidate_date = self.start_date + timedelta(days=30 * month_number)

            if candidate_date <= self.end_date:
                candidates.extend(self._generate_times_for_date(activity, candidate_date))

        elif freq.pattern == FrequencyPattern.CUSTOM:
            if freq.interval_days:
                candidate_date = self.start_date + timedelta(days=occurrence_index * freq.interval_days)
                if candidate_date <= self.end_date:
                    candidates.extend(self._generate_times_for_date(activity, candidate_date))

        # If primary strategy fails, add backup dates (±1 day)
        if len(candidates) < 3:
            for date, time in list(candidates):
                # Add previous day
                prev_date = date - timedelta(days=1)
                if prev_date >= self.start_date:
                    candidates.extend(self._generate_times_for_date(activity, prev_date))

                # Add next day
                next_date = date + timedelta(days=1)
                if next_date <= self.end_date:
                    candidates.extend(self._generate_times_for_date(activity, next_date))

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
