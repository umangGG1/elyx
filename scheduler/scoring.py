"""Soft constraint scoring for time slot selection.

This module implements the scoring logic that determines HOW GOOD a valid time slot is
(0-10 scale where higher is better).

Scoring factors:
1. Time preference matching (0-10): How well does the slot match preferred time windows?
2. Activity grouping bonus (0-2): Bonus for scheduling similar activities on same day
3. Overcrowding penalty (0-2): Penalty for days with too many activities
4. Consistency bonus (0-2): Bonus for consistent weekly patterns
5. Day preference (0-1): Bonus for preferred days of week
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Dict
from collections import defaultdict

from models import Activity, TimeSlot


class SlotScorer:
    """Scores time slots based on soft constraints and preferences."""

    def __init__(self):
        """Initialize scorer with tracking state."""
        self.daily_counts: Dict[date_type, int] = defaultdict(int)
        self.weekly_patterns: Dict[str, List[int]] = defaultdict(list)  # activity_id -> [weekdays]

    def score_slot(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot]
    ) -> float:
        """Score a valid time slot (0-10 scale, higher is better).

        Args:
            activity: The activity to schedule
            date: The date to schedule on
            start_time: The start time
            booked_slots: Already scheduled time slots

        Returns:
            Score from 0-10 (higher = better fit)
        """
        score = 0.0

        # 1. Time preference matching (0-10 points)
        score += self._score_time_preference(activity, start_time)

        # 2. Activity grouping bonus (0-2 points)
        score += self._score_grouping(activity, date, booked_slots)

        # 3. Overcrowding penalty (0 to -2 points)
        score += self._score_overcrowding(date, booked_slots)

        # 4. Consistency bonus (0-2 points)
        score += self._score_consistency(activity, date)

        # 5. Day preference (0-1 point)
        score += self._score_day_preference(activity, date)

        return max(0.0, min(10.0, score))  # Clamp to [0, 10]

    def _score_time_preference(self, activity: Activity, start_time: time_type) -> float:
        """Score how well the time matches activity preferences (0-10).

        If activity has a time window:
        - Center of window = 10 points
        - Edges of window = 5 points
        - Linear interpolation between

        If no time window:
        - Morning (6-9 AM) = 8 points (generally preferred)
        - Midday (9 AM-5 PM) = 7 points
        - Evening (5-8 PM) = 6 points
        - Late/early = 4 points
        """
        if activity.time_window_start and activity.time_window_end:
            # Calculate position within window (0.0 = start, 1.0 = end)
            window_start_minutes = activity.time_window_start.hour * 60 + activity.time_window_start.minute
            window_end_minutes = activity.time_window_end.hour * 60 + activity.time_window_end.minute
            slot_minutes = start_time.hour * 60 + start_time.minute

            window_duration = window_end_minutes - window_start_minutes
            if window_duration <= 0:
                return 5.0

            position = (slot_minutes - window_start_minutes) / window_duration

            # Parabolic scoring: peak at center (0.5), lower at edges
            # f(x) = -20(x - 0.5)^2 + 10
            # This gives: center=10, edges≈5
            distance_from_center = abs(position - 0.5)
            score = 10.0 - (20.0 * distance_from_center ** 2)
            return max(5.0, score)

        else:
            # No time window - use general preferences
            hour = start_time.hour

            if 6 <= hour < 9:
                return 8.0  # Morning
            elif 9 <= hour < 17:
                return 7.0  # Business hours
            elif 17 <= hour < 20:
                return 6.0  # Evening
            else:
                return 4.0  # Late night/early morning

    def _score_grouping(
        self,
        activity: Activity,
        date: date_type,
        booked_slots: List[TimeSlot]
    ) -> float:
        """Bonus for scheduling similar activities on same day (0-2).

        Grouping similar activities (e.g., multiple fitness sessions) can be
        beneficial for motivation and routine building.
        """
        same_day_slots = [s for s in booked_slots if s.date == date]

        if not same_day_slots:
            return 0.0

        # Count activities of same type on this day
        same_type_count = 0
        for slot in same_day_slots:
            # We need to look up the activity to check type
            # For now, we'll use a simple heuristic based on activity ID prefix
            # (In full implementation, would pass activity lookup dict)
            if activity.id[:3] == slot.activity_id[:3]:  # Same prefix = likely same type
                same_type_count += 1

        # Bonus: 1 point for 1 similar activity, 2 points for 2+
        return min(2.0, same_type_count)

    def _score_overcrowding(
        self,
        date: date_type,
        booked_slots: List[TimeSlot]
    ) -> float:
        """Penalty for days with too many activities (0 to -2).

        Having too many activities in one day can be overwhelming.
        Target: 2-4 activities per day is ideal.
        """
        same_day_count = sum(1 for s in booked_slots if s.date == date)

        if same_day_count <= 3:
            return 0.0  # Ideal range
        elif same_day_count == 4:
            return -0.5  # Starting to get busy
        elif same_day_count == 5:
            return -1.0  # Quite busy
        else:
            return -2.0  # Overcrowded

    def _score_consistency(self, activity: Activity, date: date_type) -> float:
        """Bonus for maintaining consistent weekly patterns (0-2).

        Scheduling activities on the same day of week builds routine.
        """
        weekday = date.weekday()
        past_weekdays = self.weekly_patterns.get(activity.id, [])

        if not past_weekdays:
            return 0.0  # First occurrence

        # Count how many times this activity was scheduled on this weekday
        same_weekday_count = past_weekdays.count(weekday)

        if same_weekday_count >= 2:
            return 2.0  # Strong pattern
        elif same_weekday_count == 1:
            return 1.0  # Emerging pattern
        else:
            return 0.0

    def _score_day_preference(self, activity: Activity, date: date_type) -> float:
        """Bonus for scheduling on preferred days (0-1).

        If activity has preferred days in frequency pattern, give bonus.
        """
        if not activity.frequency.preferred_days:
            return 0.0

        weekday = date.weekday()
        if weekday in activity.frequency.preferred_days:
            return 1.0
        else:
            return 0.0

    def record_booking(self, activity: Activity, date: date_type):
        """Record a booking to update scoring state.

        This allows the scorer to track patterns and adjust future scores.
        """
        self.daily_counts[date] += 1
        self.weekly_patterns[activity.id].append(date.weekday())
