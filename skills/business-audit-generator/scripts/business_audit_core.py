#!/usr/bin/env python3
"""
Business Audit Generator - Core functionality

Implements logic that analyzes tasks, transactions, and goals to generate the weekly "Monday Morning CEO Briefing"
"""

import asyncio
import datetime
import enum
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()


class ReportPeriod(Enum):
    """Types of report periods"""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PerformanceLevel(Enum):
    """Performance levels for metrics"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Risk levels for business operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskData:
    """Data structure for task-related information"""
    id: str
    title: str
    status: str  # e.g., "completed", "in_progress", "overdue", "not_started"
    assigned_to: str
    created_date: datetime
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high, critical
    category: str = "general"
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    project_id: Optional[str] = None


@dataclass
class FinancialTransaction:
    """Data structure for financial transactions"""
    id: str
    date: datetime
    amount: float
    category: str
    vendor: str
    description: str
    transaction_type: str  # e.g., "expense", "income", "transfer"
    project_id: Optional[str] = None
    department: Optional[str] = None
    currency: str = "USD"
    approved: bool = True


@dataclass
class GoalData:
    """Data structure for goal-related information"""
    id: str
    title: str
    description: str
    target_date: datetime
    current_progress: float  # 0.0 to 1.0
    target_value: float
    current_value: float
    owner: str
    category: str = "business"
    baseline_value: float = 0.0
    milestones: List[Dict[str, Union[str, float, datetime]]] = field(default_factory=list)


@dataclass
class PerformanceMetric:
    """Performance metric with analysis"""
    name: str
    current_value: float
    target_value: float
    baseline_value: float
    period: str
    trend: str  # increasing, decreasing, stable
    performance_level: PerformanceLevel
    variance: float  # percentage difference from target
    confidence: float  # 0.0 to 1.0


@dataclass
class RiskAssessment:
    """Risk assessment for business operations"""
    risk_id: str
    name: str
    description: str
    level: RiskLevel
    probability: float  # 0.0 to 1.0
    impact: float  # 0.0 to 1.0
    mitigation_strategies: List[str]
    affected_areas: List[str]


@dataclass
class ReportSection:
    """A section of the business audit report"""
    title: str
    content: str
    data: Dict[str, Any]
    charts: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BusinessAuditReport:
    """Complete business audit report structure"""
    report_id: str
    report_date: datetime
    period: str
    summary: str
    key_accomplishments: List[str]
    concerns: List[str]
    task_analysis: Dict[str, Any]
    financial_analysis: Dict[str, Any]
    goal_progress: Dict[str, Any]
    performance_metrics: List[PerformanceMetric]
    risk_assessments: List[RiskAssessment]
    recommendations: List[str]
    trending_indicators: Dict[str, str]
    next_steps: List[str]


class DataAnalyzer:
    """Analyzes business data from various sources"""

    def __init__(self):
        self.logger = logger.bind(component="DataAnalyzer")

    def analyze_tasks(self, tasks: List[TaskData]) -> Dict[str, Any]:
        """Analyze task completion and performance metrics"""
        total_tasks = len(tasks)
        if total_tasks == 0:
            return {
                "completion_rate": 0.0,
                "total_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "trending": "neutral"
            }

        completed_tasks = [t for t in tasks if t.status == "completed"]
        overdue_tasks = [t for t in tasks if t.due_date and t.due_date < datetime.now() and t.status != "completed"]
        in_progress_tasks = [t for t in tasks if t.status == "in_progress"]

        completion_rate = len(completed_tasks) / total_tasks if total_tasks > 0 else 0.0

        # Calculate average time to complete tasks
        completion_times = []
        for task in completed_tasks:
            if task.completed_date and task.created_date:
                completion_time = (task.completed_date - task.created_date).days
                if completion_time >= 0:  # Only positive durations
                    completion_times.append(completion_time)

        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0

        # Analyze task categories
        category_breakdown = {}
        for task in tasks:
            if task.category not in category_breakdown:
                category_breakdown[task.category] = {"total": 0, "completed": 0}
            category_breakdown[task.category]["total"] += 1
            if task.status == "completed":
                category_breakdown[task.category]["completed"] += 1

        # Calculate completion rates by category
        for category in category_breakdown:
            total = category_breakdown[category]["total"]
            completed = category_breakdown[category]["completed"]
            category_breakdown[category]["completion_rate"] = completed / total if total > 0 else 0.0

        # Determine trend (simplified - in a real implementation, this would compare to previous periods)
        trending = "stable"
        if completion_rate > 0.9:
            trending = "improving"
        elif completion_rate < 0.7:
            trending = "declining"

        return {
            "completion_rate": completion_rate,
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks),
            "overdue_tasks": len(overdue_tasks),
            "in_progress_tasks": len(in_progress_tasks),
            "avg_completion_time": avg_completion_time,
            "category_breakdown": category_breakdown,
            "trending": trending
        }

    def analyze_finances(self, transactions: List[FinancialTransaction]) -> Dict[str, Any]:
        """Analyze financial transactions and spending patterns"""
        if not transactions:
            return {
                "total_spending": 0.0,
                "total_income": 0.0,
                "net_flow": 0.0,
                "budget_variance": 0.0,
                "top_categories": {},
                "trending": "neutral"
            }

        # Separate expenses and income
        expenses = [t for t in transactions if t.transaction_type == "expense" and t.amount < 0]
        income = [t for t in transactions if t.transaction_type == "income" and t.amount > 0]

        total_spending = abs(sum(t.amount for t in expenses))
        total_income = sum(t.amount for t in income)
        net_flow = total_income - total_spending

        # Category breakdown
        category_totals = {}
        for trans in expenses:
            category = trans.category
            if category not in category_totals:
                category_totals[category] = 0.0
            category_totals[category] += abs(trans.amount)

        # Sort categories by spending amount
        sorted_categories = dict(sorted(category_totals.items(), key=lambda x: x[1], reverse=True))
        top_categories = dict(list(sorted_categories.items())[:5])  # Top 5 categories

        # Department breakdown if available
        dept_totals = {}
        for trans in expenses:
            if trans.department:
                dept = trans.department
                if dept not in dept_totals:
                    dept_totals[dept] = 0.0
                dept_totals[dept] += abs(trans.amount)

        # Determine trend (simplified)
        trending = "stable"
        if len(expenses) > 0 and len(income) > 0:
            expense_vs_income = total_spending / total_income if total_income > 0 else float('inf')
            if expense_vs_income > 0.8:  # Spending more than 80% of income
                trending = "concerning"
            elif expense_vs_income < 0.5:  # Spending less than 50% of income
                trending = "efficient"

        return {
            "total_spending": total_spending,
            "total_income": total_income,
            "net_flow": net_flow,
            "top_categories": top_categories,
            "department_breakdown": dept_totals,
            "transaction_count": len(transactions),
            "expense_count": len(expenses),
            "income_count": len(income),
            "trending": trending
        }

    def analyze_goals(self, goals: List[GoalData]) -> Dict[str, Any]:
        """Analyze goal progress and achievement rates"""
        if not goals:
            return {
                "overall_progress": 0.0,
                "goals_on_track": 0,
                "goals_behind": 0,
                "goals_ahead": 0,
                "milestones_achieved": 0,
                "milestones_pending": 0,
                "trending": "neutral"
            }

        total_progress = sum(goal.current_progress for goal in goals)
        overall_progress = total_progress / len(goals) if goals else 0.0

        # Classify goals based on progress vs timeline
        now = datetime.now()
        goals_on_track = 0
        goals_behind = 0
        goals_ahead = 0

        for goal in goals:
            # Calculate expected progress based on time elapsed
            # Check if baseline_value is a datetime or numeric value
            if isinstance(goal.baseline_value, datetime) and isinstance(goal.target_date, datetime):
                if goal.target_date > goal.baseline_value:
                    time_elapsed = (now - goal.baseline_value) if isinstance(goal.baseline_value, datetime) else timedelta(0)
                    total_duration = (goal.target_date - goal.baseline_value)

                    if total_duration.total_seconds() > 0:
                        expected_progress = min(1.0, time_elapsed.total_seconds() / total_duration.total_seconds())

                        if goal.current_progress >= expected_progress:
                            if goal.current_progress >= 1.0:  # Goal completed
                                goals_ahead += 1
                            else:
                                goals_on_track += 1
                        else:
                            goals_behind += 1
                    else:
                        goals_on_track += 1  # Goal duration is 0 or negative, consider on track
                else:
                    # Simplified classification if no timeline available
                    if goal.current_progress >= 1.0:
                        goals_ahead += 1
                    elif goal.current_progress >= 0.75:
                        goals_on_track += 1
                    else:
                        goals_behind += 1
            else:
                # Simplified classification if no timeline available
                if goal.current_progress >= 1.0:
                    goals_ahead += 1
                elif goal.current_progress >= 0.75:
                    goals_on_track += 1
                else:
                    goals_behind += 1

        # Count milestones
        total_milestones = sum(len(goal.milestones) for goal in goals)
        completed_milestones = 0
        for goal in goals:
            for milestone in goal.milestones:
                if milestone.get("completed", False):
                    completed_milestones += 1

        trending = "on_track"
        if overall_progress < 0.5:
            trending = "behind_schedule"
        elif overall_progress > 0.8:
            trending = "ahead_of_schedule"

        return {
            "overall_progress": overall_progress,
            "total_goals": len(goals),
            "goals_on_track": goals_on_track,
            "goals_behind": goals_behind,
            "goals_ahead": goals_ahead,
            "milestones_achieved": completed_milestones,
            "milestones_pending": total_milestones - completed_milestones,
            "trending": trending
        }

    def calculate_performance_metrics(self, task_analysis: Dict, financial_analysis: Dict, goal_analysis: Dict) -> List[PerformanceMetric]:
        """Calculate performance metrics across all domains"""
        metrics = []

        # Task performance metric
        metrics.append(PerformanceMetric(
            name="Task Completion Rate",
            current_value=task_analysis.get("completion_rate", 0.0),
            target_value=0.85,  # Target 85% completion
            baseline_value=0.0,
            period="weekly",
            trend=task_analysis.get("trending", "stable"),
            performance_level=self._calculate_performance_level(task_analysis.get("completion_rate", 0.0), 0.85),
            variance=((task_analysis.get("completion_rate", 0.0) - 0.85) / 0.85) * 100 if 0.85 != 0 else 0,
            confidence=0.9  # High confidence in task metrics
        ))

        # Financial performance metric (efficiency ratio)
        total_income = financial_analysis.get("total_income", 1)  # Avoid division by zero
        net_flow = financial_analysis.get("net_flow", 0)
        efficiency_ratio = net_flow / total_income if total_income != 0 else 0

        metrics.append(PerformanceMetric(
            name="Financial Efficiency Ratio",
            current_value=efficiency_ratio,
            target_value=0.1,  # Target 10% positive net flow
            baseline_value=0.0,
            period="weekly",
            trend=financial_analysis.get("trending", "stable"),
            performance_level=self._calculate_performance_level(efficiency_ratio, 0.1),
            variance=((efficiency_ratio - 0.1) / 0.1) * 100 if 0.1 != 0 else 0,
            confidence=0.85
        ))

        # Goal achievement metric
        metrics.append(PerformanceMetric(
            name="Goal Achievement Rate",
            current_value=goal_analysis.get("overall_progress", 0.0),
            target_value=0.75,  # Target 75% goal progress
            baseline_value=0.0,
            period="weekly",
            trend=goal_analysis.get("trending", "stable"),
            performance_level=self._calculate_performance_level(goal_analysis.get("overall_progress", 0.0), 0.75),
            variance=((goal_analysis.get("overall_progress", 0.0) - 0.75) / 0.75) * 100 if 0.75 != 0 else 0,
            confidence=0.8
        ))

        return metrics

    def _calculate_performance_level(self, current_value: float, target_value: float) -> PerformanceLevel:
        """Calculate performance level based on current vs target value"""
        if target_value == 0:
            # Handle case where target is 0 (like variance from target)
            if abs(current_value) <= 0.05:  # Within 5%
                return PerformanceLevel.EXCELLENT
            elif abs(current_value) <= 0.1:  # Within 10%
                return PerformanceLevel.GOOD
            elif abs(current_value) <= 0.2:  # Within 20%
                return PerformanceLevel.FAIR
            else:
                return PerformanceLevel.POOR

        ratio = current_value / target_value if target_value != 0 else 0

        if ratio >= 1.0:
            return PerformanceLevel.EXCELLENT
        elif ratio >= 0.9:
            return PerformanceLevel.GOOD
        elif ratio >= 0.75:
            return PerformanceLevel.FAIR
        elif ratio >= 0.5:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL

    def identify_risks(self, task_analysis: Dict, financial_analysis: Dict, goal_analysis: Dict) -> List[RiskAssessment]:
        """Identify potential risks based on analysis"""
        risks = []

        # Task-related risks
        completion_rate = task_analysis.get("completion_rate", 0)
        if completion_rate < 0.7:  # Below 70% completion rate
            risks.append(RiskAssessment(
                risk_id="TASK_COMPLETION_LOW",
                name="Low Task Completion Rate",
                description=f"Task completion rate is {completion_rate:.2%}, below recommended 70%",
                level=RiskLevel.MEDIUM if completion_rate >= 0.5 else RiskLevel.HIGH,
                probability=0.7,
                impact=0.6,
                mitigation_strategies=[
                    "Reallocate resources to critical tasks",
                    "Review task assignments and priorities",
                    "Implement daily standups to track progress"
                ],
                affected_areas=["Operations", "Delivery", "Productivity"]
            ))

        overdue_count = task_analysis.get("overdue_tasks", 0)
        if overdue_count > 5:  # More than 5 overdue tasks
            risks.append(RiskAssessment(
                risk_id="HIGH_OVERDUE_TASKS",
                name="High Number of Overdue Tasks",
                description=f"There are {overdue_count} overdue tasks that need attention",
                level=RiskLevel.MEDIUM if overdue_count <= 10 else RiskLevel.HIGH,
                probability=0.8,
                impact=0.5,
                mitigation_strategies=[
                    "Prioritize overdue tasks",
                    "Assign additional resources",
                    "Adjust deadlines if necessary"
                ],
                affected_areas=["Delivery", "Customer Satisfaction"]
            ))

        # Financial risks
        net_flow = financial_analysis.get("net_flow", 0)
        if net_flow < 0:  # Negative cash flow
            risks.append(RiskAssessment(
                risk_id="NEGATIVE_CASH_FLOW",
                name="Negative Cash Flow",
                description=f"Weekly net flow is negative (${abs(net_flow):.2f})",
                level=RiskLevel.HIGH,
                probability=0.8,
                impact=0.9,
                mitigation_strategies=[
                    "Review and reduce discretionary spending",
                    "Accelerate accounts receivable collection",
                    "Negotiate payment terms with vendors"
                ],
                affected_areas=["Finance", "Operations", "Growth"]
            ))

        # Goal-related risks
        goals_behind = goal_analysis.get("goals_behind", 0)
        total_goals = goal_analysis.get("total_goals", 1)
        if total_goals > 0 and (goals_behind / total_goals) > 0.3:  # More than 30% of goals behind
            risks.append(RiskAssessment(
                risk_id="GOALS_BEHIND_TRACK",
                name="Goals Behind Schedule",
                description=f"{goals_behind} out of {total_goals} goals are behind schedule",
                level=RiskLevel.MEDIUM,
                probability=0.6,
                impact=0.7,
                mitigation_strategies=[
                    "Reassess goal timelines and feasibility",
                    "Allocate additional resources to critical goals",
                    "Break down large goals into smaller milestones"
                ],
                affected_areas=["Strategic Planning", "Revenue", "Product Development"]
            ))

        return risks


class ReportGenerator:
    """Generates business audit reports"""

    def __init__(self):
        self.logger = logger.bind(component="ReportGenerator")

    def generate_weekly_briefing(self,
                               tasks: List[TaskData],
                               transactions: List[FinancialTransaction],
                               goals: List[GoalData],
                               period_start: Optional[datetime] = None,
                               period_end: Optional[datetime] = None) -> BusinessAuditReport:
        """Generate the weekly CEO briefing report"""

        if period_start is None:
            # Default to last week (Monday to Sunday)
            today = datetime.now()
            days_since_monday = (today.weekday()) % 7  # Monday is 0
            period_start = today - timedelta(days=days_since_monday)
            period_end = period_start + timedelta(days=6)

        period_str = f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"

        # Analyze data
        analyzer = DataAnalyzer()

        task_analysis = analyzer.analyze_tasks(tasks)
        financial_analysis = analyzer.analyze_finances(transactions)
        goal_analysis = analyzer.analyze_goals(goals)

        performance_metrics = analyzer.calculate_performance_metrics(
            task_analysis, financial_analysis, goal_analysis
        )

        risk_assessments = analyzer.identify_risks(
            task_analysis, financial_analysis, goal_analysis
        )

        # Generate report sections
        report_sections = self._create_report_sections(
            task_analysis, financial_analysis, goal_analysis,
            performance_metrics, risk_assessments
        )

        # Generate summary
        summary = self._generate_summary(task_analysis, financial_analysis, goal_analysis, risk_assessments)

        # Identify key accomplishments and concerns
        key_accomplishments = self._identify_key_accomplishments(
            task_analysis, financial_analysis, goal_analysis
        )

        concerns = self._identify_concerns(risk_assessments)

        # Generate recommendations
        recommendations = self._generate_recommendations(performance_metrics, risk_assessments)

        # Determine trending indicators
        trending_indicators = self._analyze_trends(task_analysis, financial_analysis, goal_analysis)

        # Generate next steps
        next_steps = self._generate_next_steps(recommendations)

        report = BusinessAuditReport(
            report_id=f"CEO_BRIEFING_{period_start.strftime('%Y%m%d')}",
            report_date=datetime.now(),
            period=period_str,
            summary=summary,
            key_accomplishments=key_accomplishments,
            concerns=concerns,
            task_analysis=task_analysis,
            financial_analysis=financial_analysis,
            goal_progress=goal_analysis,
            performance_metrics=performance_metrics,
            risk_assessments=risk_assessments,
            recommendations=recommendations,
            trending_indicators=trending_indicators,
            next_steps=next_steps
        )

        self.logger.info("Weekly briefing generated", report_id=report.report_id)
        return report

    def _create_report_sections(self, task_analysis: Dict, financial_analysis: Dict,
                              goal_analysis: Dict, performance_metrics: List[PerformanceMetric],
                              risk_assessments: List[RiskAssessment]) -> List[ReportSection]:
        """Create structured report sections"""
        sections = []

        # Task Analysis Section
        task_content = f"""
