#!/usr/bin/env python3
"""Flask web application for health activity scheduler."""

import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, send_from_directory
from datetime import datetime, date as date_type

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_json

app = Flask(__name__)

# Configure paths
OUTPUT_DIR = Path("output/results")
DATA_DIR = Path("data/generated")


@app.route("/")
def index():
    """Render main dashboard."""
    return render_template("index.html")


@app.route("/api/summary")
def get_summary():
    """Get schedule summary and metrics."""
    try:
        metrics = load_json(OUTPUT_DIR / "metrics.json")
        metadata = load_json(DATA_DIR / "metadata.json")

        # Extract key stats
        success_metrics = metrics.get("success_metrics", {})
        overall = success_metrics.get("overall", {})
        by_priority = success_metrics.get("by_priority", {})
        by_type = success_metrics.get("by_type", {})

        return jsonify({
            "success": True,
            "data": {
                "overall_success_rate": overall.get("success_rate", 0),
                "total_scheduled": overall.get("scheduled", 0),
                "total_required": overall.get("required", 0),
                "period": {
                    "start": metadata.get("start_date"),
                    "end": metadata.get("end_date"),
                    "duration_days": 90
                },
                "by_priority": by_priority,
                "by_type": by_type,
                "generation_cost": metadata.get("total_cost_usd", 0)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/schedule")
def get_schedule():
    """Get full schedule data."""
    try:
        schedule = load_json(OUTPUT_DIR / "schedule.json")
        activities = load_json(DATA_DIR / "activities.json")

        # Create activity lookup
        activity_map = {a["id"]: a for a in activities}

        # Enrich schedule with activity details
        enriched_schedule = []
        for slot in schedule:
            activity = activity_map.get(slot["activity_id"], {})
            enriched_schedule.append({
                **slot,
                "activity_name": activity.get("name", "Unknown"),
                "activity_type": activity.get("type", "Unknown"),
                "priority": activity.get("priority", 5)
            })

        return jsonify({
            "success": True,
            "data": enriched_schedule
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/schedule/day/<date>")
def get_day_schedule(date):
    """Get schedule for a specific day."""
    try:
        schedule = load_json(OUTPUT_DIR / "schedule.json")
        activities = load_json(DATA_DIR / "activities.json")

        # Create activity lookup
        activity_map = {a["id"]: a for a in activities}

        # Filter by date and enrich
        day_schedule = []
        for slot in schedule:
            if slot["date"] == date:
                activity = activity_map.get(slot["activity_id"], {})
                day_schedule.append({
                    **slot,
                    "activity_name": activity.get("name", "Unknown"),
                    "activity_type": activity.get("type", "Unknown"),
                    "priority": activity.get("priority", 5),
                    "details": activity.get("details", "")
                })

        # Sort by start time
        day_schedule.sort(key=lambda x: x["start_time"])

        return jsonify({
            "success": True,
            "data": day_schedule
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/calendar/<year>/<month>")
def get_month_calendar(year, month):
    """Get calendar data for a specific month."""
    try:
        schedule = load_json(OUTPUT_DIR / "schedule.json")

        # Filter by year/month
        year, month = int(year), int(month)
        month_schedule = {}

        for slot in schedule:
            slot_date = datetime.fromisoformat(slot["date"]).date()
            if slot_date.year == year and slot_date.month == month:
                date_key = slot["date"]
                if date_key not in month_schedule:
                    month_schedule[date_key] = []
                month_schedule[date_key].append(slot)

        # Calculate stats per day
        calendar_data = {}
        for date_key, slots in month_schedule.items():
            calendar_data[date_key] = {
                "count": len(slots),
                "has_priority_1": any(s.get("priority", 5) == 1 for s in slots),
                "types": list(set(s.get("activity_type", "Unknown") for s in slots))
            }

        return jsonify({
            "success": True,
            "data": calendar_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/failures")
def get_failures():
    """Get failed activities analysis."""
    try:
        failures = load_json(OUTPUT_DIR / "failures.json")

        return jsonify({
            "success": True,
            "data": failures
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/activities")
def get_activities():
    """Get all activities."""
    try:
        activities = load_json(DATA_DIR / "activities.json")

        return jsonify({
            "success": True,
            "data": activities
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 80)
    print("HEALTH ACTIVITY SCHEDULER - WEB INTERFACE")
    print("=" * 80)
    print()
    print("Starting Flask server...")
    print("Open your browser to: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()

    app.run(debug=True, host="0.0.0.0", port=5000)
