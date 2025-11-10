"""JSON I/O utilities for loading and saving data."""

import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic import ValidationError

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot


def load_json(file_path: str | Path) -> Dict[str, Any] | List[Dict[str, Any]]:
    """
    Load JSON data from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: List[Any] | Dict[str, Any], file_path: str | Path, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save (must be JSON serializable)
        file_path: Path to output file
        indent: JSON indentation level
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Handle Pydantic models
    if isinstance(data, list) and len(data) > 0 and hasattr(data[0], 'model_dump'):
        json_data = [item.model_dump(mode='json') for item in data]
    elif hasattr(data, 'model_dump'):
        json_data = data.model_dump(mode='json')
    else:
        json_data = data

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=indent, default=str)


def load_activities(file_path: str | Path) -> List[Activity]:
    """
    Load activities from JSON file.

    Args:
        file_path: Path to activities JSON file

    Returns:
        List of validated Activity objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If activities fail validation
    """
    data = load_json(file_path)

    if not isinstance(data, list):
        raise ValueError("Activities file must contain a JSON array")

    activities = []
    errors = []

    for i, item in enumerate(data):
        try:
            activity = Activity(**item)
            activities.append(activity)
        except ValidationError as e:
            errors.append(f"Activity {i} ({item.get('id', 'unknown')}): {e}")

    if errors:
        error_msg = "\n".join(errors)
        raise ValidationError(f"Validation errors in activities:\n{error_msg}")

    return activities


def load_specialists(file_path: str | Path) -> List[Specialist]:
    """
    Load specialists from JSON file.

    Args:
        file_path: Path to specialists JSON file

    Returns:
        List of validated Specialist objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If specialists fail validation
    """
    data = load_json(file_path)

    if not isinstance(data, list):
        raise ValueError("Specialists file must contain a JSON array")

    specialists = []
    errors = []

    for i, item in enumerate(data):
        try:
            specialist = Specialist(**item)
            specialists.append(specialist)
        except ValidationError as e:
            errors.append(f"Specialist {i} ({item.get('id', 'unknown')}): {e}")

    if errors:
        error_msg = "\n".join(errors)
        raise ValidationError(f"Validation errors in specialists:\n{error_msg}")

    return specialists


def load_equipment(file_path: str | Path) -> List[Equipment]:
    """
    Load equipment from JSON file.

    Args:
        file_path: Path to equipment JSON file

    Returns:
        List of validated Equipment objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If equipment fail validation
    """
    data = load_json(file_path)

    if not isinstance(data, list):
        raise ValueError("Equipment file must contain a JSON array")

    equipment_list = []
    errors = []

    for i, item in enumerate(data):
        try:
            equipment = Equipment(**item)
            equipment_list.append(equipment)
        except ValidationError as e:
            errors.append(f"Equipment {i} ({item.get('id', 'unknown')}): {e}")

    if errors:
        error_msg = "\n".join(errors)
        raise ValidationError(f"Validation errors in equipment:\n{error_msg}")

    return equipment_list


def load_travel(file_path: str | Path) -> List[TravelPeriod]:
    """
    Load travel periods from JSON file.

    Args:
        file_path: Path to travel JSON file

    Returns:
        List of validated TravelPeriod objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If travel periods fail validation
    """
    data = load_json(file_path)

    if not isinstance(data, list):
        raise ValueError("Travel file must contain a JSON array")

    travel_periods = []
    errors = []

    for i, item in enumerate(data):
        try:
            travel = TravelPeriod(**item)
            travel_periods.append(travel)
        except ValidationError as e:
            errors.append(f"Travel {i} ({item.get('id', 'unknown')}): {e}")

    if errors:
        error_msg = "\n".join(errors)
        raise ValidationError(f"Validation errors in travel periods:\n{error_msg}")

    return travel_periods


def load_timeslots(file_path: str | Path) -> List[TimeSlot]:
    """
    Load time slots from JSON file.

    Args:
        file_path: Path to time slots JSON file

    Returns:
        List of validated TimeSlot objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If time slots fail validation
    """
    data = load_json(file_path)

    if not isinstance(data, list):
        raise ValueError("TimeSlots file must contain a JSON array")

    timeslots = []
    errors = []

    for i, item in enumerate(data):
        try:
            slot = TimeSlot(**item)
            timeslots.append(slot)
        except ValidationError as e:
            errors.append(f"TimeSlot {i}: {e}")

    if errors:
        error_msg = "\n".join(errors)
        raise ValidationError(f"Validation errors in time slots:\n{error_msg}")

    return timeslots
