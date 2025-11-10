# Health Activity Scheduler - Design Document
**Date:** 2025-01-08
**Project:** Elyx Resource Allocator Assignment
**Approach:** LLM-Augmented Greedy Scheduling
**Timeline:** 3 Days
**LLM Model:** Gemini 2.5 Pro

---

## Executive Summary

This document outlines the design for a health activity scheduling system that transforms AI-generated health recommendations into practical daily schedules. The system prioritizes simplicity and strategic LLM integration over algorithmic complexity, targeting 85-90% successful activity placement within real-world constraints.

### Core Architecture Decision

**Greedy scheduler with priority-based heuristics + Strategic LLM augmentation**

**Rationale:**
- **Greedy Algorithm:** Sufficient for 85-90% success rate, implementable in 1 day vs 3-5 days for constraint programming solvers
- **LLM Integration at High-Value Touchpoints:** Data generation (saves 6+ hours manual work), natural language summaries (superior user experience)
- **Deterministic Core:** Ensures zero hallucinations in critical scheduling decisions, complete constraint satisfaction

### Success Criteria

| Metric | Target | Rationale |
|--------|--------|-----------|
| Activity Success Rate | 85-90% | Realistic for greedy approach, acceptable for health scheduling |
| Priority 1 Success Rate | 95%+ | Critical medications/treatments must be scheduled |
| Runtime Performance | <10 seconds | Immediate feedback for 100 activities across 90 days |
| Constraint Violations | 0 | Hard constraints must never be violated |
| LLM API Cost | <$2 total | Cost-effective use of LLM capabilities |
| Documentation Quality | Production-ready | Clear setup, architecture explanation, prompt documentation |

---

## Problem Analysis

### Assignment Requirements

**Core Deliverables:**
1. Realistic sample data: 100+ activities in JSON/CSV format
2. Availability data: 3-month schedules for specialists, equipment, allied health professionals
3. Scheduler: Transform action plans + constraints into personalized schedules
4. Calendar output: Readable format (daily/weekly/monthly views)
5. Prompt documentation: All GenAI usage must be documented

**Activity Structure:**
- Type: Fitness, Food, Medication, Therapy, Consultation
- Frequency: Daily, weekly, monthly, or custom patterns
- Priority: 1 (critical) to 5 (optional), based on health impact
- Constraints: Time windows, specialist requirements, equipment needs, location constraints
- Metadata: Backup activities, preparation requirements, remote capability, metrics to collect

**Constraint Categories:**
- **Travel Plans:** Member unavailability during scheduled trips
- **Equipment:** Availability windows, maintenance schedules, concurrent usage limits
- **Specialists:** Working hours, days off, holidays, patient capacity
- **Allied Health:** Similar to specialists but may have different availability patterns

### Key Challenges

1. **Combinatorial Explosion:** 100 activities × 90 days × 24 hours = 216,000 potential slot combinations
2. **Multi-Constraint Satisfaction:** Each activity must satisfy 5-8 different constraint types simultaneously
3. **Priority Balancing:** High-priority activities must be scheduled even if it means rejecting lower-priority ones
4. **Realistic Data Generation:** Manual creation of 100+ activities would take 6-8 hours; must be automated
5. **Frequency Complexity:** "3x per week" requires weekly distribution logic, not just slot finding
6. **User Experience:** Raw schedule data is meaningless without context and explanation

---

## System Architecture

### High-Level Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                               │
│  ┌────────────────┐         ┌─────────────────┐            │
│  │ LLM Generator  │────────▶│  Pydantic       │            │
│  │ (Gemini 2.5)   │         │  Validation     │            │
│  └────────────────┘         └─────────────────┘            │
│         │                            │                      │
│         ▼                            ▼                      │
│  ┌──────────────────────────────────────────┐              │
│  │  Validated Activity & Constraint Data    │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 SCHEDULING ENGINE                            │
│  ┌────────────────────────────────────────────┐            │
│  │  1. Sort by Priority & Frequency           │            │
│  └────────────────────────────────────────────┘            │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────┐            │
│  │  2. Greedy Slot Finding                    │            │
│  │     - Iterate through calendar             │            │
│  │     - Score each potential slot (0-10)     │            │
│  └────────────────────────────────────────────┘            │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────┐            │
│  │  3. Constraint Validation                  │            │
│  │     - Hard: specialist, equipment, travel  │            │
│  │     - Soft: preferences, grouping          │            │
│  └────────────────────────────────────────────┘            │
│                        │                                     │
│                        ▼                                     │
│  ┌────────────────────────────────────────────┐            │
│  │  4. Booking & Conflict Tracking            │            │
│  └────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT LAYER                               │
│  ┌────────────────┐         ┌─────────────────┐            │
│  │ Calendar       │         │  LLM Summary    │            │
│  │ Formatter      │◀────────│  Generator      │            │
│  │ (Text/JSON)    │         │  (Gemini 2.5)   │            │
│  └────────────────┘         └─────────────────┘            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────┐              │
│  │  Personalized Schedule with Context      │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Input Processing

#### Deterministic Path
- Load activity and constraint data from JSON files
- Parse into strongly-typed Pydantic models
- Run validation rules to catch data quality issues
- Reject invalid entries before scheduling begins

#### LLM-Augmented Path (Primary for this project)
- **Single comprehensive prompt** generates entire dataset:
  - 100+ activities with realistic health program distribution
  - 10-15 specialists with 3-month availability calendars
  - 8-10 equipment items with maintenance windows
  - 5-7 travel periods representing realistic client commitments
- **Validation pipeline** catches LLM hallucinations:
  - Type checking via Pydantic
  - Sanity checks (no 24-hour activities, no 20x daily frequencies)
  - Referential integrity (activities reference valid specialists/equipment)
- **Manual spot-check** of 10-15 generated activities ensures quality
- **Cost optimization:** Single large prompt ($0.50-1.00) vs multiple small prompts

### Layer 2: Core Scheduling Engine

#### Phase 1: Activity Sorting

**Sorting Strategy:**
```
Primary key: Priority (ascending - 1 before 5)
Secondary key: Frequency (descending - daily before monthly)
```