Task Performance Summary:
- Completion Rate: {task_analysis['completion_rate']:.2%}
- Total Tasks: {task_analysis['total_tasks']}
- Completed: {task_analysis['completed_tasks']}
- Overdue: {task_analysis['overdue_tasks']}
- Trend: {task_analysis['trending']}
        """.strip()

        task_section = ReportSection(
            title="Task Performance Analysis",
            content=task_content,
            data=task_analysis,
            recommendations=[]
        )
        sections.append(task_section)

        # Financial Analysis Section
        fin_content = f"""
Financial Performance Summary:
- Total Spending: ${financial_analysis['total_spending']:,.2f}
- Total Income: ${financial_analysis['total_income']:,.2f}
- Net Flow: ${financial_analysis['net_flow']:,.2f}
- Top Expense Categories: {', '.join(financial_analysis['top_categories'].keys())}
- Trend: {financial_analysis['trending']}
        """.strip()

        fin_section = ReportSection(
            title="Financial Performance Analysis",
            content=fin_content,
            data=financial_analysis,
            recommendations=[]
        )
        sections.append(fin_section)

        # Goal Progress Section
        goal_content = f"""
Goal Achievement Summary:
- Overall Progress: {goal_analysis['overall_progress']:.2%}
- Goals On Track: {goal_analysis['goals_on_track']}
- Goals Behind: {goal_analysis['goals_behind']}
- Goals Ahead: {goal_analysis['goals_ahead']}
- Milestones Achieved: {goal_analysis['milestones_achieved']}
- Trend: {goal_analysis['trending']}
        """.strip()

        goal_section = ReportSection(
            title="Goal Progress Analysis",
            content=goal_content,
            data=goal_analysis,
            recommendations=[]
        )
        sections.append(goal_section)

        return sections

    def _generate_summary(self, task_analysis: Dict, financial_analysis: Dict,
                         goal_analysis: Dict, risk_assessments: List[RiskAssessment]) -> str:
        """Generate an executive summary"""
        overall_sentiment = "positive"

        # Determine sentiment based on key metrics
        completion_rate = task_analysis.get("completion_rate", 0)
        net_flow = financial_analysis.get("net_flow", 0)
        goal_progress = goal_analysis.get("overall_progress", 0)

        if completion_rate < 0.7 or net_flow < 0 or goal_progress < 0.6:
            overall_sentiment = "challenging"
        elif completion_rate < 0.85 or goal_progress < 0.75:
            overall_sentiment = "mixed"

        risk_level = "low"
        if len([r for r in risk_assessments if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]) > 0:
            risk_level = "high"
        elif len([r for r in risk_assessments if r.level == RiskLevel.MEDIUM]) > 0:
            risk_level = "medium"

        return f"""
