"""Metrics calculation for schedule evaluation."""

from typing import List, Dict
from collections import defaultdict

from models import Activity
from scheduler import SchedulerState


class MetricsCalculator:
    """Calculate scheduling metrics and statistics."""

    def __init__(self, activities: List[Activity], state: SchedulerState):
        """Initialize metrics calculator.

        Args:
            activities: List of all activities
            state: Scheduler state with booked slots and failures
        """
        self.activities = activities
        self.state = state

    def calculate_success_rate(self, required_occurrences: Dict[str, int]) -> Dict:
        """Calculate overall and per-priority success rates.

        Args:
            required_occurrences: Dict mapping activity_id to required occurrence count

        Returns:
            Dict with success rate metrics
        """
        total_required = sum(required_occurrences.values())
        total_scheduled = len(self.state.booked_slots)

        # Calculate by priority
        priority_metrics = {}
        for priority in range(1, 6):
            priority_activities = [a for a in self.activities if a.priority == priority]
            required = sum(required_occurrences.get(a.id, 0) for a in priority_activities)
            scheduled = sum(self.state.get_occurrence_count(a.id) for a in priority_activities)

            priority_metrics[f"priority_{priority}"] = {
                "required": required,
                "scheduled": scheduled,
                "success_rate": (scheduled / required * 100) if required > 0 else 0
            }

        return {
            "overall": {
                "total_required": total_required,
                "total_scheduled": total_scheduled,
                "success_rate": (total_scheduled / total_required * 100) if total_required > 0 else 0
            },
            "by_priority": priority_metrics
        }

    def calculate_constraint_utilization(self, specialists: List, equipment: List) -> Dict:
        """Calculate how much constraints were utilized.

        Args:
            specialists: List of all specialists
            equipment: List of all equipment

        Returns:
            Dict with utilization metrics
        """
        stats = self.state.get_statistics()

        # Specialist utilization
        specialist_util = {}
        for spec in specialists:
            usage_count = stats["specialist_usage"].get(spec.id, 0)
            # Estimate max possible bookings (simplified: 40 hours/week * 12 weeks / 1 hour avg)
            max_possible = 480  # Rough estimate
            specialist_util[spec.id] = {
                "name": spec.name,
                "bookings": usage_count,
                "utilization_estimate": min(100, (usage_count / max_possible * 100))
            }

        # Equipment utilization
        equipment_util = {}
        for equip in equipment:
            usage_count = stats["equipment_usage"].get(equip.id, 0)
            # Estimate max possible uses (simplified: available most days)
            max_possible = 270  # 90 days * 3 uses per day
            equipment_util[equip.id] = {
                "name": equip.name,
                "uses": usage_count,
                "utilization_estimate": min(100, (usage_count / max_possible * 100))
            }

        return {
            "specialists": specialist_util,
            "equipment": equipment_util
        }

    def calculate_activity_distribution(self) -> Dict:
        """Calculate distribution of scheduled activities by type and time.

        Returns:
            Dict with distribution metrics
        """
        # By activity type
        type_distribution = defaultdict(int)
        for slot in self.state.booked_slots:
            activity = next((a for a in self.activities if a.id == slot.activity_id), None)
            if activity:
                type_distribution[activity.type.value] += 1

        # By time of day
        time_distribution = {
            "morning (6-12)": 0,
            "afternoon (12-17)": 0,
            "evening (17-21)": 0,
            "other": 0
        }

        for slot in self.state.booked_slots:
            hour = slot.start_time.hour
            if 6 <= hour < 12:
                time_distribution["morning (6-12)"] += 1
            elif 12 <= hour < 17:
                time_distribution["afternoon (12-17)"] += 1
            elif 17 <= hour < 21:
                time_distribution["evening (17-21)"] += 1
            else:
                time_distribution["other"] += 1

        # By day of week
        day_distribution = defaultdict(int)
        for slot in self.state.booked_slots:
            day_name = slot.date.strftime("%A")
            day_distribution[day_name] += 1

        return {
            "by_type": dict(type_distribution),
            "by_time_of_day": time_distribution,
            "by_day_of_week": dict(day_distribution)
        }

    def calculate_failure_analysis(self) -> Dict:
        """Analyze why activities failed to schedule.

        Returns:
            Dict with failure analysis
        """
        failure_report = self.state.get_failure_report()

        # Count by constraint type
        constraint_violations = defaultdict(int)
        for record in failure_report:
            for constraint_type, count in record["violation_types"].items():
                constraint_violations[constraint_type] += count

        # Group by priority
        failures_by_priority = defaultdict(list)
        for record in failure_report:
            failures_by_priority[record["priority"]].append({
                "activity_id": record["activity_id"],
                "activity_name": record["activity_name"],
                "attempts": record["attempts"]
            })

        return {
            "total_failed_activities": len(failure_report),
            "constraint_violations": dict(constraint_violations),
            "failures_by_priority": dict(failures_by_priority),
            "most_common_issue": max(constraint_violations.items(), key=lambda x: x[1])[0] if constraint_violations else None
        }

    def generate_full_report(self, required_occurrences: Dict[str, int], specialists: List, equipment: List) -> Dict:
        """Generate comprehensive metrics report.

        Args:
            required_occurrences: Dict mapping activity_id to required occurrence count
            specialists: List of all specialists
            equipment: List of all equipment

        Returns:
            Complete metrics report
        """
        return {
            "success_metrics": self.calculate_success_rate(required_occurrences),
            "utilization": self.calculate_constraint_utilization(specialists, equipment),
            "distribution": self.calculate_activity_distribution(),
            "failure_analysis": self.calculate_failure_analysis(),
            "schedule_stats": self.state.get_statistics()
        }
