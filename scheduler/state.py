"""Scheduler state management for tracking bookings and conflicts.

This module maintains the calendar state during scheduling, tracking:
- All booked time slots
- Specialist bookings (for concurrent limit checking)
- Equipment usage (for concurrent limit checking)
- Failed scheduling attempts with reasons
"""

from datetime import date as date_type, time as time_type
from typing import List, Dict, Set
from collections import defaultdict
from dataclasses import dataclass, field

from models import Activity, TimeSlot
from .constraints import ConstraintViolation


@dataclass
class SchedulingAttempt:
    """Record of a failed scheduling attempt."""
    activity: Activity
    attempts: int = 0
    violations: List[ConstraintViolation] = field(default_factory=list)


class SchedulerState:
    """Maintains the state of the scheduler during execution."""

    def __init__(self):
        """Initialize empty scheduler state."""
        self.booked_slots: List[TimeSlot] = []
        self.specialist_bookings: Dict[str, List[TimeSlot]] = defaultdict(list)
        self.equipment_bookings: Dict[str, List[TimeSlot]] = defaultdict(list)
        self.failed_activities: Dict[str, SchedulingAttempt] = {}
        self.activity_occurrences: Dict[str, int] = defaultdict(int)

    def add_booking(self, slot: TimeSlot) -> None:
        """Add a successful booking to state.

        Args:
            slot: The time slot to book
        """
        self.booked_slots.append(slot)

        # Track specialist usage
        if slot.specialist_id:
            self.specialist_bookings[slot.specialist_id].append(slot)

        # Track equipment usage
        for equip_id in slot.equipment_ids:
            self.equipment_bookings[equip_id].append(slot)

        # Track activity occurrence count
        self.activity_occurrences[slot.activity_id] += 1

    def record_failure(
        self,
        activity: Activity,
        violation: ConstraintViolation
    ) -> None:
        """Record a failed scheduling attempt.

        Args:
            activity: The activity that failed to schedule
            violation: The constraint violation that caused failure
        """
        if activity.id not in self.failed_activities:
            self.failed_activities[activity.id] = SchedulingAttempt(
                activity=activity,
                attempts=1,
                violations=[violation]
            )
        else:
            attempt = self.failed_activities[activity.id]
            attempt.attempts += 1
            attempt.violations.append(violation)

    def get_slots_for_date(self, date: date_type) -> List[TimeSlot]:
        """Get all booked slots for a specific date.

        Args:
            date: The date to query

        Returns:
            List of time slots on that date
        """
        return [slot for slot in self.booked_slots if slot.date == date]

    def get_slots_for_activity(self, activity_id: str) -> List[TimeSlot]:
        """Get all booked slots for a specific activity.

        Args:
            activity_id: The activity ID to query

        Returns:
            List of time slots for that activity
        """
        return [slot for slot in self.booked_slots if slot.activity_id == activity_id]

    def get_occurrence_count(self, activity_id: str) -> int:
        """Get the number of times an activity has been scheduled.

        Args:
            activity_id: The activity ID to query

        Returns:
            Number of scheduled occurrences
        """
        return self.activity_occurrences[activity_id]

    def get_date_range(self) -> tuple[date_type, date_type] | None:
        """Get the date range of all bookings.

        Returns:
            (start_date, end_date) or None if no bookings
        """
        if not self.booked_slots:
            return None

        dates = [slot.date for slot in self.booked_slots]
        return min(dates), max(dates)

    def get_statistics(self) -> Dict:
        """Get scheduling statistics.

        Returns:
            Dictionary with statistics about the schedule
        """
        if not self.booked_slots:
            return {
                "total_slots": 0,
                "unique_activities": 0,
                "date_range": None,
                "busiest_day": None,
                "specialist_usage": {},
                "equipment_usage": {},
                "failed_count": len(self.failed_activities)
            }

        # Calculate statistics
        dates = [slot.date for slot in self.booked_slots]
        date_counts = defaultdict(int)
        for d in dates:
            date_counts[d] += 1

        busiest_day = max(date_counts.items(), key=lambda x: x[1]) if date_counts else None

        return {
            "total_slots": len(self.booked_slots),
            "unique_activities": len(self.activity_occurrences),
            "date_range": (min(dates), max(dates)),
            "busiest_day": busiest_day,
            "specialist_usage": {
                spec_id: len(slots)
                for spec_id, slots in self.specialist_bookings.items()
            },
            "equipment_usage": {
                equip_id: len(slots)
                for equip_id, slots in self.equipment_bookings.items()
            },
            "failed_count": len(self.failed_activities)
        }

    def get_failure_report(self) -> List[Dict]:
        """Get detailed report of failed scheduling attempts.

        Returns:
            List of failure records with activity details and reasons
        """
        report = []

        for activity_id, attempt in self.failed_activities.items():
            # Count violation types
            violation_counts = defaultdict(int)
            for v in attempt.violations:
                violation_counts[v.constraint_type] += 1

            report.append({
                "activity_id": activity_id,
                "activity_name": attempt.activity.name,
                "activity_type": attempt.activity.type.value,
                "priority": attempt.activity.priority,
                "attempts": attempt.attempts,
                "violation_types": dict(violation_counts),
                "sample_reason": attempt.violations[0].reason if attempt.violations else None
            })

        # Sort by priority (most critical first)
        report.sort(key=lambda x: x["priority"])

        return report

    def clear(self) -> None:
        """Clear all state (useful for testing)."""
        self.booked_slots.clear()
        self.specialist_bookings.clear()
        self.equipment_bookings.clear()
        self.failed_activities.clear()
        self.activity_occurrences.clear()
