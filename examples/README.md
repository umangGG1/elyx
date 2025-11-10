# Examples

This directory contains simple examples demonstrating how to use the health activity scheduler with minimal datasets.

## Quick Start Example

The `simple_schedule.py` script demonstrates basic scheduler usage with a small dataset:
- 5 activities (daily exercise, weekly checkup, etc.)
- 2 specialists (trainer, nutritionist)
- 1 piece of equipment (gym equipment)
- 7-day scheduling period

### Running the Example

```bash
# From the project root
cd examples
python3 simple_schedule.py
```

### Expected Output

The script will:
1. Load the sample data from `sample_data/`
2. Run the greedy scheduler
3. Print a daily calendar view
4. Display success metrics
5. Show any failed activities

### Sample Data Files

- `sample_data/activities.json` - 5 example health activities
- `sample_data/specialists.json` - 2 example specialists with availability
- `sample_data/equipment.json` - 1 example equipment item
- `sample_data/travel.json` - 1 example travel period

## Use Cases

### 1. Understanding Basic Scheduling

Run `simple_schedule.py` to see how the scheduler:
- Prioritizes activities by priority level (P1-P5)
- Respects specialist availability windows
- Avoids equipment conflicts
- Handles travel periods for remote vs. non-remote activities

### 2. Testing Custom Activities

Modify `sample_data/activities.json` to test different scenarios:
- Change priorities to see scheduling order changes
- Adjust time windows to create conflicts
- Modify frequencies (daily vs. weekly)
- Add equipment requirements

### 3. Learning the API

Use `simple_schedule.py` as a template for your own scheduling scripts:

```python
from scheduler.greedy import GreedyScheduler
from utils.io import load_json

# Load data
activities = load_json("data/activities.json")
specialists = load_json("data/specialists.json")
equipment = load_json("data/equipment.json")
travel = load_json("data/travel.json")

# Create scheduler
scheduler = GreedyScheduler(
    activities=activities,
    specialists=specialists,
    equipment=equipment,
    travel_periods=travel,
    start_date=start,
    end_date=end
)

# Run scheduling
schedule = scheduler.schedule()

# Access results
print(f"Scheduled: {len(schedule.scheduled)} slots")
print(f"Failed: {len(schedule.failed)} activities")
```

## Modifying Examples

### Adding New Activities

Edit `sample_data/activities.json`:

```json
{
  "id": "act_example_001",
  "name": "Morning Yoga",
  "type": "Exercise",
  "priority": 2,
  "duration_minutes": 45,
  "frequency": {
    "pattern": "daily",
    "count": 1
  },
  "time_window": {
    "start_time": "06:00",
    "end_time": "08:00"
  },
  "requires_specialist": null,
  "requires_equipment": null,
  "can_be_remote": true,
  "location": "home"
}
```

### Changing Specialist Availability

Edit `sample_data/specialists.json`:

```json
{
  "id": "spec_example_001",
  "name": "John Smith",
  "type": "trainer",
  "availability_blocks": [
    {
      "day": 0,
      "start_time": "09:00",
      "end_time": "17:00"
    }
  ],
  "days_off": [6],
  "holidays": []
}
```

## Next Steps

After running the example:

1. **Generate Full Dataset**: Use `generate_data.py` to create a realistic 100+ activity dataset
2. **Run Full Scheduler**: Use `run_scheduler.py` for the complete 90-day scheduling workflow
3. **Launch Web UI**: Use `web_app.py` to visualize schedules in the browser
4. **Write Tests**: See `tests/` directory for comprehensive test examples

## Troubleshooting

### Import Errors

Make sure you're running from the project root or have the module path set:

```bash
# Option 1: Run from project root
cd /path/to/elyx
python3 examples/simple_schedule.py

# Option 2: Set PYTHONPATH
export PYTHONPATH=/path/to/elyx
python3 examples/simple_schedule.py
```

### Validation Errors

If you get Pydantic validation errors, check:
- Time formats are "HH:MM" (e.g., "09:00")
- Dates are "YYYY-MM-DD" (e.g., "2025-12-09")
- Priority is 1-5
- Duration is positive integer
- Frequency pattern is "daily", "weekly", or "monthly"

### No Activities Scheduled

Common causes:
- Time windows too restrictive
- Specialist/equipment unavailable during required times
- Travel periods blocking non-remote activities
- Conflicting requirements (multiple specialists/equipment)
