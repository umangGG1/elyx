# Health Activity Scheduler

**AI-Powered 90-Day Health Program Scheduler**

An intelligent scheduling system that transforms health recommendations into practical daily schedules using a greedy algorithm with LLM-augmented data generation.

## 🎯 Overview

This system schedules 100+ health activities across a 90-day period, respecting complex constraints like specialist availability, equipment conflicts, travel periods, and time windows. It achieves **93% overall success rate** with perfect scheduling for critical (P1-P3) activities.

## ✨ Key Features

- **93% Success Rate** - Exceeds 70% target by 23 percentage points
- **Perfect P1-P3 Scheduling** - 100% success for critical, important, and moderate priorities
- **Flexible Date Selection** - Activities can be scheduled across multiple weeks for optimal placement
- **Intelligent Backfill** - Second pass fills empty days with failed activities
- **Modern Web UI** - Beautiful, responsive interface for visualizing schedules
- **LLM Data Generation** - Realistic activity data generated with Gemini 2.5 Pro (<$2 cost)
- **Zero Constraint Violations** - Hard constraints always satisfied

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key (for data generation)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd elyx

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Generate Data and Run Scheduler

```bash
# Set your Gemini API key
export GOOGLE_API_KEY="your-api-key-here"

# Generate realistic health program data (100+ activities)
python3 generate_data.py

# Run the scheduler
python3 run_scheduler.py
```

### Launch Web Interface

```bash
# Start web server
./start_web.sh

# Or manually:
python3 web_app.py

# Open browser to: http://localhost:5000
```

## 📊 Results

**Current Performance:**
- Overall Success Rate: **93.0%**
- Priority 1 (Critical): **100.0%**
- Priority 2 (Important): **100.0%**
- Priority 3 (Moderate): **100.0%**
- Priority 4 (Low): **56.5%**
- Priority 5 (Very Low): **2.4%**

**Statistics:**
- 1,612 out of 1,734 required slots scheduled
- All 90 days utilized (average 17.9 activities per day)
- 0 constraint violations
- Runtime: <60 seconds for full scheduling

## 🏗️ Architecture

### Core Components

1. **Data Models** ([models/](models/))
   - Pydantic models for activities, specialists, equipment, travel periods
   - Strong validation and type safety

2. **LLM Generator** ([generators/](generators/))
   - Gemini 2.5 Pro integration for realistic data generation
   - Cost-optimized prompts (<$2 total)

3. **Scheduling Engine** ([scheduler/](scheduler/))
   - **GreedyScheduler**: Priority-based greedy algorithm with flexible date selection
   - **BalancedScheduler**: Alternative with capacity quotas per priority
   - Constraint checking for specialists, equipment, travel, time windows
   - Intelligent backfill pass for empty days

4. **Output Layer** ([output/](output/))
   - Calendar formatters (daily, weekly, monthly views)
   - Metrics calculation
   - JSON exports

5. **Web Interface** ([web_app.py](web_app.py), [templates/](templates/), [static/](static/))
   - Flask API server
   - Modern responsive UI with calendar visualization
   - Real-time metrics dashboard

### Scheduling Algorithm

**Two-Phase Greedy Approach:**

**Phase 1: Main Scheduling**
1. Sort activities by priority (P1 first) and frequency (daily first)
2. For each activity occurrence:
   - Generate candidates across ALL eligible weeks (flexible scheduling)
   - Score each candidate based on soft constraints
   - Book highest-scoring valid slot

**Phase 2: Backfill**
1. Identify failed activities
2. Find lightest days (fewest scheduled activities)
3. Attempt to place failed activities on light days
4. Prioritize by priority level

**Key Innovation: Flexible Date Selection**
- Weekly activities can be scheduled on ANY week, not just their assigned week
- P3-P5 activities prefer lighter days to avoid congestion
- Result: 93% success rate vs 45% with rigid date assignment

## 📁 Project Structure

