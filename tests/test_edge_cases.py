"""
Edge case tests for the health activity scheduler.

Tests extreme and boundary conditions to ensure robustness.
"""

import pytest
from datetime import date, time, timedelta
from models.activity import Activity, Frequency, FrequencyPattern, TimeWindow
from models.constraints import (
    Specialist, SpecialistType, AvailabilityBlock,
    Equipment, EquipmentType, Location, MaintenanceWindow,
    TravelPeriod
)
from scheduler.greedy import GreedyScheduler


@pytest.fixture
def start_date():
    """Fixed start date for testing."""
    return date(2025, 12, 9)


@pytest.fixture
def end_date():
    """Fixed end date for testing (7 days)."""
    return date(2025, 12, 15)


@pytest.fixture
def single_day_period():
    """Single day period for boundary testing."""
    return date(2025, 12, 9), date(2025, 12, 9)


def test_empty_activities_list(start_date, end_date):
    """Test that scheduler handles empty activities list gracefully."""
    scheduler = GreedyScheduler(
        activities=[],  # Empty list
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Should return empty schedule without errors
    assert schedule is not None
    assert len(schedule.scheduled) == 0
    assert len(schedule.failed) == 0


def test_single_day_period():
    """Test scheduler with a single-day scheduling period."""
    single_date = date(2025, 12, 9)

    # Create a simple daily activity
    activity = Activity(
        id="act_single_001",
        name="Single Day Activity",
        type="Exercise",
        priority=1,
        duration_minutes=30,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(10, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=single_date,
        end_date=single_date  # Same as start date
    )

    schedule = scheduler.schedule()

    # Should schedule exactly 1 occurrence on the single day
    assert len(schedule.scheduled) == 1
    assert schedule.scheduled[0].date == single_date
    assert len(schedule.failed) == 0


def test_very_long_activity(start_date, end_date):
    """Test scheduling with a very long activity (3+ hours)."""
    # Create a 4-hour activity (240 minutes)
    long_activity = Activity(
        id="act_long_001",
        name="Long Activity",
        type="Workshop",
        priority=1,
        duration_minutes=240,  # 4 hours
        frequency=Frequency(pattern=FrequencyPattern.WEEKLY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(18, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[long_activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Should schedule successfully despite long duration
    assert len(schedule.scheduled) >= 1

    # Verify duration is preserved
    for slot in schedule.scheduled:
        assert slot.duration_minutes == 240


def test_very_short_activity(start_date, end_date):
    """Test scheduling with a very short activity (5 minutes)."""
    # Create a 5-minute activity
    short_activity = Activity(
        id="act_short_001",
        name="Short Activity",
        type="Quick Check",
        priority=1,
        duration_minutes=5,  # 5 minutes
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(10, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[short_activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Should schedule all 7 days
    assert len(schedule.scheduled) == 7

    # Verify duration is preserved
    for slot in schedule.scheduled:
        assert slot.duration_minutes == 5


def test_all_specialists_unavailable(start_date, end_date):
    """Test that activities fail gracefully when all specialists are unavailable."""
    # Create specialist with no availability
    unavailable_specialist = Specialist(
        id="spec_unavail_001",
        name="Unavailable Specialist",
        type=SpecialistType.TRAINER,
        availability_blocks=[],  # No availability
        days_off=list(range(7)),  # Off every day
        holidays=[]
    )

    # Create activity requiring this specialist
    activity = Activity(
        id="act_need_spec_001",
        name="Activity Needing Specialist",
        type="Training",
        priority=1,
        duration_minutes=60,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(10, 0)),
        requires_specialist="spec_unavail_001",
        requires_equipment=None,
        can_be_remote=False,
        location=Location.GYM
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[unavailable_specialist],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # All occurrences should fail (specialist unavailable)
    assert len(schedule.scheduled) == 0
    assert len(schedule.failed) > 0


def test_high_frequency_activity(start_date, end_date):
    """Test scheduling with high frequency activity (7x per week)."""
    # Create activity requiring 7 occurrences per week
    high_freq_activity = Activity(
        id="act_high_freq_001",
        name="Daily Activity",
        type="Exercise",
        priority=1,
        duration_minutes=30,
        frequency=Frequency(pattern=FrequencyPattern.WEEKLY, count=7),  # 7x per week
        time_window=TimeWindow(start_time=time(6, 0), end_time=time(21, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[high_freq_activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Should schedule all 7 occurrences in the 7-day period
    assert len(schedule.scheduled) == 7

    # Verify no duplicates on the same day
    scheduled_dates = [slot.date for slot in schedule.scheduled]
    assert len(scheduled_dates) == len(set(scheduled_dates))


def test_tight_time_window(start_date, end_date):
    """Test scheduling with a very tight time window (30 minutes)."""
    # Create activity with tight 30-minute window
    tight_window_activity = Activity(
        id="act_tight_001",
        name="Tight Window Activity",
        type="Appointment",
        priority=1,
        duration_minutes=25,  # 25 minutes in 30-minute window
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(9, 30)),  # 30-min window
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[tight_window_activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Should schedule successfully
    assert len(schedule.scheduled) == 7

    # Verify all slots are within the tight window
    for slot in schedule.scheduled:
        assert slot.start_time >= time(9, 0)
        # End time = start_time + 25 minutes, should be <= 9:30
        end_time = (
            timedelta(hours=slot.start_time.hour, minutes=slot.start_time.minute)
            + timedelta(minutes=25)
        )
        assert end_time <= timedelta(hours=9, minutes=30)


def test_entire_period_is_travel(start_date, end_date):
    """Test scheduling when the entire period is marked as travel."""
    # Create travel period covering all 7 days
    full_travel = TravelPeriod(
        start_date=start_date,
        end_date=end_date
    )

    # Create non-remote activity (should fail during travel)
    non_remote_activity = Activity(
        id="act_non_remote_001",
        name="Non-Remote Activity",
        type="Gym Session",
        priority=1,
        duration_minutes=60,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(9, 0), end_time=time(10, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=False,  # Cannot be done remotely
        location=Location.GYM
    )

    # Create remote activity (should succeed during travel)
    remote_activity = Activity(
        id="act_remote_001",
        name="Remote Activity",
        type="Online Meeting",
        priority=1,
        duration_minutes=30,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        time_window=TimeWindow(start_time=time(10, 0), end_time=time(11, 0)),
        requires_specialist=None,
        requires_equipment=None,
        can_be_remote=True,  # Can be done remotely
        location=Location.HOME
    )

    scheduler = GreedyScheduler(
        activities=[non_remote_activity, remote_activity],
        specialists=[],
        equipment=[],
        travel_periods=[full_travel],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # Non-remote activity should fail all occurrences
    non_remote_slots = [s for s in schedule.scheduled if s.activity_id == "act_non_remote_001"]
    assert len(non_remote_slots) == 0

    # Remote activity should succeed all occurrences
    remote_slots = [s for s in schedule.scheduled if s.activity_id == "act_remote_001"]
    assert len(remote_slots) == 7


def test_overlapping_time_windows_multiple_activities(start_date, end_date):
    """Test that multiple activities with overlapping time windows don't create conflicts."""
    # Create 3 P1 activities with overlapping time windows
    activities = []
    for i in range(3):
        activity = Activity(
            id=f"act_overlap_{i:03d}",
            name=f"Activity {i+1}",
            type="Exercise",
            priority=1,
            duration_minutes=30,
            frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
            time_window=TimeWindow(start_time=time(9, 0), end_time=time(12, 0)),  # Same window
            requires_specialist=None,
            requires_equipment=None,
            can_be_remote=True,
            location=Location.HOME
        )
        activities.append(activity)

    scheduler = GreedyScheduler(
        activities=activities,
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    schedule = scheduler.schedule()

    # All activities should be scheduled
    assert len(schedule.scheduled) == 21  # 3 activities × 7 days

    # Verify no overlaps on any day
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        day_slots = [s for s in schedule.scheduled if s.date == current_date]

        # Check all pairs for overlaps
        for i, slot1 in enumerate(day_slots):
            for slot2 in day_slots[i+1:]:
                # Calculate end times
                end1 = (
                    timedelta(hours=slot1.start_time.hour, minutes=slot1.start_time.minute)
                    + timedelta(minutes=slot1.duration_minutes)
                )
                end2 = (
                    timedelta(hours=slot2.start_time.hour, minutes=slot2.start_time.minute)
                    + timedelta(minutes=slot2.duration_minutes)
                )
                start1 = timedelta(hours=slot1.start_time.hour, minutes=slot1.start_time.minute)
                start2 = timedelta(hours=slot2.start_time.hour, minutes=slot2.start_time.minute)

                # Check for overlap: slots overlap if start1 < end2 AND start2 < end1
                overlaps = start1 < end2 and start2 < end1
                assert not overlaps, f"Overlap detected on {current_date}: {slot1.activity_id} and {slot2.activity_id}"


def test_zero_duration_activity():
    """Test that activities with zero duration are rejected by validation."""
    # This should be caught by Pydantic validation
    with pytest.raises(Exception):  # Pydantic will raise validation error
        Activity(
            id="act_zero_001",
            name="Zero Duration",
            type="Invalid",
            priority=1,
            duration_minutes=0,  # Invalid
            frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
            time_window=TimeWindow(start_time=time(9, 0), end_time=time(10, 0)),
            requires_specialist=None,
            requires_equipment=None,
            can_be_remote=True,
            location=Location.HOME
        )