**Rationale:**
- Critical medications (priority 1, daily) must claim best slots first
- Frequent activities have less flexibility, should be placed early
- Optional wellness activities (priority 4-5) fill remaining gaps

**Expected Distribution After Sort:**
- Top 20%: Daily medications and critical therapies
- Middle 50%: Regular fitness, nutrition, consultations
- Bottom 30%: Optional activities and wellness practices

#### Phase 2: Slot Finding & Scoring

**For Each Activity:**
1. Determine required slot pattern based on frequency:
   - Daily: Find single consistent time across all days
   - Weekly (e.g., 3x/week): Find 3 slots per week, repeated across 12 weeks
   - Monthly: Find 1 slot per month across 3 months

2. Iterate through calendar to identify candidate slots

3. Score each candidate slot (0-10 scale)

**Scoring Function Design:**

**Hard Constraints (Score = 0 if violated):**
- **Time Window Compliance:** Activity specifies "6-8 AM", slot must fall within this range
- **Specialist Availability:** Check specialist's calendar for that day/time, respect holidays and days off
- **Equipment Availability:** Verify equipment not in maintenance, check concurrent usage limits
- **Travel Conflicts:** If client traveling and activity not remote-capable, slot is infeasible
- **No Time Overlaps:** Ensure no conflict with already-scheduled activities

**Soft Constraints (Adjust score 1-10):**
- **Time Preference Matching:** Fitness activities prefer morning (6-9 AM) or evening (5-8 PM), consultations prefer business hours
- **Activity Type Patterns:** Group related activities (all fitness on same days reduces gym trips)
- **Overcrowding Penalty:** Reduce score if day already has 4+ activities scheduled
- **Consistency Bonus:** Daily medications at same time increase adherence, add bonus for consistent timing
- **Equipment Utilization:** Slight bonus for using equipment that's underutilized

**Scoring Example:**
- Slot at 7 AM for "Morning Medication" (requires 6-8 AM):
  - Base score: 10 (within time window)
  - Specialist available: +0 (no change)
  - No conflicts: +0 (no change)
  - Consistent timing (same as yesterday): +1
  - **Final: 10**

- Slot at 3 PM for "HIIT Training" (prefers morning/evening):
  - Base score: 5 (suboptimal time)
  - Trainer available: +0
  - Day already has 3 activities: -2
  - **Final: 3**

#### Phase 3: Booking Logic

**Greedy Selection:**
- From all scored slots for current activity, select highest score
- If multiple slots tie, prefer earlier in the 90-day horizon (front-load scheduling)
- If score = 0 for all slots, activity cannot be scheduled

**State Updates After Booking:**
- Add activity to calendar at selected time
- Mark specialist as busy for that slot
- Decrement equipment availability counter
- Update daily activity count for overcrowding tracking

**Conflict Tracking:**
- If activity not scheduled, log detailed reason:
  - Which constraints were violated most often
  - Best slot found and its score (for debugging)
  - Suggested adjustments (e.g., "No specialist available Mondays")

#### Phase 4: Frequency Distribution

**Weekly Activities (most complex):**
- If activity requires "3x per week":
  1. Divide 90 days into 12 weeks
  2. For each week, find 3 best slots (e.g., Mon/Wed/Fri pattern)
  3. Ensure slots are distributed (not Mon/Mon/Tue)
  4. Prefer consistent pattern across weeks (same Mon/Wed/Fri for all 12 weeks)

**Daily Activities:**
- Find single optimal time slot (e.g., 8 AM)
- Apply across all 90 days
- Skip days where client is traveling

**Monthly Activities:**
- Find best day in each month (early, mid, or late)
- Spread evenly (e.g., 5th of each month)

### Layer 3: Output Generation

#### Deterministic Outputs

**Weekly Calendar View (Primary Output):**
```
Week 1: Jan 8 - Jan 14, 2025
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  Monday  │ Tuesday  │Wednesday │ Thursday │  Friday  │ Saturday │  Sunday  │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 7:00 AM  │ 7:00 AM  │ 7:00 AM  │ 7:00 AM  │ 7:00 AM  │ 7:00 AM  │ 7:00 AM  │
│ Blood    │ Blood    │ Blood    │ Blood    │ Blood    │ Blood    │ Blood    │
│ Pressure │ Pressure │ Pressure │ Pressure │ Pressure │ Pressure │ Pressure │
│ Med      │ Med      │ Med      │ Med      │ Med      │ Med      │ Med      │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 8:30 AM  │          │ 8:30 AM  │          │ 8:30 AM  │          │          │
│ HIIT     │          │ HIIT     │          │ HIIT     │          │          │
│ Training │          │ Training │          │ Training │          │          │
│ (Trainer)│          │ (Trainer)│          │ (Trainer)│          │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Daily Detail View:**
- List all activities for a specific day
- Show start time, duration, type, specialist/equipment
- Highlight any preparation requirements

**Monthly Overview:**
- High-level summary of activity counts per week
- Visual indicator of schedule density
- Flag weeks with travel or low activity

**Metrics Dashboard:**
- Overall success rate: "87 of 100 activities scheduled (87%)"
- By priority: "Priority 1: 18/19 (95%), Priority 2: 28/31 (90%)..."
- By activity type: "Fitness: 22/25, Medication: 18/18, Consultation: 8/10..."
- Constraint utilization: "Trainer Sarah: 75% booked, Gym Equipment: 60% utilized"

**JSON Export:**
- Machine-readable schedule for integration with other systems
- Include all metadata (activity IDs, specialist IDs, constraint references)

#### LLM-Generated Outputs

**Natural Language Schedule Summary:**

**Purpose:** Transform raw schedule data into user-friendly narrative that:
- Explains the health program's focus areas
- Highlights scheduling patterns and rationale
- Provides motivational framing
- Notes any important gaps or limitations

**Input to LLM:**
- Schedule statistics (success rate, activity distribution, busiest days)
- Priority breakdown (how many critical activities scheduled)
- Activity type patterns (e.g., fitness concentrated Mon/Wed/Fri)
- Conflicts or unscheduled activities with reasons

**Prompt Strategy:**
- Request 2-3 paragraph summary
- Specify tone: "warm health coach, not clinical"
- Include specific instructions: "Explain WHY activities are scheduled this way"
- Ask for actionable insights: "What should the user pay attention to?"

**Expected Output Example:**
```
Your 90-day health program prioritizes cardiovascular health and medication
adherence, with 18 daily medications scheduled consistently at 7 AM to build
routine. We've placed your 3 weekly HIIT sessions on Monday, Wednesday, and
Friday mornings when your preferred trainer Sarah is available, giving you
recovery days in between.