```
elyx/
├── models/                 # Pydantic data models
│   ├── activity.py
│   ├── constraints.py
│   └── schedule.py
├── generators/            # LLM data generation
│   ├── llm_generator.py
│   └── prompts.py
├── scheduler/             # Core scheduling algorithms
│   ├── greedy.py         # Main greedy scheduler
│   ├── balanced.py       # Alternative balanced scheduler
│   ├── constraints.py    # Constraint validation
│   ├── scoring.py        # Slot scoring logic
│   └── state.py          # Schedule state management
├── output/                # Output formatters
│   ├── calendar_formatter.py
│   ├── metrics.py
│   └── exporter.py
├── utils/                 # Utility functions
│   └── io.py
├── data/
│   └── generated/        # Generated data files
│       ├── activities.json
│       ├── specialists.json
│       ├── equipment.json
│       └── travel.json
├── output/
│   └── results/          # Scheduler outputs
│       ├── schedule.json
│       ├── metrics.json
│       ├── failures.json
│       └── *.txt calendars
├── templates/            # Web UI templates
│   └── index.html
├── static/               # Web UI assets
│   ├── css/style.css
│   └── js/app.js
├── web_app.py           # Flask web server
├── generate_data.py     # Data generation script
├── run_scheduler.py     # Main scheduler workflow
└── README.md
```

## 🧪 Design Decisions

### Why Greedy Algorithm?

- **Simple**: Implementable in 1 day vs 3-5 days for CP-SAT solvers
- **Effective**: Achieves 93% success rate (far exceeds 70% target)
- **Fast**: <60 seconds runtime vs minutes for constraint programming
- **Debuggable**: Clear trace of scheduling decisions

### Why LLM for Data Generation?

- **Time Savings**: 5 minutes vs 6+ hours of manual creation
- **Realistic**: High-quality varied activities with proper distributions
- **Cost-Effective**: <$2 total cost with Gemini 2.5 Pro
- **Validated**: Pydantic models catch LLM hallucinations

### Why Not LLM for Scheduling?

- **Hallucinations**: LLM might invent slots or ignore constraints
- **Cost**: $0.20-0.50 per attempt, $1-2 with iterations
- **Unpredictable**: No guarantee of constraint satisfaction
- **Non-Debuggable**: Can't trace decision logic

**Result**: Deterministic scheduler + LLM for I/O = Best of both worlds

## 📖 Documentation

- [Design Document](docs/plans/2025-01-08-health-scheduler-design.md) - Comprehensive system design
- [Architecture Deep Dive](docs/ARCHITECTURE.md) - Algorithm details, data models, and design decisions
- [Evaluation Results](docs/EVALUATION.md) - Performance benchmarks, metrics, and quality analysis

## 🧪 Testing

### Running Tests

The project includes comprehensive test coverage for data models:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=models --cov=scheduler
```

### Test Coverage

- **Model Validation Tests** (`tests/test_models.py`) - 21 tests
  - Frequency validation (daily, weekly, monthly, custom patterns)
  - Activity validation (priority, duration, time windows)
  - Specialist validation (availability blocks, constraints)
  - Equipment validation (maintenance windows)
  - Travel period validation

### Test Results

All model tests pass successfully:

```
21 passed in 0.14s
```

The test suite validates:
- ✓ Pydantic model validation and constraints
- ✓ Time window logic
- ✓ Priority and duration boundaries
- ✓ Specialist availability constraints
- ✓ Equipment maintenance scheduling

## 🔮 Future Enhancements

- **Backtracking for P1**: Unschedule lower priorities to guarantee 100% P1 success
- **Conflict Resolution**: LLM-generated suggestions for failed activities
- **Rescheduling Support**: Handle specialist unavailability changes
- **Multi-User Scheduling**: Schedule for multiple clients sharing resources
- **Natural Language Input**: Parse activity descriptions with LLM

## 📊 Web UI Features

- **Dashboard**: Real-time success metrics and statistics
- **Priority Breakdown**: Visual progress bars for each priority level
- **Activity Distribution**: Type-based categorization with icons
- **Interactive Calendar**: Monthly view with activity counts
- **Daily Schedule**: Detailed timeline for selected dates
- **Failed Activities**: Analysis of unscheduled activities with reasons

## 🛠️ Technology Stack

- **Python 3.12**
- **Pydantic** - Data validation
- **Google Gemini 2.5 Pro** - LLM data generation
- **Flask** - Web framework
- **Vanilla JavaScript** - Frontend (no framework overhead)
- **Modern CSS** - Responsive design with CSS Grid/Flexbox

## 📝 License

This project is created as part of the Elyx internship assignment.

## 🙏 Acknowledgments

- Design inspired by the [Elyx Assignment.docx](docs/Elyx%20Assignment.docx) requirements
- LLM integration powered by Google Gemini
- Algorithm design based on greedy scheduling principles

---

**Built with ❤️ for Elyx Internship Assignment**

**Achievement Unlocked: 93% Success Rate! 🎉**
