"""Activity and Frequency models for health scheduling."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import time


class ActivityType(str, Enum):
    """Type of health activity."""
    FITNESS = "Fitness"
    FOOD = "Food"
    MEDICATION = "Medication"
    THERAPY = "Therapy"
    CONSULTATION = "Consultation"


class Location(str, Enum):
    """Where an activity can be performed."""
    HOME = "Home"
    GYM = "Gym"
    CLINIC = "Clinic"
    ANY = "Any"


class FrequencyPattern(str, Enum):
    """How often an activity occurs."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    CUSTOM = "Custom"


class Frequency(BaseModel):
    """Defines how often an activity should occur."""

    pattern: FrequencyPattern = Field(description="Frequency pattern (Daily, Weekly, Monthly, Custom)")
    count: int = Field(default=1, ge=1, description="Number of times per period (e.g., 3 for '3x per week')")
    preferred_days: Optional[List[int]] = Field(
        default=None,
        description="Preferred days of week (0=Monday, 6=Sunday) for weekly patterns"
    )
    interval_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Interval in days for custom patterns (e.g., 3 for 'every 3 days')"
    )

    @field_validator('count')
    @classmethod
    def validate_count(cls, v, info):
        """Validate count based on pattern."""
        pattern = info.data.get('pattern')
        if pattern == FrequencyPattern.WEEKLY and v > 7:
            raise ValueError("Weekly frequency count cannot exceed 7")
        if pattern == FrequencyPattern.MONTHLY and v > 31:
            raise ValueError("Monthly frequency count cannot exceed 31")
        return v

    @model_validator(mode='after')
    def validate_frequency(self):
        """Validate frequency combinations."""
        if self.pattern == FrequencyPattern.DAILY and self.preferred_days is not None:
            raise ValueError("Daily pattern cannot have preferred_days")

        if self.pattern == FrequencyPattern.CUSTOM and self.interval_days is None:
            raise ValueError("Custom pattern requires interval_days")

        if self.pattern != FrequencyPattern.CUSTOM and self.interval_days is not None:
            raise ValueError("interval_days only valid for Custom pattern")

        if self.preferred_days is not None:
            for day in self.preferred_days:
                if day < 0 or day > 6:
                    raise ValueError("preferred_days must be 0-6 (Monday-Sunday)")

        return self


class Activity(BaseModel):
    """Represents a single health-related task that needs to be scheduled."""

    id: str = Field(description="Unique identifier")
    name: str = Field(min_length=1, description="Human-readable name")
    type: ActivityType = Field(description="Type of activity")
    priority: int = Field(ge=1, le=5, description="Priority 1 (critical) to 5 (optional)")
    frequency: Frequency = Field(description="How often this activity occurs")
    duration_minutes: int = Field(ge=5, le=480, description="Duration in minutes (5-480)")
    time_window_start: Optional[time] = Field(
        default=None,
        description="Start of preferred time window (e.g., 06:00 for morning meds)"
    )
    time_window_end: Optional[time] = Field(
        default=None,
        description="End of preferred time window (e.g., 08:00 for morning meds)"
    )
    details: str = Field(default="", description="Additional details about the activity")

    # Constraint references
    specialist_id: Optional[str] = Field(default=None, description="Required specialist ID")
    equipment_ids: List[str] = Field(default_factory=list, description="Required equipment IDs")
    location: Location = Field(default=Location.ANY, description="Where activity is performed")
    remote_capable: bool = Field(default=False, description="Can be done remotely via video call")

    # Metadata
    preparation_requirements: List[str] = Field(
        default_factory=list,
        description="Preparation tasks needed"
    )
    backup_activity_ids: List[str] = Field(
        default_factory=list,
        description="Alternative activities if this can't be scheduled"
    )
    metrics_to_collect: List[str] = Field(
        default_factory=list,
        description="Measurements to track"
    )

    @model_validator(mode='after')
    def validate_time_window(self):
        """Validate time window."""
        if self.time_window_start and self.time_window_end:
            if self.time_window_end <= self.time_window_start:
                raise ValueError("time_window_end must be after time_window_start")
        elif (self.time_window_start is None) != (self.time_window_end is None):
            raise ValueError("Both time_window_start and time_window_end must be provided together")

        return self

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "act_001",
            "name": "Morning Blood Pressure Medication",
            "type": "Medication",
            "priority": 1,
            "frequency": {
                "pattern": "Daily",
                "count": 1
            },
            "duration_minutes": 5,
            "time_window_start": "06:00:00",
            "time_window_end": "08:00:00",
            "details": "Take with water, before breakfast",
            "location": "Home",
            "remote_capable": False,
            "metrics_to_collect": ["Blood pressure", "Adherence"]
        }
    })