This week's business performance shows a {overall_sentiment} trajectory with {risk_level} risk exposure.
Task completion stands at {completion_rate:.2%}, financial position shows a net {'surplus' if net_flow >= 0 else 'deficit'} of ${abs(net_flow):,.2f},
and overall goal progress sits at {goal_progress:.2%}. We've identified {len(risk_assessments)} potential risks requiring management attention.
        """.strip()

    def _identify_key_accomplishments(self, task_analysis: Dict, financial_analysis: Dict,
                                   goal_analysis: Dict) -> List[str]:
        """Identify key accomplishments for the report"""
        accomplishments = []

        completion_rate = task_analysis.get("completion_rate", 0)
        if completion_rate >= 0.9:
            accomplishments.append(f"Exceptional task completion rate of {completion_rate:.2%}")

        if goal_analysis.get("goals_ahead", 0) > 0:
            accomplishments.append(f"Achieved {goal_analysis['goals_ahead']} goals ahead of schedule")

        net_flow = financial_analysis.get("net_flow", 0)
        if net_flow > 0:
            accomplishments.append(f"Maintained positive cash flow of ${net_flow:,.2f}")

        if goal_analysis.get("milestones_achieved", 0) > 5:
            accomplishments.append(f"Achieved {goal_analysis['milestones_achieved']} key milestones")

        if not accomplishments:
            accomplishments.append("Maintained steady operations across all business units")

        return accomplishments

    def _identify_concerns(self, risk_assessments: List[RiskAssessment]) -> List[str]:
        """Identify concerns based on risk assessments"""
        concerns = []

        for risk in risk_assessments:
            if risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                concerns.append(f"{risk.name}: {risk.description}")

        if not concerns:
            # Even if no high risks, report medium risks
            for risk in risk_assessments:
                if risk.level == RiskLevel.MEDIUM:
                    concerns.append(f"{risk.name}: {risk.description}")

        if not concerns:
            concerns.append("No significant concerns identified this period")

        return concerns

    def _generate_recommendations(self, performance_metrics: List[PerformanceMetric],
                                risk_assessments: List[RiskAssessment]) -> List[str]:
        """Generate recommendations based on metrics and risks"""
        recommendations = []

        # Recommendations based on performance metrics
        for metric in performance_metrics:
            if metric.performance_level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                if "Task Completion" in metric.name:
                    recommendations.append("Focus on improving task completion rates through better resource allocation")
                elif "Financial Efficiency" in metric.name:
                    recommendations.append("Review spending patterns to improve financial efficiency")
                elif "Goal Achievement" in metric.name:
                    recommendations.append("Implement more frequent goal progress reviews to stay on track")

        # Recommendations based on risks
        for risk in risk_assessments:
            recommendations.extend(risk.mitigation_strategies)

        # Remove duplicates while preserving order
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)

        return unique_recs[:5]  # Limit to top 5 recommendations

    def _analyze_trends(self, task_analysis: Dict, financial_analysis: Dict,
                       goal_analysis: Dict) -> Dict[str, str]:
        """Analyze trends across different business areas"""
        trends = {}

        trends["tasks"] = task_analysis.get("trending", "neutral")
        trends["finance"] = financial_analysis.get("trending", "neutral")
        trends["goals"] = goal_analysis.get("trending", "neutral")

        # Overall trend
        trend_scores = {
            "improving": 2,
            "on_track": 1,
            "stable": 0,
            "neutral": 0,
            "declining": -1,
            "behind_schedule": -1,
            "ahead_of_schedule": 1,
            "concerning": -2,
            "efficient": 1
        }

        avg_score = (
            trend_scores.get(trends["tasks"], 0) +
            trend_scores.get(trends["finance"], 0) +
            trend_scores.get(trends["goals"], 0)
        ) / 3

        if avg_score >= 1:
            overall_trend = "improving"
        elif avg_score >= 0:
            overall_trend = "stable"
        else:
            overall_trend = "declining"

        trends["overall"] = overall_trend
        return trends

    def _generate_next_steps(self, recommendations: List[str]) -> List[str]:
        """Generate next steps based on recommendations"""
        # Take the first few recommendations as next steps
        next_steps = recommendations[:3] if recommendations else []

        if not next_steps:
            next_steps = [
                "Continue current business operations",
                "Monitor key metrics closely",
                "Prepare for next reporting period"
            ]

        return next_steps


class BusinessAuditGenerator:
    """Main class for generating business audit reports"""

    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.report_generator = ReportGenerator()
        self.logger = logger.bind(component="BusinessAuditGenerator")

    def generate_weekly_briefing(self,
                               tasks: List[TaskData] = None,
                               transactions: List[FinancialTransaction] = None,
                               goals: List[GoalData] = None,
                               period_start: Optional[datetime] = None,
                               period_end: Optional[datetime] = None) -> BusinessAuditReport:
        """Generate the weekly CEO briefing report"""

        # Use empty lists if None provided
        tasks = tasks or []
        transactions = transactions or []
        goals = goals or []

        report = self.report_generator.generate_weekly_briefing(
            tasks, transactions, goals, period_start, period_end
        )

        self.logger.info("Weekly briefing generated successfully", report_id=report.report_id)
        return report

    def analyze_data_sets(self, tasks: List[TaskData] = None, finances: List[FinancialTransaction] = None,
                         goals: List[GoalData] = None) -> Dict[str, Any]:
        """Analyze specific data sets without generating full report"""
        analyzer = DataAnalyzer()

        tasks = tasks or []
        finances = finances or []
        goals = goals or []

        analysis_results = {
            "tasks": analyzer.analyze_tasks(tasks),
            "finances": analyzer.analyze_finances(finances),
            "goals": analyzer.analyze_goals(goals),
            "timestamp": datetime.now().isoformat()
        }

        self.logger.info("Data analysis completed", analysis_timestamp=analysis_results["timestamp"])
        return analysis_results

    def generate_custom_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate a custom report from analysis data"""
        # Extract components from analysis data
        task_analysis = analysis_data.get("tasks", {})
        financial_analysis = analysis_data.get("finances", {})
        goal_analysis = analysis_data.get("goals", {})

        # Create a simple formatted report
        report_parts = [
            "# Business Analysis Report",
            f"Generated: {analysis_data.get('timestamp', datetime.now().isoformat())}",
            "",
            "## Task Analysis",
            f"- Completion Rate: {task_analysis.get('completion_rate', 0):.2%}",
            f"- Total Tasks: {task_analysis.get('total_tasks', 0)}",
            f"- Completed: {task_analysis.get('completed_tasks', 0)}",
            f"- Overdue: {task_analysis.get('overdue_tasks', 0)}",
            "",
            "## Financial Analysis",
            f"- Total Spending: ${financial_analysis.get('total_spending', 0):,.2f}",
            f"- Total Income: ${financial_analysis.get('total_income', 0):,.2f}",
            f"- Net Flow: ${financial_analysis.get('net_flow', 0):,.2f}",
            "",
            "## Goal Progress",
            f"- Overall Progress: {goal_analysis.get('overall_progress', 0):.2%}",
            f"- Total Goals: {goal_analysis.get('total_goals', 0)}",
            f"- On Track: {goal_analysis.get('goals_on_track', 0)}",
            f"- Behind: {goal_analysis.get('goals_behind', 0)}"
        ]

        return "\n".join(report_parts)