Nutrition consultations are scheduled monthly on the first Tuesday to review
progress and adjust your meal plans. We've kept weekends lighter (averaging
2 activities vs 4 on weekdays) to allow for flexibility and rest.

Note: We couldn't schedule your evening yoga sessions due to studio
availability conflicts during your February travel. Consider the online yoga
alternative during this period, or we can reschedule these sessions for March.
```

**Cost Analysis:**
- Prompt size: ~1,500 tokens (schedule statistics + instructions)
- Response size: ~500 tokens (2-3 paragraphs)
- Cost per summary: ~$0.02 with Gemini 2.5 Pro
- Total cost for project: ~$0.02 (generate once per schedule)

---

## Data Model Design

### Core Entities

#### Activity
**Purpose:** Represents a single health-related task that needs to be scheduled

**Essential Attributes:**
- **id:** Unique identifier
- **name:** Human-readable name (e.g., "Morning Blood Pressure Medication")
- **type:** Enum (Fitness, Food, Medication, Therapy, Consultation)
- **priority:** Integer 1-5 (1 = critical, 5 = optional)
- **frequency:** Complex object (see Frequency model below)
- **duration_minutes:** How long the activity takes
- **time_window:** Optional (e.g., "06:00-08:00" for morning medications)
- **details:** Text description (e.g., "Maintain HR 120-140 BPM")

**Constraint References:**
- **specialist_id:** Optional reference to required specialist
- **equipment_ids:** List of required equipment
- **location:** Enum (Home, Gym, Clinic, Any)
- **remote_capable:** Boolean (can this be done via video call?)

**Metadata:**
- **preparation_requirements:** List of prep tasks (e.g., ["Cook meal", "Warm up 5 min"])
- **backup_activity_ids:** Alternative activities if this can't be scheduled
- **metrics_to_collect:** List of measurements (e.g., ["Heart rate", "Duration", "Calories"])

#### Frequency
**Purpose:** Defines how often an activity should occur

**Supported Patterns:**
- **Daily:** Every day (e.g., medications)
- **Weekly:** Specific number per week (e.g., "3x per week") with optional day preferences
- **Monthly:** Specific number per month or specific dates
- **Custom:** Interval-based (e.g., "every 3 days")

**Attributes:**
- **pattern:** Enum (Daily, Weekly, Monthly, Custom)
- **count:** Integer (e.g., 3 for "3x per week")
- **preferred_days:** Optional list (e.g., [Monday, Wednesday, Friday])
- **interval_days:** For custom patterns (e.g., 3 for "every 3 days")

#### Specialist
**Purpose:** Healthcare professional or trainer with limited availability

**Attributes:**
- **id:** Unique identifier
- **name:** Human-readable name
- **type:** Enum (Trainer, Dietitian, Therapist, Physician, Allied_Health)
- **availability:** List of weekly time blocks (e.g., "Monday 8 AM - 5 PM")
- **days_off:** List of dates (holidays, vacation)
- **max_concurrent_clients:** Usually 1, but group classes could be higher

#### Equipment
**Purpose:** Physical resources with limited availability

**Attributes:**
- **id:** Unique identifier
- **name:** Human-readable name (e.g., "Treadmill", "Sauna", "MRI Machine")
- **location:** Where the equipment is located
- **maintenance_windows:** List of time ranges when unavailable
- **max_concurrent_users:** Usually 1, some equipment supports multiple
- **requires_specialist:** Boolean (some equipment needs supervision)

#### Travel Period
**Purpose:** Times when the client is unavailable or has limited access to resources

**Attributes:**
- **start_date:** Beginning of travel
- **end_date:** End of travel
- **location:** Where the client will be
- **remote_activities_only:** Boolean (if true, only remote-capable activities can be scheduled)

#### TimeSlot
**Purpose:** A specific scheduled instance of an activity

**Attributes:**
- **activity_id:** Reference to the activity being scheduled
- **date:** Specific calendar date
- **start_time:** Time of day (e.g., "08:30")
- **duration_minutes:** How long this instance will take
- **specialist_id:** Which specialist is facilitating (if applicable)
- **equipment_ids:** Which equipment is being used (if applicable)

### Validation Rules

**Activity Validation:**
- Priority must be 1-5
- Duration must be 5-480 minutes (not 0, not >8 hours)
- If specialist_id provided, must reference valid specialist
- Frequency count must be reasonable (e.g., not "50x per week")
- Time window must be valid 24-hour format and end > start

**Specialist Validation:**
- Must have at least one availability block
- Availability blocks must not overlap with each other
- Days off must be valid dates within the scheduling horizon

**Equipment Validation:**
- Max concurrent users must be ≥1
- Maintenance windows must not overlap

**Frequency Validation:**
- Weekly count must be ≤7 (can't do more than 7x per week)
- Daily pattern cannot have preferred_days specified (contradiction)
- Monthly count must be ≤31

### Data Generation Strategy (LLM)

**Prompt Design Principles:**

1. **Explicit Schema:** Provide complete JSON schema with field descriptions
2. **Distribution Requirements:** Specify desired activity type percentages to ensure realism
3. **Edge Cases:** Request variety (early morning meds, multi-hour consultations, daily vs monthly mix)
4. **Validation Rules:** Include rules in prompt to reduce hallucinations
5. **Output Format:** Request pure JSON (no markdown, no explanations)

**Sample Prompt Structure (High-Level):**
```
Generate realistic health program data for a 90-day period:

