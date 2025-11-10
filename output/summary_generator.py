"""
LLM-powered schedule summary generation.

Uses Google Gemini to generate natural language summaries of schedules.
"""

import os
from datetime import date, timedelta
from typing import List, Dict, Any
import google.generativeai as genai

from models.activity import Activity
from models.schedule import TimeSlot
from scheduler.state import SchedulerState


def configure_llm():
    """Configure the LLM API with the API key from environment."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set. "
            "Set it with: export GOOGLE_API_KEY='your-api-key'"
        )
    genai.configure(api_key=api_key)


def generate_schedule_summary(
    state: SchedulerState,
    activities: List[Activity],
    start_date: date,
    end_date: date,
    model_name: str = "gemini-2.0-flash-exp"
) -> str:
    """
    Generate a natural language summary of the schedule.

    Args:
        state: The scheduler state with booked slots and failures
        activities: List of all activities
        start_date: Schedule start date
        end_date: Schedule end date
        model_name: Gemini model to use

    Returns:
        Natural language summary as a string
    """
    configure_llm()

    # Prepare schedule data
    schedule_data = _prepare_schedule_data(state, activities, start_date, end_date)

    # Create prompt
    prompt = _create_summary_prompt(schedule_data)

    # Call LLM
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    return response.text


def generate_failure_analysis(
    state: SchedulerState,
    activities: List[Activity],
    model_name: str = "gemini-2.0-flash-exp"
) -> str:
    """
    Generate an analysis of why certain activities failed to schedule.

    Args:
        state: The scheduler state with failures
        activities: List of all activities
        model_name: Gemini model to use

    Returns:
        Natural language analysis of failures
    """
    if not state.failed_activities:
        return "All activities were successfully scheduled!"

    configure_llm()

    # Prepare failure data
    failure_data = _prepare_failure_data(state)

    # Create prompt
    prompt = _create_failure_analysis_prompt(failure_data)

    # Call LLM
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    return response.text


def _prepare_schedule_data(
    state: SchedulerState,
    activities: List[Activity],
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """Prepare schedule data for summarization."""
    # Create activity lookup
    activity_map = {a.id: a for a in activities}

    # Calculate statistics
    total_days = (end_date - start_date).days + 1
    total_scheduled = len(state.booked_slots)
    total_failed = len(state.failed_activities)

    # Calculate required occurrences
    total_required = total_scheduled + sum(
        attempt.attempts for attempt.failures in state.failed_activities.values()
    )

    # Group by priority
    by_priority = {}
    for priority in range(1, 6):
        p_activities = [a for a in activities if a.priority == priority]
        p_scheduled = [s for s in state.booked_slots if activity_map[s.activity_id].priority == priority]
        p_failed = [f for f in state.failed_activities.values() if f.activity.priority == priority]

        by_priority[f"P{priority}"] = {
            "count": len(p_activities),
            "scheduled": len(p_scheduled),
            "failed": len(p_failed)
        }

    # Group by type
    by_type = {}
    for activity in activities:
        act_type = activity.type.value
        if act_type not in by_type:
            by_type[act_type] = {
                "count": 0,
                "scheduled": 0,
                "failed": 0
            }
        by_type[act_type]["count"] += 1

    for slot in state.booked_slots:
        activity = activity_map[slot.activity_id]
        by_type[activity.type.value]["scheduled"] += 1

    for failure in state.failed_activities.values():
        by_type[failure.activity.type.value]["failed"] += failure.attempts

    # Activities per day
    slots_per_day = {}
    for slot in state.booked_slots:
        if slot.date not in slots_per_day:
            slots_per_day[slot.date] = 0
        slots_per_day[slot.date] += 1

    avg_per_day = sum(slots_per_day.values()) / len(slots_per_day) if slots_per_day else 0
    min_per_day = min(slots_per_day.values()) if slots_per_day else 0
    max_per_day = max(slots_per_day.values()) if slots_per_day else 0

    return {
        "period": {
            "start": start_date.strftime("%B %d, %Y"),
            "end": end_date.strftime("%B %d, %Y"),
            "days": total_days
        },
        "summary": {
            "total_scheduled": total_scheduled,
            "total_failed": total_failed,
            "total_required": max(total_required, total_scheduled),
            "success_rate": (total_scheduled / max(total_required, 1) * 100)
        },
        "by_priority": by_priority,
        "by_type": by_type,
        "distribution": {
            "avg_per_day": avg_per_day,
            "min_per_day": min_per_day,
            "max_per_day": max_per_day
        }
    }


def _prepare_failure_data(state: SchedulerState) -> Dict[str, Any]:
    """Prepare failure data for analysis."""
    failure_report = state.get_failure_report()

    # Convert to list format
    failure_list = []
    for report in failure_report:
        failure_list.append({
            "name": report["activity_name"],
            "type": report["activity_type"],
            "priority": report["priority"],
            "failed_count": report["attempts"],
            "reason": report["sample_reason"] or "Unknown",
            "violation_types": report["violation_types"]
        })

    return {
        "total_failed": sum(r["attempts"] for r in failure_report),
        "activities_affected": len(failure_report),
        "failures": failure_list
    }


def _create_summary_prompt(schedule_data: Dict[str, Any]) -> str:
    """Create prompt for overall schedule summary."""
    return f"""You are a health program coordinator summarizing a client's scheduled activities.

