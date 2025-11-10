"""LLM-powered realistic data generator using Gemini 2.5 Pro."""

import os
import json
import google.generativeai as genai
from typing import List, Tuple, Dict, Any
from datetime import date, timedelta

from models import Activity, Specialist, Equipment, TravelPeriod


class DataGenerator:
    """Generate realistic health program data using Gemini 2.5 Pro."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize the data generator.

        Args:
            api_key: Google AI API key. If None, reads from GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set and no API key provided")

        genai.configure(api_key=self.api_key)
        # Use gemini-2.0-flash-exp for higher output token limits
        self.model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        self.total_cost = 0.0

    def _estimate_cost(self, prompt_tokens: int, response_tokens: int) -> float:
        """
        Estimate API cost based on token counts.
        Gemini 2.0 Flash pricing (as of Jan 2025):
        - Input: $0.075 per 1M tokens
        - Output: $0.30 per 1M tokens

        Args:
            prompt_tokens: Number of input tokens
            response_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (prompt_tokens / 1_000_000) * 0.075
        output_cost = (response_tokens / 1_000_000) * 0.30
        return input_cost + output_cost

    def generate_data(self, prompt: str) -> Tuple[str, float]:
        """
        Generate data using Gemini 2.5 Pro.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Tuple of (response_text, estimated_cost)
        """
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=16000,
            )
        )

        # Estimate cost based on token counts
        prompt_tokens = self.model.count_tokens(prompt).total_tokens
        response_tokens = self.model.count_tokens(response.text).total_tokens
        cost = self._estimate_cost(prompt_tokens, response_tokens)
        self.total_cost += cost

        return response.text, cost

    def generate_activities(self, count: int = 110, start_date: date | None = None, id_offset: int = 0) -> Tuple[List[Activity], float]:
        """
        Generate realistic health activities.

        Args:
            count: Number of activities to generate (aim for 110 to ensure 100+ after validation)
            start_date: Start date for the 90-day scheduling horizon
            id_offset: Starting ID number for activities (e.g., 0 for act_001-030, 30 for act_031-060)

        Returns:
            Tuple of (list of validated Activity objects, cost)
        """
        if start_date is None:
            start_date = date.today()

        prompt = f"""Generate {count} realistic health program activities for a 90-day wellness program starting {start_date}.

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON array, no markdown, no explanations
- Each activity must have ALL required fields
- Use these exact type names: "Fitness", "Food", "Medication", "Therapy", "Consultation"
- Use these exact pattern names: "Daily", "Weekly", "Monthly", "Custom"
- Use these exact location names: "Home", "Gym", "Clinic", "Any"

DISTRIBUTION (for {count} activities):
- 6 Medication activities (critical medications only, priority 1)
- 10 Fitness activities (mix of Weekly patterns)
- 8 Food/Nutrition activities (mix of Daily and Weekly)
- 4 Therapy activities (Weekly or Monthly)
- 2 Consultation activities (Monthly)

CRITICAL SCHEDULING REQUIREMENTS (MUST FOLLOW EXACTLY):
1. ONLY 2-3 activities should be Daily frequency (absolute maximum)
2. Weekly frequency: Use 1-3x per week for MOST activities (NOT 5-7x)
3. High frequency (5-7x/week): Maximum 3 activities total
4. Time windows:
   - Daily activities: NO time windows (use null for both start and end)
   - Weekly 5-7x: NO time windows or very wide (10+ hours)
   - Weekly 3-4x: Wide windows (6+ hours) or null
   - Weekly 1-2x: Can have specific windows (2-4 hours)
   - Monthly: Can have specific windows
5. NO MORE than 2 activities should share the same time window

ACTIVITY REQUIREMENTS:
1. Priority: 1 (critical medications) to 5 (optional wellness)
   - Priority 1: ONLY 2-3 Daily critical medications
   - Priority 2-3: Weekly activities
   - Priority 4-5: Monthly or low-frequency weekly

2. Frequency patterns (STRICT LIMITS):
   - Daily: Maximum 2-3 activities total (critical meds only)
   - Weekly 7x: Maximum 1 activity
   - Weekly 5-6x: Maximum 2 activities
   - Weekly 3-4x: Maximum 8 activities
   - Weekly 1-2x: Majority of activities (15-20 per batch)
   - Monthly: 2-3 activities

3. Duration (minutes):
   - Medications: 5-15 minutes
   - Fitness: 30-90 minutes
   - Food preparation: 20-60 minutes
   - Therapy sessions: 30-120 minutes
   - Consultations: 30-90 minutes

4. Time windows (CRITICAL - maximize schedulability):
   - Daily activities: ALWAYS null (no time windows)
   - Weekly 5-7x: ALWAYS null or 10+ hour windows
   - Weekly 3-4x: null or 6+ hour windows
   - Weekly 1-2x: Can use 2-4 hour windows
   - Monthly: Can use specific 2-3 hour windows
   - Spread windows across day: 30% morning (06:00-12:00), 30% afternoon (12:00-17:00), 30% evening (17:00-21:00), 10% anytime (null)

5. Include variety:
   - Different specialist requirements (use IDs: spec_001 to spec_015)
   - Different equipment needs (use IDs: equip_001 to equip_010)
   - Mix of locations (Home, Gym, Clinic)
   - Some remote-capable activities
   - Realistic preparation requirements
   - Relevant metrics to collect

JSON SCHEMA:
[
  {{
    "id": "act_001",
    "name": "Morning Blood Pressure Medication",
    "type": "Medication",
    "priority": 1,
    "frequency": {{
      "pattern": "Daily",
      "count": 1
    }},
    "duration_minutes": 5,
    "time_window_start": "06:00:00",
    "time_window_end": "08:00:00",
    "details": "Take with water before breakfast",
    "specialist_id": null,
    "equipment_ids": ["equip_009"],
    "location": "Home",
    "remote_capable": false,
    "preparation_requirements": [],
    "backup_activity_ids": [],
    "metrics_to_collect": ["Blood pressure", "Adherence"]
  }}
]

VALIDATION RULES (CRITICAL):
- NO activities >480 minutes (8 hours)
- Weekly frequency count ≤7
- Monthly frequency count ≤31
- Time windows: end must be after start
- All times in 24-hour format HH:MM:SS
- specialist_id and equipment_ids can be null/empty or reference spec_XXX/equip_XXX
- Use null not "null" for null values

Generate {count} diverse, realistic activities now:"""

        response_text, cost = self.generate_data(prompt)

        # Parse and validate
        try:
            # Clean response (remove markdown if present)
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                # Remove markdown code blocks
                lines = clean_text.split("\n")
                clean_text = "\n".join([l for l in lines if not l.startswith("```")])
                clean_text = clean_text.replace("json", "").strip()

            # Try to extract JSON array if response is incomplete
            if not clean_text.endswith("]"):
                # Find the last complete JSON object
                last_brace = clean_text.rfind("}")
                if last_brace > 0:
                    clean_text = clean_text[:last_brace + 1] + "\n]"

            data = json.loads(clean_text)
            if not isinstance(data, list):
                raise ValueError("Response is not a JSON array")

            activities = []
            errors = []

            for i, item in enumerate(data):
                try:
                    # Renumber ID based on offset
                    item['id'] = f"act_{id_offset + i + 1:03d}"
                    activity = Activity(**item)
                    activities.append(activity)
                except Exception as e:
                    errors.append(f"Activity {i} ({item.get('id', 'unknown')}): {e}")

            validation_rate = len(activities) / len(data) * 100 if data else 0
            print(f"✓ Generated {len(activities)}/{len(data)} valid activities ({validation_rate:.1f}% pass rate)")
            print(f"   IDs: act_{id_offset + 1:03d} to act_{id_offset + len(activities):03d}")

            if errors:
                print(f"⚠ {len(errors)} activities failed validation:")
                for err in errors[:5]:  # Show first 5 errors
                    print(f"  - {err}")

            return activities, cost

        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing failed: {e}")
            print(f"Response preview: {response_text[:500]}")
            raise

    def generate_specialists(self, count: int = 15) -> Tuple[List[Specialist], float]:
        """
        Generate realistic specialist availability data.

        Args:
            count: Number of specialists to generate

        Returns:
            Tuple of (list of validated Specialist objects, cost)
        """
        prompt = f"""Generate {count} realistic healthcare specialists with 3-month availability schedules.

OUTPUT: Return ONLY valid JSON array, no markdown.

DISTRIBUTION:
- 5 Fitness Trainers
- 3 Dietitians
- 2 Therapists
- 3 Physicians
- 2 Allied Health professionals

REQUIREMENTS:
1. Each specialist works 30-50 hours per week
2. Availability: 2-4 time blocks per working day
3. Working days: 3-6 days per week (0=Monday, 6=Sunday)
4. Hours: realistic for profession
   - Trainers: 6 AM - 9 PM (flexible hours)
   - Dietitians: 8 AM - 5 PM (business hours)
   - Therapists: 9 AM - 8 PM (flexible)
   - Physicians: 8 AM - 6 PM (limited hours)
   - Allied Health: 7 AM - 6 PM (varied)
5. Days off: 3-6 specific dates over 90 days (holidays, vacation)
6. Use these exact type names: "Trainer", "Dietitian", "Therapist", "Physician", "Allied_Health"

JSON SCHEMA:
[
  {{
    "id": "spec_001",
    "name": "Sarah Mitchell",
    "type": "Trainer",
    "availability": [
      {{"day_of_week": 0, "start_time": "06:00:00", "end_time": "13:00:00"}},
      {{"day_of_week": 0, "start_time": "17:00:00", "end_time": "20:00:00"}},
      {{"day_of_week": 2, "start_time": "06:00:00", "end_time": "13:00:00"}},
      {{"day_of_week": 4, "start_time": "06:00:00", "end_time": "20:00:00"}}
    ],
    "days_off": ["2025-02-14", "2025-03-17", "2025-04-01"],
    "max_concurrent_clients": 1
  }}
]

VALIDATION RULES:
- day_of_week: 0-6 (Monday-Sunday)
- All times: 24-hour format HH:MM:SS
- end_time must be after start_time
- Dates: YYYY-MM-DD format
- Use realistic names

Generate {count} specialists now:"""

        response_text, cost = self.generate_data(prompt)

        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                clean_text = "\n".join([l for l in lines if not l.startswith("```")])
                clean_text = clean_text.replace("json", "").strip()

            data = json.loads(clean_text)
            specialists = []
            errors = []

            for i, item in enumerate(data):
                try:
                    specialist = Specialist(**item)
                    specialists.append(specialist)
                except Exception as e:
                    errors.append(f"Specialist {i}: {e}")

            validation_rate = len(specialists) / len(data) * 100 if data else 0
            print(f"✓ Generated {len(specialists)}/{len(data)} valid specialists ({validation_rate:.1f}% pass rate)")

            if errors:
                print(f"⚠ {len(errors)} specialists failed validation")

            return specialists, cost

        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing failed: {e}")
            raise

    def generate_equipment(self, count: int = 10, start_date: date | None = None) -> Tuple[List[Equipment], float]:
        """
        Generate realistic equipment availability data.

        Args:
            count: Number of equipment items to generate
            start_date: Start date for maintenance windows

        Returns:
            Tuple of (list of validated Equipment objects, cost)
        """
        if start_date is None:
            start_date = date.today()

        end_date = start_date + timedelta(days=90)

        prompt = f"""Generate {count} realistic health/fitness equipment items with maintenance schedules.

EQUIPMENT TYPES:
- 4 Gym equipment (treadmill, elliptical, weights, rowing machine)
- 2 Therapy equipment (sauna, ice bath)
- 2 Medical equipment (blood pressure monitor, body composition analyzer)
- 2 Specialized equipment (yoga mats, resistance bands)

REQUIREMENTS:
1. Each item: 1-2 maintenance windows over 90 days ({start_date} to {end_date})
2. Maintenance: 2-4 hours duration
3. Location: specific and realistic
4. max_concurrent_users: usually 1, can be 2-4 for group equipment
5. requires_specialist: true for medical/therapy equipment

JSON SCHEMA:
[
  {{
    "id": "equip_001",
    "name": "Commercial Treadmill",
    "location": "Main Gym",
    "maintenance_windows": [
      {{
        "start_date": "2025-02-15",
        "end_date": "2025-02-15",
        "start_time": "14:00:00",
        "end_time": "16:00:00"
      }}
    ],
    "max_concurrent_users": 1,
    "requires_specialist": false
  }}
]

VALIDATION RULES:
- Dates: YYYY-MM-DD format, within {start_date} to {end_date}
- Times: HH:MM:SS format (or null for all-day maintenance)
- end_date >= start_date
- Use realistic equipment names and locations

OUTPUT: Return ONLY valid JSON array, no markdown.

Generate {count} equipment items now:"""

        response_text, cost = self.generate_data(prompt)

        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                clean_text = "\n".join([l for l in lines if not l.startswith("```")])
                clean_text = clean_text.replace("json", "").strip()

            data = json.loads(clean_text)
            equipment_list = []
            errors = []

            for i, item in enumerate(data):
                try:
                    equipment = Equipment(**item)
                    equipment_list.append(equipment)
                except Exception as e:
                    errors.append(f"Equipment {i}: {e}")

            validation_rate = len(equipment_list) / len(data) * 100 if data else 0
            print(f"✓ Generated {len(equipment_list)}/{len(data)} valid equipment ({validation_rate:.1f}% pass rate)")

            if errors:
                print(f"⚠ {len(errors)} equipment failed validation")

            return equipment_list, cost

        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing failed: {e}")
            raise

    def generate_travel_periods(self, count: int = 6, start_date: date | None = None) -> Tuple[List[TravelPeriod], float]:
        """
        Generate realistic travel periods.

        Args:
            count: Number of travel periods to generate
            start_date: Start date for the 90-day horizon

        Returns:
            Tuple of (list of validated TravelPeriod objects, cost)
        """
        if start_date is None:
            start_date = date.today()

        end_date = start_date + timedelta(days=90)

        prompt = f"""Generate {count} realistic travel periods over 90 days ({start_date} to {end_date}).

REQUIREMENTS:
1. Mix of trip lengths:
   - 3-4 weekend trips (2-3 days)
   - 1-2 longer vacations (5-7 days)
   - 1 business trip (3-4 days)
2. Spread across the 90-day period (not clustered)
3. Some allow remote activities (business trips with good wifi)
4. Some require in-person only (remote locations, international travel)

JSON SCHEMA:
[
  {{
    "id": "travel_001",
    "start_date": "2025-02-20",
    "end_date": "2025-02-23",
    "location": "Seattle, WA - Business Conference",
    "remote_activities_only": true
  }},
  {{
    "id": "travel_002",
    "start_date": "2025-03-10",
    "end_date": "2025-03-16",
    "location": "Bali, Indonesia - Vacation",
    "remote_activities_only": false
  }}
]

VALIDATION RULES:
- Dates: YYYY-MM-DD format, within {start_date} to {end_date}
- end_date >= start_date
- No overlapping travel periods
- Realistic destinations and purposes

OUTPUT: Return ONLY valid JSON array, no markdown.

Generate {count} travel periods now:"""

        response_text, cost = self.generate_data(prompt)

        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                clean_text = "\n".join([l for l in lines if not l.startswith("```")])
                clean_text = clean_text.replace("json", "").strip()

            data = json.loads(clean_text)
            travel_periods = []
            errors = []

            for i, item in enumerate(data):
                try:
                    travel = TravelPeriod(**item)
                    travel_periods.append(travel)
                except Exception as e:
                    errors.append(f"Travel {i}: {e}")

            validation_rate = len(travel_periods) / len(data) * 100 if data else 0
            print(f"✓ Generated {len(travel_periods)}/{len(data)} valid travel periods ({validation_rate:.1f}% pass rate)")

            if errors:
                print(f"⚠ {len(errors)} travel periods failed validation")

            return travel_periods, cost

        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing failed: {e}")
            raise