ACTIVITIES (100+ total):
- 20% Medication (priority 1-2, mostly daily, strict time windows)
- 30% Fitness (priority 2-3, weekly patterns, require trainers/equipment)
- 25% Nutrition (priority 2-4, varied frequencies)
- 15% Therapy (priority 2-3, weekly/biweekly)
- 10% Consultation (priority 2-3, monthly)

Include variety:
- Early morning medications (6-8 AM)
- Lunch-related activities (12-2 PM)
- Evening fitness (5-8 PM)
- Multi-hour sessions (therapy, consultations)

SPECIALISTS (10-15):
- 4-5 Fitness trainers (varied availability, some weekends)
- 2-3 Dietitians (business hours only)
- 2 Therapists (flexible hours)
- 2-3 Physicians (limited availability)
- 1-2 Allied health (varied)

Each specialist: realistic weekly schedule with 2-3 time blocks per day they work

EQUIPMENT (8-10):
- Gym equipment (treadmill, weights, yoga mats)
- Therapy equipment (sauna, ice bath)
- Medical equipment (blood pressure monitor, etc.)

Include 1-2 maintenance windows per item over 90 days

TRAVEL (5-7 periods):
- Mix of weekend trips (2-3 days) and longer vacations (1 week)
- Spread across the 90-day period
- Some allowing remote activities, some not

OUTPUT: Valid JSON matching the schema below...
[schema details]

VALIDATION:
- No activities >8 hours duration
- No frequencies >7 per week for weekly patterns
- All specialist/equipment references must be valid IDs
- Time windows must be realistic (medication: 2 hour window, consultation: 8 hour window)
```

**Post-Generation Validation:**
- Parse JSON response into Pydantic models (catches type errors)
- Run sanity checks (no 10x daily medications, no 24-hour activities)
- Verify referential integrity (all specialist_ids exist, all equipment_ids exist)
- Manual spot-check 10-15 activities for realism
- If >10% fail validation, regenerate with refined prompt

---

## Algorithm Design

### Greedy Scheduling Algorithm

**High-Level Pseudocode:**

```
Function: ScheduleActivities(activities, constraints, horizon_days)

1. Initialize:
   - Empty calendar (90 days × 24 hours)
   - Empty specialist booking tracker
   - Empty equipment booking tracker
   - Empty conflict log

2. Sort activities:
   - Primary: priority ascending (1 before 5)
   - Secondary: frequency descending (daily before monthly)

3. For each activity in sorted list:

   a. Determine slot requirements based on frequency:
      - Daily → need 90 slots (1 per day)
      - Weekly 3x → need 36 slots (3 per week × 12 weeks)
      - Monthly → need 3 slots (1 per month × 3 months)

   b. Find all candidate slot patterns:
      - For daily: iterate through hours 0-23, find best consistent time
      - For weekly: iterate through week patterns (Mon/Wed/Fri, Tue/Thu/Sat, etc.)
      - For monthly: iterate through days 1-28, find best day of month

   c. Score each candidate pattern:
      - For each slot in the pattern:
        - Check hard constraints (specialist, equipment, travel, time window)
        - If any hard constraint violated → pattern score = 0
        - Calculate soft constraint score (1-10)
      - Pattern total score = average of all slot scores

   d. Select best pattern:
      - If max score = 0 → activity cannot be scheduled (log conflict)
      - Otherwise → book highest-scoring pattern

   e. Update state:
      - Add slots to calendar
      - Mark specialists as busy for those times
      - Mark equipment as in-use for those times
      - Increment daily activity counts

4. Return:
   - Completed schedule (list of TimeSlots)
   - Conflict report (unscheduled activities with reasons)
   - Metrics (success rate, constraint utilization)
