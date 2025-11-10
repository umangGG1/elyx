"""Constraint models: Specialist, Equipment, Travel."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date, time


class SpecialistType(str, Enum):
    """Type of healthcare professional."""
    TRAINER = "Trainer"
    DIETITIAN = "Dietitian"
    THERAPIST = "Therapist"
    PHYSICIAN = "Physician"
    ALLIED_HEALTH = "Allied_Health"


class AvailabilityBlock(BaseModel):
    """A time block when a specialist is available."""
    day_of_week: int = Field(ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    start_time: time = Field(description="Start time")
    end_time: time = Field(description="End time")

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Ensure end_time is after start_time."""
        start = info.data.get('start_time')
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class Specialist(BaseModel):
    """Healthcare professional or trainer with limited availability."""

    id: str = Field(description="Unique identifier")
    name: str = Field(min_length=1, description="Human-readable name")
    type: SpecialistType = Field(description="Type of specialist")
    availability: List[AvailabilityBlock] = Field(
        min_length=1,
        description="Weekly time blocks when available"
    )
    days_off: List[date] = Field(default_factory=list, description="Specific dates unavailable")
    max_concurrent_clients: int = Field(default=1, ge=1, description="Max clients at same time")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "spec_001",
            "name": "Sarah Johnson",
            "type": "Trainer",
            "availability": [
                {"day_of_week": 0, "start_time": "08:00:00", "end_time": "17:00:00"},
                {"day_of_week": 2, "start_time": "08:00:00", "end_time": "17:00:00"},
                {"day_of_week": 4, "start_time": "08:00:00", "end_time": "17:00:00"}
            ],
            "days_off": ["2025-02-14", "2025-03-15"],
            "max_concurrent_clients": 1
        }
    })


class MaintenanceWindow(BaseModel):
    """A time range when equipment is unavailable."""
    start_date: date = Field(description="Start date of maintenance")
    end_date: date = Field(description="End date of maintenance")
    start_time: Optional[time] = Field(default=None, description="Start time (None = all day)")
    end_time: Optional[time] = Field(default=None, description="End time (None = all day)")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is not before start_date."""
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError("end_date cannot be before start_date")
        return v


class Equipment(BaseModel):
    """Physical resource with limited availability."""

    id: str = Field(description="Unique identifier")
    name: str = Field(min_length=1, description="Human-readable name")
    location: str = Field(description="Where equipment is located")
    maintenance_windows: List[MaintenanceWindow] = Field(
        default_factory=list,
        description="Times when equipment is unavailable"
    )
    max_concurrent_users: int = Field(default=1, ge=1, description="Max users at same time")
    requires_specialist: bool = Field(default=False, description="Needs supervision")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "equip_001",
            "name": "Treadmill",
            "location": "Main Gym",
            "maintenance_windows": [
                {
                    "start_date": "2025-02-15",
                    "end_date": "2025-02-15",
                    "start_time": "14:00:00",
                    "end_time": "16:00:00"
                }
            ],
            "max_concurrent_users": 1,
            "requires_specialist": False
        }
    })


class TravelPeriod(BaseModel):
    """Times when client is unavailable or has limited access to resources."""

    id: str = Field(description="Unique identifier")
    start_date: date = Field(description="Start date of travel")
    end_date: date = Field(description="End date of travel")
    location: str = Field(description="Travel destination")
    remote_activities_only: bool = Field(
        default=False,
        description="If true, only remote-capable activities can be scheduled"
    )

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is not before start_date."""
        start = info.data.get('start_date')
        if start and v < start:
            raise ValueError("end_date cannot be before start_date")
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "travel_001",
            "start_date": "2025-02-20",
            "end_date": "2025-02-23",
            "location": "Business trip to Seattle",
            "remote_activities_only": True
        }
    })