def generate_all_data(
    api_key: str | None = None,
    activity_count: int = 110,
    specialist_count: int = 15,
    equipment_count: int = 10,
    travel_count: int = 6,
    start_date: date | None = None
) -> Tuple[Dict[str, List[Any]], float]:
    """
    Generate all data needed for scheduling.

    Args:
        api_key: Google AI API key
        activity_count: Number of activities to generate
        specialist_count: Number of specialists to generate
        equipment_count: Number of equipment items to generate
        travel_count: Number of travel periods to generate
        start_date: Start date for the 90-day scheduling horizon

    Returns:
        Tuple of (dict with all data, total cost)
    """
    generator = DataGenerator(api_key)

    print("🤖 Generating health program data with Gemini 2.0 Flash...\n")

    # Generate all data
    print("1️⃣  Generating activities...")
    activities, cost1 = generator.generate_activities(activity_count, start_date)

    print("\n2️⃣  Generating specialists...")
    specialists, cost2 = generator.generate_specialists(specialist_count)

    print("\n3️⃣  Generating equipment...")
    equipment, cost3 = generator.generate_equipment(equipment_count, start_date)

    print("\n4️⃣  Generating travel periods...")
    travel, cost4 = generator.generate_travel_periods(travel_count, start_date)

    total_cost = generator.total_cost

    print(f"\n✅ Data generation complete!")
    print(f"   - Activities: {len(activities)}")
    print(f"   - Specialists: {len(specialists)}")
    print(f"   - Equipment: {len(equipment)}")
    print(f"   - Travel: {len(travel)}")
    print(f"   - Total API cost: ${total_cost:.4f}")

    return {
        "activities": activities,
        "specialists": specialists,
        "equipment": equipment,
        "travel": travel
    }, total_cost