Generate a concise, friendly summary (2-3 paragraphs) of the following schedule:

PERIOD: {schedule_data['period']['start']} to {schedule_data['period']['end']} ({schedule_data['period']['days']} days)

OVERALL SUCCESS:
- Scheduled: {schedule_data['summary']['total_scheduled']} slots
- Failed: {schedule_data['summary']['total_failed']} activities
- Success Rate: {schedule_data['summary']['success_rate']:.1f}%

BY PRIORITY:
{_format_priority_data(schedule_data['by_priority'])}

BY TYPE:
{_format_type_data(schedule_data['by_type'])}

DAILY DISTRIBUTION:
- Average: {schedule_data['distribution']['avg_per_day']:.1f} activities/day
- Range: {schedule_data['distribution']['min_per_day']}-{schedule_data['distribution']['max_per_day']} activities/day

Write a summary that:
1. Highlights the overall success and key metrics
2. Mentions the most common activity types
3. Notes any interesting patterns or priorities
4. Is encouraging and positive in tone

Do not use bullet points. Write in natural paragraphs."""


def _create_failure_analysis_prompt(failure_data: Dict[str, Any]) -> str:
    """Create prompt for failure analysis."""
    return f"""You are a health program coordinator explaining why certain activities couldn't be scheduled.

Analyze the following scheduling failures and provide helpful recommendations:

TOTAL FAILURES: {failure_data['total_failed']} occurrences across {failure_data['activities_affected']} activities

FAILED ACTIVITIES:
{_format_failure_list(failure_data['failures'])}

Write an analysis (2-3 paragraphs) that:
1. Identifies common patterns in failures (priority, type, constraints)
2. Explains likely root causes (conflicts, availability, capacity)
3. Suggests practical solutions (adjust times, increase specialist availability, reduce frequency)
4. Is constructive and solution-focused

Be specific and actionable."""


def _format_priority_data(by_priority: Dict[str, Any]) -> str:
    """Format priority data for prompt."""
    lines = []
    for p in ["P1", "P2", "P3", "P4", "P5"]:
        if p in by_priority:
            data = by_priority[p]
            total = data['scheduled'] + data['failed']
            lines.append(
                f"{p}: {data['scheduled']}/{total} scheduled "
                f"({data['count']} activities)"
            )
    return "\n".join(lines)


def _format_type_data(by_type: Dict[str, Any]) -> str:
    """Format type data for prompt."""
    lines = []
    for activity_type, data in sorted(by_type.items(), key=lambda x: x[1]['scheduled'], reverse=True):
        total = data['scheduled'] + data['failed']
        lines.append(
            f"{activity_type}: {data['scheduled']}/{total} scheduled "
            f"({data['count']} activities)"
        )
    return "\n".join(lines)


def _format_failure_list(failures: List[Dict[str, Any]]) -> str:
    """Format failure list for prompt."""
    lines = []
    for failure in failures:
        lines.append(
            f"- {failure['name']} (P{failure['priority']}, {failure['type']})\n"
            f"  Failed: {failure['failed_count']} occurrences\n"
            f"  Reason: {failure['reason']}\n"
            f"  Violation Types: {', '.join(failure['violation_types'].keys())}"
        )
    return "\n\n".join(lines)
