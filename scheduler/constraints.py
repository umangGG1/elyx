"""Hard constraint checking for activity scheduling.

This module implements the constraint validation logic that determines whether
an activity CAN be scheduled at a given time slot (binary yes/no).

Hard constraints include:
- Specialist availability (day of week + time range + days off + concurrent limit)
- Equipment availability (maintenance windows + concurrent usage limit)
- Travel conflicts (remote-only activities during travel OR no scheduling during certain travel)
- Time window constraints (activity must fit in specified window)
- Time overlap detection (no double-booking)
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Optional, Dict, Set
from dataclasses import dataclass

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot


@dataclass
class ConstraintViolation:
    """Represents a constraint violation with details."""
    constraint_type: str  # "specialist", "equipment", "travel", "time_window", "overlap"
    reason: str
    activity_id: str
    date: date_type
    start_time: time_type


class ConstraintChecker:
    """Validates hard constraints for activity scheduling."""

    def __init__(
        self,
        specialists: List[Specialist],
        equipment: List[Equipment],
        travel_periods: List[TravelPeriod]
    ):
        """Initialize constraint checker with resource data.

        Args:
            specialists: List of all specialists with availability
            equipment: List of all equipment with maintenance windows
            travel_periods: List of client travel periods
        """
        self.specialists = {s.id: s for s in specialists}
        self.equipment = {e.id: e for e in equipment}
        self.travel_periods = travel_periods

    def check_time_slot(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot]
    ) -> Optional[ConstraintViolation]:
        """Check if an activity can be scheduled at a specific time slot.

        Returns None if valid, or ConstraintViolation if invalid.

        Args:
            activity: The activity to schedule
            date: The date to schedule on
            start_time: The start time
            booked_slots: Already scheduled time slots (for overlap checking)
        """
        # Check time window constraint
        if activity.time_window_start and activity.time_window_end:
            end_time = self._add_minutes_to_time(start_time, activity.duration_minutes)

            if start_time < activity.time_window_start or end_time > activity.time_window_end:
                return ConstraintViolation(
                    constraint_type="time_window",
                    reason=f"Activity must be scheduled between {activity.time_window_start} and {activity.time_window_end}",
                    activity_id=activity.id,
                    date=date,
                    start_time=start_time
                )

        # Check time overlap
        overlap = self._check_overlap(activity, date, start_time, booked_slots)
        if overlap:
            return overlap

        # Check specialist availability
        if activity.specialist_id:
            violation = self._check_specialist(activity, date, start_time)
            if violation:
                return violation

        # Check equipment availability
        if activity.equipment_ids:
            violation = self._check_equipment(activity, date, start_time, booked_slots)
            if violation:
                return violation

        # Check travel conflicts
        violation = self._check_travel(activity, date)
        if violation:
            return violation

        return None  # All constraints satisfied

    def _check_overlap(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot]
    ) -> Optional[ConstraintViolation]:
        """Check if activity overlaps with any existing bookings."""
        end_time = self._add_minutes_to_time(start_time, activity.duration_minutes)

        for slot in booked_slots:
            if slot.date != date:
                continue

            slot_end = self._add_minutes_to_time(slot.start_time, slot.duration_minutes)

            # Check for overlap: (start1 < end2) AND (start2 < end1)
            if start_time < slot_end and slot.start_time < end_time:
                return ConstraintViolation(
                    constraint_type="overlap",
                    reason=f"Overlaps with {slot.activity_id} at {slot.start_time}",
                    activity_id=activity.id,
                    date=date,
                    start_time=start_time
                )

        return None

    def _check_specialist(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type
    ) -> Optional[ConstraintViolation]:
        """Check if specialist is available at the given time."""
        specialist = self.specialists.get(activity.specialist_id)
        if not specialist:
            return ConstraintViolation(
                constraint_type="specialist",
                reason=f"Specialist {activity.specialist_id} not found",
                activity_id=activity.id,
                date=date,
                start_time=start_time
            )

        # Check if on a day off
        if date in specialist.days_off:
            return ConstraintViolation(
                constraint_type="specialist",
                reason=f"{specialist.name} is unavailable on {date} (day off)",
                activity_id=activity.id,
                date=date,
                start_time=start_time
            )

        # Check day of week availability
        day_of_week = date.weekday()  # 0=Monday, 6=Sunday
        available_blocks = [
            block for block in specialist.availability
            if block.day_of_week == day_of_week
        ]

        if not available_blocks:
            return ConstraintViolation(
                constraint_type="specialist",
                reason=f"{specialist.name} doesn't work on {date.strftime('%A')}s",
                activity_id=activity.id,
                date=date,
                start_time=start_time
            )

        # Check if activity fits within any availability block
        end_time = self._add_minutes_to_time(start_time, activity.duration_minutes)

        for block in available_blocks:
            if block.start_time <= start_time and end_time <= block.end_time:
                return None  # Found a valid block

        return ConstraintViolation(
            constraint_type="specialist",
            reason=f"{specialist.name} not available at {start_time} on {date.strftime('%A')}s",
            activity_id=activity.id,
            date=date,
            start_time=start_time
        )

    def _check_equipment(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot]
    ) -> Optional[ConstraintViolation]:
        """Check if all required equipment is available."""
        end_time = self._add_minutes_to_time(start_time, activity.duration_minutes)

        for equip_id in activity.equipment_ids:
            equip = self.equipment.get(equip_id)
            if not equip:
                return ConstraintViolation(
                    constraint_type="equipment",
                    reason=f"Equipment {equip_id} not found",
                    activity_id=activity.id,
                    date=date,
                    start_time=start_time
                )

            # Check maintenance windows
            for window in equip.maintenance_windows:
                if window.start_date <= date <= window.end_date:
                    # If no specific times, maintenance is all day
                    if window.start_time is None or window.end_time is None:
                        return ConstraintViolation(
                            constraint_type="equipment",
                            reason=f"{equip.name} under maintenance on {date}",
                            activity_id=activity.id,
                            date=date,
                            start_time=start_time
                        )

                    # Check time overlap with maintenance
                    if start_time < window.end_time and window.start_time < end_time:
                        return ConstraintViolation(
                            constraint_type="equipment",
                            reason=f"{equip.name} under maintenance {window.start_time}-{window.end_time}",
                            activity_id=activity.id,
                            date=date,
                            start_time=start_time
                        )

            # Check concurrent usage limit
            concurrent_count = sum(
                1 for slot in booked_slots
                if equip_id in slot.equipment_ids
                and slot.date == date
                and self._times_overlap(
                    start_time, end_time,
                    slot.start_time, self._add_minutes_to_time(slot.start_time, slot.duration_minutes)
                )
            )

            if concurrent_count >= equip.max_concurrent_users:
                return ConstraintViolation(
                    constraint_type="equipment",
                    reason=f"{equip.name} at capacity ({equip.max_concurrent_users} users)",
                    activity_id=activity.id,
                    date=date,
                    start_time=start_time
                )

        return None

    def _check_travel(
        self,
        activity: Activity,
        date: date_type
    ) -> Optional[ConstraintViolation]:
        """Check if travel conflicts with activity scheduling."""
        for travel in self.travel_periods:
            if travel.start_date <= date <= travel.end_date:
                # If travel requires remote-only, check if activity supports it
                if travel.remote_activities_only and not activity.remote_capable:
                    return ConstraintViolation(
                        constraint_type="travel",
                        reason=f"Traveling to {travel.location} (remote-only), activity not remote-capable",
                        activity_id=activity.id,
                        date=date,
                        start_time=time_type(0, 0)  # Placeholder
                    )

        return None

    def _add_minutes_to_time(self, t: time_type, minutes: int) -> time_type:
        """Add minutes to a time object, handling day overflow."""
        dt = datetime.combine(date_type.today(), t)
        dt += timedelta(minutes=minutes)
        return dt.time()

    def _times_overlap(
        self,
        start1: time_type,
        end1: time_type,
        start2: time_type,
        end2: time_type
    ) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1
