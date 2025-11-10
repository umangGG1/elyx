"""Test suite for scheduler logic and algorithm behavior."""

import pytest
from datetime import date, time, timedelta
from models.activity import Activity, ActivityType, Frequency, FrequencyPattern, Location
from models.constraints import Specialist, SpecialistType, AvailabilityBlock
from models.constraints import Equipment, TravelPeriod, MaintenanceWindow
from scheduler.greedy import GreedyScheduler
from scheduler.state import SchedulerState


@pytest.fixture
def start_date():
    """Fixed start date for testing."""
    return date(2025, 12, 9)


@pytest.fixture
def end_date():
    """Fixed end date for testing (7 days)."""
    return date(2025, 12, 15)


@pytest.fixture
def simple_specialist():
    """Create a specialist available all week."""
    return Specialist(
        id="spec_test_001",
        name="Test Specialist",
        type=SpecialistType.TRAINER,
        availability_blocks=[
            AvailabilityBlock(day=i, start_time="06:00", end_time="21:00")
            for i in range(7)
        ],
        days_off=[],
        holidays=[]
    )


@pytest.fixture
def simple_equipment():
    """Create equipment with no maintenance."""
    return Equipment(
        id="equip_test_001",
        name="Test Equipment",
        location="Gym",
        maintenance_windows=[]
    )