```

### Complexity Analysis

**Time Complexity:**
- N = number of activities (100)
- D = horizon days (90)
- H = hours per day (24)
- P = patterns per frequency type (~10-20)

**Per Activity:**
- Sorting: O(N log N) - one-time cost
- Pattern iteration: O(P)
- Pattern scoring: O(D) for daily, O(D × slots_per_week) for weekly
- Worst case per activity: O(P × D)

**Overall: O(N log N + N × P × D)**
- With N=100, P=20, D=90: ~180,000 operations
- Expected runtime: 2-5 seconds (dominated by constraint checking, not computation)

**Space Complexity:**
- Calendar: O(D × H) = ~2,160 slots
- Bookings: O(N × slots_per_activity) = ~2,000-5,000 slots
- Overall: O(D × H + N × S) where S = average slots per activity
- Expected memory: <50 MB

### Optimization Opportunities (If Needed)

**If success rate < 85%:**
1. **Backtracking:** If critical activity fails, try unscheduling lower-priority activities to make room
2. **Specialist preference relaxation:** Allow second-choice specialists if first choice unavailable
3. **Time window expansion:** For priority 1-2 activities, slightly expand time windows if no slots found

**If runtime > 10 seconds:**
1. **Pattern pruning:** Skip obviously infeasible patterns early (e.g., if specialist works 0 Mondays, skip Mon/Wed/Fri pattern)
2. **Caching:** Cache specialist availability lookups (frequently checked)
3. **Early termination:** Once a pattern scores 9+, stop searching for better options

---

## LLM Integration Strategy

### Integration Point 1: Data Generation

**Objective:** Generate 100+ realistic activities and all constraint data in <5 minutes with <$1 cost

**Approach:**
- **Single comprehensive prompt** generates entire dataset at once
- Reduces API calls from 100+ (one per activity) to 1-2 (full dataset + potential refinement)
- Cost: $0.50-1.00 per generation with Gemini 2.5 Pro

**Prompt Engineering:**
- Provide complete JSON schema with examples
- Specify distribution requirements (activity types, priority levels, frequency patterns)
- Request edge cases explicitly (morning medications, evening fitness, multi-hour consultations)
- Include validation rules to guide LLM (no activities >8 hours, frequencies ≤7 per week)
- Ask for pure JSON output (no markdown code blocks, no explanations)

**Validation Pipeline:**
1. Parse JSON response
2. Load into Pydantic models (automatic type checking)
3. Run sanity checks (duration 5-480 min, frequency counts reasonable, no orphaned references)
4. Manual spot-check 10-15 activities for realism
5. If >10% fail validation → refine prompt and regenerate

**Fallback Strategy:**
- If LLM output quality poor after 2-3 iterations → generate 50 activities via LLM, create 50 manually
- If cost exceeds budget → use smaller model (Gemini 1.5 Flash) or reduce to 70 activities

### Integration Point 2: Schedule Summary

**Objective:** Transform raw schedule data into user-friendly narrative that explains the program

**Approach:**
- **Single summary prompt** after scheduling completes
- Input: Schedule statistics, activity patterns, conflicts
- Output: 2-3 paragraph natural language summary

**Prompt Engineering:**
- Specify tone and style: "Warm health coach explaining personalized program"
- Request specific content:
  - Health focus areas based on activity types
  - Scheduling patterns and rationale (why Mon/Wed/Fri for HIIT)
  - Gaps or limitations with constructive suggestions
- Provide context: "User is seeing this schedule for the first time, help them understand it"

**Cost Analysis:**
- Input tokens: ~1,500 (schedule data + prompt instructions)
- Output tokens: ~500 (2-3 paragraphs)
- Cost per summary: ~$0.02 with Gemini 2.5 Pro
- Total for project: ~$0.02 (generate once)

**Quality Control:**
- Verify summary matches actual schedule data (no hallucinated activities)
- Check tone is appropriate (friendly but not overly casual)
- Ensure actionable insights provided (what user should pay attention to)

### Why Not Use LLM For Scheduling?

**Decision Rationale:**

**Rejected Approach: LLM-as-scheduler**
- Prompt LLM to "schedule these 100 activities given these constraints"
- Expected issues:
  - Hallucinations: LLM may invent time slots or ignore constraints
  - Cost: 10,000+ token responses = $0.20-0.50 per schedule attempt
  - Iteration: Multiple attempts needed to fix constraint violations = $1-2 total
  - Unpredictability: No guarantee of 100% constraint satisfaction
  - Debugging: Impossible to trace why LLM made specific decisions

**Chosen Approach: Deterministic scheduler + LLM for I/O**
- Scheduling logic is deterministic greedy algorithm
- Benefits:
  - Zero hallucinations: Hard constraints always satisfied
  - Cheap: Scheduling is free (no API calls)
  - Debuggable: Can trace exactly why each activity placed where it is
  - Reliable: Same input always produces same output
  - Fast: 2-5 seconds vs 30-60 seconds for LLM

**LLM Value-Add:**
- Data generation: Saves 6+ hours of manual work
- Natural language I/O: Superior user experience vs raw JSON
- Cost: <$2 total vs $10-20 if using LLM for scheduling logic

### Prompt Documentation Requirements

**Assignment Requirement:** Document all prompts used

**PROMPTS_USED.md Structure:**

1. **Data Generation Prompt**
   - Full prompt text
   - Purpose: Generate 100+ activities and constraint data
   - Input: Schema definitions
   - Expected output: Complete JSON dataset
   - Iterations made: Original prompt, refinements after validation failures
   - Cost: $0.50-1.00

2. **Schedule Summary Prompt**
   - Full prompt text
   - Purpose: Generate natural language explanation of schedule
   - Input: Schedule statistics and patterns
   - Expected output: 2-3 paragraph summary
   - Tone specifications: Warm health coach
   - Cost: ~$0.02

3. **Total Cost Breakdown**
   - Data generation: $0.50-1.00
   - Summary generation: $0.02
   - Refinement iterations: $0.20-0.50
   - **Total: $1.00-2.00**

4. **Accuracy Metrics**
   - Data generation validation pass rate: Target 90%+
   - Manual quality review: Sample 15 activities, assess realism
   - Summary accuracy: Verify claims match actual schedule data

---

## Implementation Timeline

### Day 1: Foundation + Data Generation (8 hours)

**Morning Block (3-4 hours): Data Models**

**Objectives:**
- Define all Pydantic models with complete validation
- Implement JSON loading/saving utilities
- Create basic test suite for model validation

**Deliverables:**
- `models/activity.py`: Activity, Frequency models
- `models/constraints.py`: Specialist, Equipment, Travel models
- `models/schedule.py`: TimeSlot model
- `utils/io.py`: JSON load/save with error handling
- `tests/test_models.py`: Validation tests

**Success Criteria:**
- All models enforce validation rules
- Can load/save complex nested structures
- Tests catch common validation failures (negative duration, invalid time windows, etc.)

**Afternoon Block (4-5 hours): LLM Data Generation**

**Objectives:**
- Set up Gemini 2.5 Pro API client
- Design and test data generation prompt
- Generate complete validated dataset
- Document prompts used

**Deliverables:**
- `generators/llm_generator.py`: Prompt templates, API client, validation pipeline
- `data/generated/activities.json`: 100+ validated activities
- `data/generated/specialists.json`: 10-15 specialists with availability
- `data/generated/equipment.json`: 8-10 equipment items
- `data/generated/travel.json`: 5-7 travel periods
- `docs/PROMPTS_USED.md`: Initial version with data generation prompt

**Success Criteria:**
- 100+ activities generated with 90%+ validation pass rate
- Activities span all required types (fitness, medication, nutrition, therapy, consultation)
- Realistic distribution of priorities and frequencies
- All constraint data has referential integrity (no orphaned IDs)
- Manual spot-check of 15 activities shows realism
- Total cost: <$1.50

**End-of-Day Checkpoint:**
- Complete validated dataset ready for scheduling
- All data structures proven to work
- Foundation for Day 2 scheduling implementation

---

### Day 2: Scheduling Engine + Output (8 hours)

**Morning Block (4-5 hours): Greedy Scheduler**

**Objectives:**
- Implement core greedy scheduling algorithm
- Build constraint checking logic (hard and soft)
- Create booking and conflict tracking systems

**Deliverables:**
- `scheduler/greedy.py`: Main scheduling algorithm
- `scheduler/constraints.py`: Hard constraint validators (specialist availability, equipment, travel, time windows, overlaps)
- `scheduler/scoring.py`: Soft constraint scoring (time preferences, grouping, overcrowding)
- `scheduler/state.py`: Calendar state management, booking tracker

**Success Criteria:**
- Scheduler successfully places 85-90% of activities
- Priority 1 activities achieve 95%+ success rate
- Zero hard constraint violations (verify in tests)
- Conflicts logged with detailed reasons
- Runtime <10 seconds for 100 activities

**Afternoon Block (3-4 hours): Calendar Output + LLM Summary**

**Objectives:**
- Build calendar formatters for human-readable output
- Implement LLM summary generation
- Create metrics calculator
- Export functionality

**Deliverables:**
- `output/calendar_formatter.py`: Weekly grid view, daily detail, monthly overview
- `output/summary_generator.py`: LLM prompt template, API client, summary insertion
- `output/metrics.py`: Success rate calculation, constraint utilization, activity distribution
- `output/exporter.py`: JSON export for integration

**Success Criteria:**
- Weekly calendar view is readable and clear
- LLM summary accurately reflects schedule data (no hallucinations)
- Summary tone is appropriate (warm health coach)
- Metrics provide actionable insights
- JSON export is valid and complete
- Total LLM cost for summaries: <$0.05

**End-of-Day Checkpoint:**
- Complete working system from input → scheduling → output
- Can generate schedule with natural language summary in <15 seconds
- Ready for testing and polish

---

### Day 3: Testing, Documentation, Polish (8 hours)

**Morning Block (3-4 hours): Testing + Edge Cases**

**Objectives:**
- Write comprehensive test suite
- Test edge cases and failure modes
- Measure and validate success criteria
- Fix bugs discovered during testing

**Deliverables:**
- `tests/test_scheduler.py`: Core scheduling logic tests
- `tests/test_constraints.py`: Constraint validation tests
- `tests/test_edge_cases.py`: Edge case handling (all specialists unavailable, overlapping travel, impossible constraints)
- `tests/test_performance.py`: Runtime and memory benchmarks

**Test Cases:**
1. Priority 1 activities achieve ≥95% success rate
2. No specialist ever double-booked
3. No equipment over-allocated
4. Travel periods respected (no in-person activities during remote-only travel)
5. Time windows strictly enforced
6. No overlapping activities in schedule
7. Performance: 100 activities scheduled in <10 seconds
8. Edge: All specialists unavailable on a specific day
9. Edge: Equipment in maintenance during only feasible time window
10. Edge: Activity with impossible constraints (requires 8 AM slot but specialist only works 2-6 PM)

**Success Criteria:**
- All tests pass
- Success rate 85-90% overall, 95%+ for priority 1
- Zero constraint violations
- Performance targets met
- Edge cases handled gracefully (logged, not crashed)

**Afternoon Block (4-5 hours): Documentation**

**Objectives:**
- Write production-ready documentation
- Document all design decisions
- Complete prompt documentation
- Create examples and quick-start guide

**Deliverables:**
- `README.md`: Project overview, quick start (install + run in <2 min), architecture summary, key features, design decisions
- `docs/ARCHITECTURE.md`: Detailed algorithm explanation, constraint handling, complexity analysis, LLM integration rationale
- `docs/PROMPTS_USED.md`: Complete with all prompts, iterations, cost breakdown, accuracy metrics
- `docs/EVALUATION.md`: Success metrics, performance benchmarks, comparison to alternatives
- `examples/`: Sample input files, expected outputs, instructions

**README.md Structure:**
1. **Project Overview:** What this system does in 2-3 sentences
2. **Quick Start:** Copy-paste commands to install and run (must work in <2 minutes)
3. **Key Features:** Bullet list of main capabilities
4. **Architecture:** High-level diagram and component explanation (reference ARCHITECTURE.md)
5. **Design Decisions:** Why greedy not CP-SAT, why LLM at specific touchpoints
6. **Performance:** Benchmarks (runtime, success rate, cost)
7. **Future Enhancements:** What could be improved with more time

**ARCHITECTURE.md Structure:**
1. **Algorithm Deep Dive:** Detailed greedy scheduling explanation with pseudocode
2. **Constraint Handling:** How each constraint type is validated
3. **Scoring Function:** Soft constraint rationale and weight tuning
4. **Complexity Analysis:** Time/space complexity with justification
5. **LLM Integration:** Why at these specific points, not in scheduling logic
6. **Comparison to Alternatives:** Why not CP-SAT, why not pure LLM

**PROMPTS_USED.md Structure:**
1. **Data Generation Prompt:** Full text, purpose, iterations, cost, validation results
2. **Summary Generation Prompt:** Full text, purpose, tone specifications, cost
3. **Total Cost Breakdown:** Itemized costs, total <$2
4. **Quality Metrics:** Validation pass rates, manual review findings

**Success Criteria:**
- README quick-start works exactly as documented
- All design decisions justified with clear rationale
- Documentation is professional and thorough
- Examples demonstrate key capabilities

**End-of-Day Checkpoint:**
- Submission-ready project with complete documentation
- All tests passing
- Performance and quality targets met
- Ready for final review and submission

---

## Risk Assessment & Mitigation

### Risk 1: LLM Data Generation Quality Issues

**Probability:** Medium (30-40%)
**Impact:** High (would require 6+ hours manual data creation)

**Symptoms:**
- Validation pass rate <70%
- Activities have unrealistic patterns (10x daily medication)
- Constraint data has broken references (specialist IDs don't match)
- Cost exceeds budget due to multiple regenerations

**Mitigation Strategies:**

**Prevention:**
- Explicit schema in prompt with detailed examples
- Validation rules embedded in prompt (no activities >8 hours, etc.)
- Request pure JSON (no markdown) to avoid parsing issues
- Test prompt with small batch (10 activities) before full generation

**Detection:**
- Automated validation catches type errors, constraint violations
- Manual spot-check of 15 activities for realism
- Cost tracking alerts if >$1.50 spent on generation

**Recovery:**
- Refine prompt based on validation failures, regenerate
- If quality still poor after 2 iterations → hybrid approach: 50 via LLM, 50 manual
- If cost exceeds budget → switch to Gemini 1.5 Flash (cheaper) or reduce to 70 activities

**Fallback:**
- Manual creation of 100 activities takes ~6 hours but guarantees quality
- Can create subset (30-50) manually as baseline, use LLM to generate variations

---

### Risk 2: Greedy Scheduler Success Rate Too Low

**Probability:** Low (15-20%)
**Impact:** Medium (would fail to meet 85-90% target)

**Symptoms:**
- Overall success rate <80%
- Priority 1 activities <90% (target 95%+)
- Many conflicts logged due to over-constrained activities

**Root Causes:**
- Scoring function weights poorly tuned
- Specialist availability too limited
- Greedy approach makes poor early decisions that block later activities

**Mitigation Strategies:**

**Prevention:**
- Generate sufficient specialist availability (each specialist works 30+ hours/week)
- Test scoring function with small dataset (20-30 activities) before full run
- Implement basic conflict detection (if priority 1 fails, flag immediately)

**Detection:**
- Run metrics after scheduling completes
- Compare success rates by priority level
- Analyze conflict logs for patterns (e.g., "Specialist X always unavailable")

**Recovery:**
- **Tuning:** Adjust scoring weights (increase time preference penalty, reduce grouping bonus)
- **Relaxation:** For priority 1-2 activities, expand time windows slightly if no slots found
- **Backtracking:** If priority 1 fails, try unscheduling lower-priority activities to make room

**Fallback:**
- If greedy can't achieve 85%, implement simple backtracking (adds 2-3 hours)
- Reduce total activities to 70-80 (easier to schedule fewer activities)
- Manually adjust specialist availability to be more generous

---

### Risk 3: Timeline Slippage

**Probability:** Medium (25-35%)
**Impact:** Medium (could delay submission or force scope cuts)

**Symptoms:**
- Day 1 extends beyond 8 hours
- Scheduler implementation takes >5 hours on Day 2
- Debugging consumes buffer time

**Root Causes:**
- Pydantic model validation more complex than expected
- LLM prompt requires many iterations to get quality data
- Bugs in scheduling logic hard to diagnose

**Mitigation Strategies:**

**Prevention:**
- Start with simplest models, add complexity incrementally
- Test LLM prompt with small batch before full generation
- Use extensive logging in scheduler for debuggability
- Time-box each block (if over by 1 hour, cut scope)

**Detection:**
- Track actual hours spent per block vs. planned
- Alert if any block exceeds planned time by >50%

**Recovery:**
- **Day 1 overrun:** Cut manual spot-check to 5 activities instead of 15
- **Day 2 overrun:** Skip monthly overview formatter, focus on weekly view only
- **Day 3 overrun:** Reduce documentation depth (combine ARCHITECTURE + EVALUATION into README)

**Fallback:**
- If 2+ hours behind by end of Day 2 → cut LLM summaries entirely (saves 3 hours)
- If 4+ hours behind → submit Week 1 version (deterministic scheduler only, no LLM features)
- Buffer: Day 3 afternoon has 4 hours for documentation, can compress to 2 hours if needed

---

### Risk 4: LLM API Cost Exceeds Budget

**Probability:** Low (10-15%)
**Impact:** Low (budget is $2, unlikely to matter but violates constraint)

**Symptoms:**
- Data generation costs >$1.50 due to multiple iterations
- Summary generation unexpectedly expensive (model returns very long responses)

**Root Causes:**
- Many prompt iterations needed to get quality data
- Gemini 2.5 Pro pricing higher than expected
- Response tokens exceed estimate (LLM verbose despite instructions)

**Mitigation Strategies:**

**Prevention:**
- Test prompt cost with small batch first, extrapolate to full dataset
- Specify max response length in prompt (e.g., "2-3 paragraphs, no more than 500 words")
- Use Gemini 1.5 Flash for initial testing, upgrade to 2.5 Pro only if needed

**Detection:**
- Track API costs in real-time after each call
- Alert if cumulative cost >$1.50 after data generation

**Recovery:**
- Switch to cheaper model (Gemini 1.5 Flash) if quality acceptable
- Reduce summary length to 1 paragraph instead of 2-3
- Cache LLM responses aggressively (don't regenerate unnecessarily)

**Fallback:**
- Skip summary generation entirely (saves ~$0.02, minimal impact)
- Use free tier model (Gemini 1.5 Flash has free quota)
- Reduce activities to 70 (less data to generate = lower cost)

---

## Success Metrics & Evaluation

### Primary Metrics (Must Achieve)

| Metric | Target | Measurement Method | Pass/Fail |
|--------|--------|-------------------|-----------|
| Overall Success Rate | 85-90% | Activities scheduled / Total activities | Must be ≥85% |
| Priority 1 Success Rate | 95%+ | Priority 1 scheduled / Total priority 1 | Must be ≥95% |
| Constraint Violations | 0 | Test suite validation | Must be exactly 0 |
| Runtime Performance | <10s | Time from start to schedule output | Must be <10s |
| LLM Cost | <$2 | Track all API calls | Must be ≤$2 |

### Secondary Metrics (Nice to Have)

| Metric | Target | Measurement Method | Notes |
|--------|--------|-------------------|-------|
| Priority 2 Success Rate | 90%+ | Priority 2 scheduled / Total priority 2 | Indicates good prioritization |
| Average Activities/Day | 2-4 | Sum scheduled / 90 days | Not overcrowded, not sparse |
| Specialist Utilization | 60-80% | Booked hours / Available hours | Efficient use of resources |
| Documentation Clarity | High | Peer review or self-assessment | Quick-start works in <2 min |
| Test Coverage | 70%+ | Code coverage tool | Core logic well-tested |

### Evaluation Framework

**Scheduling Quality Assessment:**

1. **Success Rate by Priority:**
   - Calculate percentage scheduled for each priority level (1-5)
   - Verify inverse correlation (priority 1 > priority 2 > ... > priority 5)
   - Flag if any priority 1-2 activities unscheduled (manual review required)

2. **Constraint Satisfaction:**
   - Run automated tests for each constraint type
   - Manually verify random sample (10 time slots) against specialist/equipment availability
   - Confirm zero overlapping activities in final schedule

3. **Schedule Quality:**
   - Check for overcrowding (flag days with >6 activities)
   - Verify weekly patterns consistent (e.g., HIIT always Mon/Wed/Fri, not random)
   - Confirm medications scheduled at consistent times daily (adherence optimization)

**LLM Performance Assessment:**

1. **Data Generation Quality:**
   - Validation pass rate: % of generated activities that pass Pydantic validation
   - Realism score: Manual review of 15 activities on 1-5 scale (realistic health program?)
   - Diversity: Verify distribution matches requirements (30% fitness, 20% medication, etc.)
   - Cost efficiency: $ spent per activity generated

2. **Summary Quality:**
   - Accuracy: Verify all claims in summary match actual schedule data (no hallucinations)
   - Tone: Assess warmth/professionalism on 1-5 scale
   - Usefulness: Does summary provide actionable insights? (yes/no)
   - Cost: $ per summary generated

**System Performance Assessment:**

1. **Runtime Benchmarks:**
   - Data loading: <1 second
   - Scheduling: <5 seconds
   - LLM summary: <5 seconds (dependent on API latency)
   - Calendar formatting: <1 second
   - Total end-to-end: <15 seconds

2. **Memory Usage:**
   - Measure peak memory during scheduling
   - Target: <500 MB (should be <100 MB with efficient implementation)

3. **Scalability Test:**
   - Run with 200 activities to test algorithm scaling
   - Verify runtime increases linearly, not exponentially
   - Target: 200 activities in <20 seconds

**Documentation Quality Assessment:**

1. **Quick-Start Test:**
   - Fresh environment (new virtual env, no prior setup)
   - Follow README instructions exactly
   - Measure time from clone to seeing first schedule output
   - Target: <5 minutes, ideally <2 minutes

2. **Completeness Check:**
   - All prompts documented in PROMPTS_USED.md? (yes/no)
   - Design decisions explained with rationale? (yes/no)
   - Architecture diagram provided? (yes/no)
   - Example outputs included? (yes/no)

3. **Clarity Assessment:**
   - Can a non-expert understand the system from README? (subjective, peer review ideal)
   - Are technical terms explained? (yes/no)
   - Is prompt iteration process documented? (yes/no)

### Comparison to Alternatives (Optional But Valuable)

**If time permits, demonstrate value of LLM integration:**

| Aspect | Manual Approach | LLM-Augmented Approach |
|--------|----------------|----------------------|
| Data Generation Time | 6-8 hours | 5-10 minutes |
| Data Quality | High (human-created) | High (with validation) |
| Data Diversity | Limited by creator patience | High (LLM generates variety) |
| Output Format | Raw JSON/text | Natural language + JSON |
| User Experience | Technical, hard to interpret | Friendly, contextual |
| Total Cost | $0 (time only) | <$2 (saves 6+ hours) |
| Debuggability | Same | Same (deterministic scheduler) |

**Justification for Hybrid Approach:**
- LLM saves significant time on low-risk tasks (data generation, summaries)
- Deterministic scheduler ensures correctness on high-risk task (constraint satisfaction)
- Total cost <$2 to save 6+ hours of manual work = excellent ROI
- User experience significantly improved with natural language I/O

---

## Future Enhancements (Out of Scope for Assignment)

### If Additional Time Available (Day 4+)

**High-Value Enhancements:**

1. **Backtracking for Priority 1 Activities (2-3 hours):**
   - If priority 1 activity fails to schedule, try unscheduling lower-priority activities to make room
   - Guarantees 100% success for critical medications/treatments
   - Adds complexity but significantly improves quality

2. **Web-Based Calendar View (4-6 hours):**
   - Simple HTML/CSS calendar grid instead of text output
   - Color-coding by activity type
   - Clickable activities showing details
   - Much more impressive for demo/submission

3. **Conflict Resolution Suggestions (2-3 hours):**
   - For unscheduled activities, use LLM to generate specific recommendations
   - "Consider booking Trainer Sarah on Tuesdays instead of Mondays"
   - "Equipment X is heavily utilized; suggest purchasing second unit"

4. **Visualizations (3-4 hours):**
   - Weekly heatmap (activity density by day/time)
   - Priority distribution pie chart
   - Specialist utilization bar chart
   - Makes evaluation much clearer

**Lower-Priority Enhancements:**

5. **Natural Language Activity Parser (3-4 hours):**
   - Allow user to input: "I need to do HIIT training 3 times a week in the morning"
   - LLM parses to structured Activity object
   - Nice demo but low practical value for assignment

6. **Rescheduling Support (4-6 hours):**
   - Handle "Specialist X called in sick, reschedule all their activities"
   - Requires more complex state management
   - Out of scope for "simple" scheduler

7. **Multi-User Scheduling (6-8 hours):**
   - Schedule activities for multiple clients sharing specialists/equipment
   - Significantly more complex constraint satisfaction
   - Interesting but not required

**Not Recommended (Low ROI):**
- CP-SAT solver (7-10 hours, marginal improvement over greedy for this use case)
- Preference learning (LLM learns user patterns over time - requires multi-schedule data)
- Advanced optimization (genetic algorithms, simulated annealing - overkill)

---

## Conclusion

This design document outlines a pragmatic approach to building a health activity scheduler in 3 days. The key strategic decisions are:

1. **Greedy algorithm over constraint programming:** 85-90% success rate achievable in 1 day vs 3-5 days for CP-SAT, with minimal quality difference for this use case

2. **LLM for data generation and summaries, not scheduling logic:** Saves 6+ hours of manual work and provides superior UX, while keeping scheduling deterministic and hallucination-free

3. **Focus on core requirements + one differentiator:** Meeting all assignment requirements with LLM augmentation is more valuable than partial implementation of advanced features

4. **Documentation as first-class deliverable:** Recruiters read documentation before code; invest 30% of time here

**Expected Outcomes:**
- ✅ Complete working system in 3 days
- ✅ 100+ realistic activities via LLM generation
- ✅ 85-90% scheduling success rate with 0 constraint violations
- ✅ Natural language summaries for superior UX
- ✅ Production-quality documentation
- ✅ Total LLM cost <$2
- ✅ Impressive yet practical submission

This approach balances innovation (strategic LLM use) with pragmatism (deterministic core) to deliver a high-quality submission within the assignment timeline.
