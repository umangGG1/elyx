"""Schedule models: TimeSlot for scheduled activities."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import date as date_type, time as time_type


class TimeSlot(BaseModel):
    """A specific scheduled instance of an activity."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "activity_id": "act_001",
            "date": "2025-01-15",
            "start_time": "07:00:00",
            "duration_minutes": 5,
            "specialist_id": None,
            "equipment_ids": []
        }
    })

    activity_id: str = Field(description="Reference to the activity being scheduled")
    date: date_type = Field(description="Calendar date")
    start_time: time_type = Field(description="Time of day")
    duration_minutes: int = Field(ge=5, le=480, description="Duration in minutes")
    specialist_id: Optional[str] = Field(default=None, description="Specialist facilitating")
    equipment_ids: List[str] = Field(default_factory=list, description="Equipment being used")