def test_priority_1_activities_scheduled_first(start_date, end_date):
    """Test that P1 activities are scheduled before P2 activities.

    Create 2 activities:
    - P1 activity: Daily, 30min
    - P2 activity: Daily, 30min, same time window

    Expected: All P1 occurrences scheduled before any P2.
    """
    # Create P1 activity
    p1_activity = Activity(
        id="p1_test",
        name="Critical Activity",
        type=ActivityType.MEDICATION,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=30,
        time_window_start="08:00",
        time_window_end="09:00",
        location=Location.HOME,
        remote_capable=False,
        details="P1 test activity"
    )

    # Create P2 activity (same time window = conflict)
    p2_activity = Activity(
        id="p2_test",
        name="Important Activity",
        type=ActivityType.FITNESS,
        priority=2,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=30,
        time_window_start="08:00",
        time_window_end="09:00",
        location=Location.HOME,
        remote_capable=False,
        details="P2 test activity"
    )

    # Run scheduler
    scheduler = GreedyScheduler(
        activities=[p1_activity, p2_activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Assert P1 got all 7 days (Dec 9-15)
    p1_count = state.get_occurrence_count("p1_test")
    assert p1_count == 7, f"Expected P1 to schedule 7 times, got {p1_count}"

    # Assert P2 got 0 (blocked by P1)
    p2_count = state.get_occurrence_count("p2_test")
    assert p2_count == 0, f"Expected P2 to schedule 0 times (blocked), got {p2_count}"


def test_priority_ordering_in_schedule(start_date, end_date):
    """Test that activities are scheduled in priority order.

    Create 5 activities (P1-P5) with no conflicts.
    Expected: All should succeed, P1 scheduled first.
    """
    activities = []
    for priority in range(1, 6):
        activity = Activity(
            id=f"p{priority}_test",
            name=f"Priority {priority} Activity",
            type=ActivityType.FITNESS,
            priority=priority,
            frequency=Frequency(pattern=FrequencyPattern.WEEKLY, count=1),
            duration_minutes=30,
            location=Location.HOME,
            remote_capable=False,
            details=f"P{priority} test"
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

    state = scheduler.schedule()

    # All activities should succeed (no conflicts)
    for priority in range(1, 6):
        count = state.get_occurrence_count(f"p{priority}_test")
        assert count == 1, f"P{priority} should schedule 1 time, got {count}"


def test_no_specialist_double_booking(start_date, end_date, simple_specialist):
    """Test that specialist is not double-booked.

    Create 2 activities requiring same specialist at same time.
    Expected: Only 1 scheduled, other fails.
    """
    # Activity 1: Daily at 08:00
    activity1 = Activity(
        id="act1_specialist",
        name="Activity 1",
        type=ActivityType.FITNESS,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        time_window_start="08:00",
        time_window_end="09:00",
        specialist_id="spec_test_001",
        location=Location.GYM,
        remote_capable=False,
        details="Test activity 1"
    )

    # Activity 2: Daily at 08:00 (conflicts with activity 1)
    activity2 = Activity(
        id="act2_specialist",
        name="Activity 2",
        type=ActivityType.FITNESS,
        priority=2,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        time_window_start="08:00",
        time_window_end="09:00",
        specialist_id="spec_test_001",
        location=Location.GYM,
        remote_capable=False,
        details="Test activity 2"
    )

    scheduler = GreedyScheduler(
        activities=[activity1, activity2],
        specialists=[simple_specialist],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Activity 1 (P1) should get all 7 slots
    act1_count = state.get_occurrence_count("act1_specialist")
    assert act1_count == 7, f"Activity 1 (P1) should schedule 7 times, got {act1_count}"

    # Activity 2 (P2) should fail (specialist busy)
    act2_count = state.get_occurrence_count("act2_specialist")
    assert act2_count == 0, f"Activity 2 (P2) should fail (specialist busy), got {act2_count}"

    # Verify no double-booking in booked slots
    specialist_slots = [
        slot for slot in state.booked_slots
        if slot.specialist_id == "spec_test_001"
    ]

    # Check for time overlaps
    for i, slot1 in enumerate(specialist_slots):
        for slot2 in specialist_slots[i+1:]:
            if slot1.date == slot2.date:
                # Parse times and check for overlap
                from datetime import datetime
                time1_start = datetime.strptime(slot1.start_time, "%H:%M")
                time1_end = time1_start + timedelta(minutes=slot1.duration_minutes)
                time2_start = datetime.strptime(slot2.start_time, "%H:%M")
                time2_end = time2_start + timedelta(minutes=slot2.duration_minutes)

                # Assert no overlap
                assert time1_end <= time2_start or time2_end <= time1_start, \
                    f"Specialist double-booked: {slot1.date} {slot1.start_time}-{slot2.start_time}"


def test_specialist_availability_respected(start_date, end_date):
    """Test that specialist availability blocks are respected.

    Create specialist only available Monday-Wednesday 08:00-12:00.
    Create activity requiring specialist daily.
    Expected: Only Mon-Wed scheduled, Thu-Sun fail.
    """
    # Specialist available Mon-Wed only
    limited_specialist = Specialist(
        id="spec_limited",
        name="Limited Specialist",
        type=SpecialistType.TRAINER,
        availability_blocks=[
            AvailabilityBlock(day=0, start_time="08:00", end_time="12:00"),  # Monday
            AvailabilityBlock(day=1, start_time="08:00", end_time="12:00"),  # Tuesday
            AvailabilityBlock(day=2, start_time="08:00", end_time="12:00"),  # Wednesday
        ],
        days_off=[3, 4, 5, 6],  # Thu-Sun off
        holidays=[]
    )

    activity = Activity(
        id="daily_specialist_activity",
        name="Daily Specialist Activity",
        type=ActivityType.THERAPY,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        specialist_id="spec_limited",
        location=Location.CLINIC,
        remote_capable=False,
        details="Requires limited specialist"
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[limited_specialist],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Should schedule 3 times (Mon-Wed) in 7-day period
    count = state.get_occurrence_count("daily_specialist_activity")
    assert count == 3, f"Expected 3 occurrences (Mon-Wed), got {count}"

    # Verify all scheduled slots are Mon-Wed
    for slot in state.booked_slots:
        if slot.activity_id == "daily_specialist_activity":
            slot_date = date.fromisoformat(slot.date)
            weekday = slot_date.weekday()
            assert weekday in [0, 1, 2], f"Activity scheduled on {slot_date.strftime('%A')} (not Mon-Wed)"


def test_no_equipment_overallocation(start_date, end_date, simple_equipment):
    """Test that equipment is not double-booked.

    Create 2 activities requiring same equipment at overlapping times.
    Expected: Only 1 scheduled, other fails or schedules at different time.
    """
    activity1 = Activity(
        id="act1_equipment",
        name="Equipment Activity 1",
        type=ActivityType.FITNESS,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        time_window_start="08:00",
        time_window_end="09:00",
        equipment_ids=["equip_test_001"],
        location=Location.GYM,
        remote_capable=False,
        details="Test equipment conflict 1"
    )

    activity2 = Activity(
        id="act2_equipment",
        name="Equipment Activity 2",
        type=ActivityType.FITNESS,
        priority=2,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        time_window_start="08:00",
        time_window_end="09:00",
        equipment_ids=["equip_test_001"],
        location=Location.GYM,
        remote_capable=False,
        details="Test equipment conflict 2"
    )

    scheduler = GreedyScheduler(
        activities=[activity1, activity2],
        specialists=[],
        equipment=[simple_equipment],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # P1 should get all 7 days
    act1_count = state.get_occurrence_count("act1_equipment")
    assert act1_count == 7, f"P1 should schedule 7 times, got {act1_count}"

    # P2 should fail (equipment busy)
    act2_count = state.get_occurrence_count("act2_equipment")
    assert act2_count == 0, f"P2 should fail (equipment busy), got {act2_count}"


def test_equipment_maintenance_windows(start_date, end_date):
    """Test that equipment maintenance windows are respected.

    Create equipment with maintenance on specific day/time.
    Create activity requiring equipment.
    Expected: Activity not scheduled during maintenance.
    """
    from models.constraints import MaintenanceWindow

    # Equipment unavailable on Dec 10 (Wednesday) 10:00-12:00
    maintenance_date = date(2025, 12, 10)
    equipment_with_maintenance = Equipment(
        id="equip_maintenance",
        name="Equipment Under Maintenance",
        location="Gym",
        maintenance_windows=[
            MaintenanceWindow(
                start_date=maintenance_date,
                end_date=maintenance_date,
                start_time=time(10, 0),
                end_time=time(12, 0)
            )
        ]
    )

    activity = Activity(
        id="maintenance_test_activity",
        name="Maintenance Test",
        type=ActivityType.FITNESS,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        time_window_start="10:00",
        time_window_end="12:00",
        equipment_ids=["equip_maintenance"],
        location=Location.GYM,
        remote_capable=False,
        details="Should avoid maintenance window"
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[],
        equipment=[equipment_with_maintenance],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Should schedule 6 times (7 days - 1 maintenance day)
    count = state.get_occurrence_count("maintenance_test_activity")
    assert count == 6, f"Expected 6 occurrences (avoiding maintenance), got {count}"

    # Verify no slots on maintenance day at maintenance time
    for slot in state.booked_slots:
        if slot.activity_id == "maintenance_test_activity":
            if slot.date == maintenance_date.isoformat():
                assert False, f"Activity scheduled during maintenance window: {slot.date} {slot.start_time}"


def test_travel_periods_respected(start_date, end_date):
    """Test that non-remote activities are not scheduled during travel.

    Create travel period and non-remote activity.
    Expected: Activity not scheduled during travel.
    """
    # Travel from Dec 13-14 (Sat-Sun)
    travel_period = TravelPeriod(
        start_date=date(2025, 12, 13),
        end_date=date(2025, 12, 14),
        location="Vacation",
        remote_capable=False
    )

    # Non-remote activity (daily)
    non_remote_activity = Activity(
        id="non_remote_activity",
        name="Non-Remote Activity",
        type=ActivityType.FITNESS,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=60,
        location=Location.GYM,
        remote_capable=False,
        details="Cannot do during travel"
    )

    scheduler = GreedyScheduler(
        activities=[non_remote_activity],
        specialists=[],
        equipment=[],
        travel_periods=[travel_period],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Should schedule 5 times (7 days - 2 travel days)
    count = state.get_occurrence_count("non_remote_activity")
    assert count == 5, f"Expected 5 occurrences (avoiding travel), got {count}"

    # Verify no slots during travel
    travel_dates = {date(2025, 12, 13).isoformat(), date(2025, 12, 14).isoformat()}
    for slot in state.booked_slots:
        if slot.activity_id == "non_remote_activity":
            assert slot.date not in travel_dates, f"Non-remote activity scheduled during travel: {slot.date}"


def test_remote_activity_during_travel(start_date, end_date):
    """Test that remote-capable activities CAN be scheduled during travel.

    Create travel period and remote-capable activity.
    Expected: Activity scheduled including during travel.
    """
    travel_period = TravelPeriod(
        start_date=date(2025, 12, 13),
        end_date=date(2025, 12, 14),
        location="Vacation",
        remote_capable=False
    )

    remote_activity = Activity(
        id="remote_activity",
        name="Remote Activity",
        type=ActivityType.CONSULTATION,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=30,
        location=Location.ONLINE,
        remote_capable=True,
        details="Can do during travel"
    )

    scheduler = GreedyScheduler(
        activities=[remote_activity],
        specialists=[],
        equipment=[],
        travel_periods=[travel_period],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Should schedule all 7 days (including travel)
    count = state.get_occurrence_count("remote_activity")
    assert count == 7, f"Expected 7 occurrences (remote works during travel), got {count}"


def test_time_windows_enforced(start_date, end_date):
    """Test that activities with time windows are scheduled within those windows.

    Create activity with morning time window (06:00-09:00).
    Expected: All slots between 06:00-09:00.
    """
    activity = Activity(
        id="morning_activity",
        name="Morning Activity",
        type=ActivityType.MEDITATION,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=30,
        time_window_start="06:00",
        time_window_end="09:00",
        location=Location.HOME,
        remote_capable=False,
        details="Must be in morning"
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Should schedule all 7 days
    count = state.get_occurrence_count("morning_activity")
    assert count == 7, f"Expected 7 occurrences, got {count}"

    # Verify all slots within time window
    from datetime import datetime
    for slot in state.booked_slots:
        if slot.activity_id == "morning_activity":
            start_time = datetime.strptime(slot.start_time, "%H:%M")
            end_time = start_time + timedelta(minutes=slot.duration_minutes)

            window_start = datetime.strptime("06:00", "%H:%M")
            window_end = datetime.strptime("09:00", "%H:%M")

            assert start_time >= window_start, f"Slot starts before window: {slot.start_time}"
            assert end_time <= window_end, f"Slot ends after window: {slot.start_time} + {slot.duration_minutes}min"


def test_no_overlapping_activities(start_date, end_date):
    """Test that no two activities overlap on the same day.

    Create multiple activities and verify no time overlaps.
    """
    activities = [
        Activity(
            id=f"activity_{i}",
            name=f"Activity {i}",
            type=ActivityType.FITNESS,
            priority=1,
            frequency=Frequency(pattern=FrequencyPattern.WEEKLY, count=2),
            duration_minutes=60,
            location=Location.HOME,
            remote_capable=False,
            details=f"Test activity {i}"
        )
        for i in range(5)
    ]

    scheduler = GreedyScheduler(
        activities=activities,
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    # Group slots by date
    from collections import defaultdict
    slots_by_date = defaultdict(list)
    for slot in state.booked_slots:
        slots_by_date[slot.date].append(slot)

    # Check each date for overlaps
    from datetime import datetime
    for date_key, slots in slots_by_date.items():
        for i, slot1 in enumerate(slots):
            time1_start = datetime.strptime(slot1.start_time, "%H:%M")
            time1_end = time1_start + timedelta(minutes=slot1.duration_minutes)

            for slot2 in slots[i+1:]:
                time2_start = datetime.strptime(slot2.start_time, "%H:%M")
                time2_end = time2_start + timedelta(minutes=slot2.duration_minutes)

                # Check for overlap
                if time1_start < time2_end and time2_start < time1_end:
                    assert False, f"Overlap detected on {date_key}: " \
                                  f"{slot1.activity_id} ({slot1.start_time}) and " \
                                  f"{slot2.activity_id} ({slot2.start_time})"


def test_frequency_daily_scheduling(start_date, end_date):
    """Test that daily activities are scheduled correctly.

    Create daily activity for 7-day period.
    Expected: 7 occurrences.
    """
    activity = Activity(
        id="daily_test",
        name="Daily Activity",
        type=ActivityType.MEDICATION,
        priority=1,
        frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
        duration_minutes=15,
        location=Location.HOME,
        remote_capable=False,
        details="Daily medication"
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    count = state.get_occurrence_count("daily_test")
    assert count == 7, f"Expected 7 daily occurrences, got {count}"


def test_frequency_weekly_scheduling(start_date, end_date):
    """Test that weekly activities are scheduled correctly.

    Create 3x per week activity for 7-day period.
    Expected: 3 occurrences (flexible weeks).
    """
    activity = Activity(
        id="weekly_test",
        name="Weekly Activity",
        type=ActivityType.FITNESS,
        priority=1,
        frequency=Frequency(
            pattern=FrequencyPattern.WEEKLY,
            count=3,
            preferred_days=[0, 2, 4]  # Mon, Wed, Fri
        ),
        duration_minutes=45,
        location=Location.GYM,
        remote_capable=False,
        details="3x per week"
    )

    scheduler = GreedyScheduler(
        activities=[activity],
        specialists=[],
        equipment=[],
        travel_periods=[],
        start_date=start_date,
        end_date=end_date
    )

    state = scheduler.schedule()

    count = state.get_occurrence_count("weekly_test")
    assert count == 3, f"Expected 3 weekly occurrences, got {count}"