# Convenience functions
def create_sample_tasks(count: int = 10) -> List[TaskData]:
    """Create sample task data for testing"""
    import random
    from datetime import timedelta

    statuses = ["completed", "in_progress", "overdue", "not_started"]
    categories = ["Development", "Marketing", "Operations", "Sales", "Research"]
    priorities = ["low", "medium", "high"]

    tasks = []
    for i in range(count):
        due_date = datetime.now() + timedelta(days=random.randint(-5, 10))
        completed_date = None
        if random.choice([True, False]):  # 50% chance of being completed
            if random.choice([True, False]):  # If completed, 50% chance of being overdue
                completed_date = due_date + timedelta(days=random.randint(1, 3))
            else:
                completed_date = due_date - timedelta(days=random.randint(0, 2))

        tasks.append(TaskData(
            id=f"task_{i}",
            title=f"Sample Task {i}",
            status=random.choice(statuses),
            assigned_to=f"user_{random.randint(1, 5)}",
            created_date=datetime.now() - timedelta(days=random.randint(1, 20)),
            due_date=due_date,
            completed_date=completed_date,
            priority=random.choice(priorities),
            category=random.choice(categories),
            estimated_hours=random.randint(1, 16) if random.choice([True, False]) else None,
            actual_hours=random.randint(1, 20) if completed_date else None
        ))

    return tasks


