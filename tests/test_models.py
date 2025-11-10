"""Tests for Pydantic models validation."""

import pytest
from datetime import time, date
from pydantic import ValidationError

from models import (
    Activity, Frequency, FrequencyPattern, ActivityType, Location,
    Specialist, SpecialistType, Equipment, TravelPeriod, TimeSlot,
    AvailabilityBlock, MaintenanceWindow
)


class TestFrequency:
    """Tests for Frequency model."""

    def test_valid_daily_frequency(self):
        """Test valid daily frequency."""
        freq = Frequency(pattern=FrequencyPattern.DAILY, count=1)
        assert freq.pattern == FrequencyPattern.DAILY
        assert freq.count == 1

    def test_valid_weekly_frequency(self):
        """Test valid weekly frequency."""
        freq = Frequency(
            pattern=FrequencyPattern.WEEKLY,
            count=3,
            preferred_days=[0, 2, 4]  # Mon, Wed, Fri
        )
        assert freq.pattern == FrequencyPattern.WEEKLY
        assert freq.count == 3
        assert freq.preferred_days == [0, 2, 4]

    def test_weekly_count_exceeds_7(self):
        """Test weekly frequency with count > 7 fails."""
        with pytest.raises(ValidationError, match="cannot exceed 7"):
            Frequency(pattern=FrequencyPattern.WEEKLY, count=10)

    def test_monthly_count_exceeds_31(self):
        """Test monthly frequency with count > 31 fails."""
        with pytest.raises(ValidationError, match="cannot exceed 31"):
            Frequency(pattern=FrequencyPattern.MONTHLY, count=50)

    def test_daily_with_preferred_days_fails(self):
        """Test daily pattern cannot have preferred_days."""
        with pytest.raises(ValidationError, match="cannot have preferred_days"):
            Frequency(
                pattern=FrequencyPattern.DAILY,
                count=1,
                preferred_days=[0, 2]
            )

    def test_custom_requires_interval(self):
        """Test custom pattern requires interval_days."""
        with pytest.raises(ValidationError, match="requires interval_days"):
            Frequency(pattern=FrequencyPattern.CUSTOM, count=1)

    def test_valid_custom_frequency(self):
        """Test valid custom frequency."""
        freq = Frequency(
            pattern=FrequencyPattern.CUSTOM,
            count=1,
            interval_days=3
        )
        assert freq.interval_days == 3


class TestActivity:
    """Tests for Activity model."""

    def test_valid_activity(self):
        """Test valid activity creation."""
        activity = Activity(
            id="act_001",
            name="Morning Medication",
            type=ActivityType.MEDICATION,
            priority=1,
            frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
            duration_minutes=5,
            time_window_start=time(6, 0),
            time_window_end=time(8, 0)
        )
        assert activity.id == "act_001"
        assert activity.priority == 1

    def test_priority_out_of_range(self):
        """Test priority must be 1-5."""
        with pytest.raises(ValidationError):
            Activity(
                id="act_001",
                name="Test",
                type=ActivityType.FITNESS,
                priority=6,  # Invalid
                frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
                duration_minutes=30
            )

    def test_duration_too_short(self):
        """Test duration must be >= 5 minutes."""
        with pytest.raises(ValidationError):
            Activity(
                id="act_001",
                name="Test",
                type=ActivityType.FITNESS,
                priority=3,
                frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
                duration_minutes=2  # Invalid
            )

    def test_duration_too_long(self):
        """Test duration must be <= 480 minutes (8 hours)."""
        with pytest.raises(ValidationError):
            Activity(
                id="act_001",
                name="Test",
                type=ActivityType.FITNESS,
                priority=3,
                frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
                duration_minutes=600  # Invalid (10 hours)
            )

    def test_time_window_end_before_start(self):
        """Test time window end must be after start."""
        with pytest.raises(ValidationError, match="must be after"):
            Activity(
                id="act_001",
                name="Test",
                type=ActivityType.MEDICATION,
                priority=1,
                frequency=Frequency(pattern=FrequencyPattern.DAILY, count=1),
                duration_minutes=5,
                time_window_start=time(8, 0),
                time_window_end=time(6, 0)  # Before start
            )


class TestSpecialist:
    """Tests for Specialist model."""

    def test_valid_specialist(self):
        """Test valid specialist creation."""
        specialist = Specialist(
            id="spec_001",
            name="Dr. Smith",
            type=SpecialistType.PHYSICIAN,
            availability=[
                AvailabilityBlock(day_of_week=0, start_time=time(9, 0), end_time=time(17, 0)),
                AvailabilityBlock(day_of_week=2, start_time=time(9, 0), end_time=time(17, 0))
            ]
        )
        assert specialist.name == "Dr. Smith"
        assert len(specialist.availability) == 2

    def test_specialist_must_have_availability(self):
        """Test specialist must have at least one availability block."""
        with pytest.raises(ValidationError):
            Specialist(
                id="spec_001",
                name="Dr. Smith",
                type=SpecialistType.PHYSICIAN,
                availability=[]  # Invalid - must have at least 1
            )

    def test_availability_block_invalid_time(self):
        """Test availability block end time must be after start."""
        with pytest.raises(ValidationError, match="must be after"):
            AvailabilityBlock(
                day_of_week=0,
                start_time=time(17, 0),
                end_time=time(9, 0)  # Before start
            )


class TestEquipment:
    """Tests for Equipment model."""

    def test_valid_equipment(self):
        """Test valid equipment creation."""
        equipment = Equipment(
            id="equip_001",
            name="Treadmill",
            location="Main Gym",
            max_concurrent_users=1
        )
        assert equipment.name == "Treadmill"

    def test_equipment_with_maintenance(self):
        """Test equipment with maintenance window."""
        equipment = Equipment(
            id="equip_001",
            name="Treadmill",
            location="Main Gym",
            maintenance_windows=[
                MaintenanceWindow(
                    start_date=date(2025, 2, 15),
                    end_date=date(2025, 2, 15),
                    start_time=time(14, 0),
                    end_time=time(16, 0)
                )
            ]
        )
        assert len(equipment.maintenance_windows) == 1


class TestTravelPeriod:
    """Tests for TravelPeriod model."""

    def test_valid_travel_period(self):
        """Test valid travel period creation."""
        travel = TravelPeriod(
            id="travel_001",
            start_date=date(2025, 2, 20),
            end_date=date(2025, 2, 23),
            location="Seattle",
            remote_activities_only=True
        )
        assert travel.location == "Seattle"

    def test_travel_end_before_start(self):
        """Test travel end date cannot be before start."""
        with pytest.raises(ValidationError, match="cannot be before"):
            TravelPeriod(
                id="travel_001",
                start_date=date(2025, 2, 20),
                end_date=date(2025, 2, 10),  # Before start
                location="Seattle"
            )


class TestTimeSlot:
    """Tests for TimeSlot model."""

    def test_valid_timeslot(self):
        """Test valid time slot creation."""
        slot = TimeSlot(
            activity_id="act_001",
            date=date(2025, 1, 15),
            start_time=time(7, 0),
            duration_minutes=30
        )
        assert slot.activity_id == "act_001"
        assert slot.duration_minutes == 30

    def test_timeslot_duration_validation(self):
        """Test time slot duration must be 5-480."""
        with pytest.raises(ValidationError):
            TimeSlot(
                activity_id="act_001",
                date=date(2025, 1, 15),
                start_time=time(7, 0),
                duration_minutes=500  # Invalid
            )