def create_sample_transactions(count: int = 15) -> List[FinancialTransaction]:
    """Create sample transaction data for testing"""
    import random
    from datetime import timedelta

    categories = ["Marketing", "Operations", "Travel", "Equipment", "Software", "Consulting"]
    departments = ["Engineering", "Sales", "Marketing", "HR", "Operations"]
    vendors = ["Vendor A", "Vendor B", "Vendor C", "Vendor D", "Vendor E"]

    transactions = []
    for i in range(count):
        is_expense = random.choice([True, False])
        amount = random.uniform(100, 5000) * (-1 if is_expense else 1)

        transactions.append(FinancialTransaction(
            id=f"trans_{i}",
            date=datetime.now() - timedelta(days=random.randint(0, 14)),
            amount=amount,
            category=random.choice(categories),
            vendor=random.choice(vendors),
            description=f"Sample transaction {i}",
            transaction_type="expense" if is_expense else "income",
            department=random.choice(departments) if random.choice([True, False]) else None,
            project_id=f"proj_{random.randint(1, 5)}" if random.choice([True, False]) else None
        ))

    return transactions


def create_sample_goals(count: int = 5) -> List[GoalData]:
    """Create sample goal data for testing"""
    import random
    from datetime import timedelta

    categories = ["Revenue", "Customer Acquisition", "Product", "Team", "Market"]
    owners = ["Alice", "Bob", "Charlie", "Diana", "Eve"]

    goals = []
    for i in range(count):
        target_value = random.uniform(100, 1000)
        current_value = random.uniform(0, target_value)

        goals.append(GoalData(
            id=f"goal_{i}",
            title=f"Sample Goal {i}",
            description=f"Description for goal {i}",
            target_date=datetime.now() + timedelta(days=random.randint(30, 180)),
            current_progress=current_value / target_value if target_value > 0 else 0,
            target_value=target_value,
            current_value=current_value,
            owner=random.choice(owners),
            category=random.choice(categories),
            baseline_value=random.uniform(0, target_value * 0.3)
        ))

    return goals


def demo_business_audit():
    """Demo function to show business audit generator usage"""
    print("Business Audit Generator Demo")
    print("=" * 40)

    # Create sample data
    print("Creating sample data...")
    tasks = create_sample_tasks(20)
    transactions = create_sample_transactions(30)
    goals = create_sample_goals(8)

    print(f"Created {len(tasks)} tasks, {len(transactions)} transactions, {len(goals)} goals")

    # Create generator and run analysis
    generator = BusinessAuditGenerator()

    print("\nGenerating weekly briefing...")
    report = generator.generate_weekly_briefing(tasks, transactions, goals)

    print(f"\nReport ID: {report.report_id}")
    print(f"Period: {report.period}")
    print(f"Summary: {report.summary}")
    print(f"\nKey Accomplishments: {len(report.key_accomplishments)}")
    for acc in report.key_accomplishments:
        print(f"  - {acc}")

    print(f"\nConcerns: {len(report.concerns)}")
    for con in report.concerns:
        print(f"  - {con}")

    print(f"\nRecommendations: {len(report.recommendations)}")
    for rec in report.recommendations[:3]:  # Show first 3
        print(f"  - {rec}")

    print(f"\nTrending: {report.trending_indicators}")
    print(f"Next Steps: {len(report.next_steps)}")
    for step in report.next_steps:
        print(f"  - {step}")


if __name__ == "__main__":
    demo_business_audit()