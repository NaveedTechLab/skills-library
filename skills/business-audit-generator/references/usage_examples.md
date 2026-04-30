# Business Audit Generator - Usage Examples

## Overview
This document provides practical examples of how to use the Business Audit Generator skill to analyze tasks, transactions, and goals to generate the weekly "Monday Morning CEO Briefing".

## Installation and Setup

### Prerequisites
```bash
pip install pandas numpy matplotlib scikit-learn scipy jinja2 structlog
```

### Basic Initialization
```python
from business_audit_generator.scripts.business_audit_core import BusinessAuditGenerator
from business_audit_generator.scripts.data_analyzer import AdvancedDataAnalyzer
from business_audit_generator.scripts.report_generator import ReportGenerator
from business_audit_generator.scripts.config_manager import get_config_manager

# Create a business audit generator
generator = BusinessAuditGenerator()

# Create a data analyzer
analyzer = AdvancedDataAnalyzer()

# Create a report generator
report_gen = ReportGenerator()

# Get configuration manager
config_manager = get_config_manager()
```

## Basic Usage Examples

### Simple Report Generation
```python
# Create sample data
from business_audit_generator.scripts.business_audit_core import (
    TaskData, FinancialTransaction, GoalData
)
from datetime import datetime, timedelta

# Create sample tasks
tasks = [
    TaskData(
        id="task_1",
        title="Q1 Product Launch",
        status="completed",
        assigned_to="Alice",
        created_date=datetime.now() - timedelta(days=10),
        due_date=datetime.now() - timedelta(days=2),
        completed_date=datetime.now() - timedelta(days=1),
        priority="high",
        category="Product"
    ),
    # Add more tasks as needed
]

# Create sample transactions
transactions = [
    FinancialTransaction(
        id="trans_1",
        date=datetime.now() - timedelta(days=5),
        amount=-5000.00,
        category="Marketing",
        vendor="Marketing Agency",
        description="Q1 Campaign",
        transaction_type="expense"
    ),
    # Add more transactions as needed
]

# Create sample goals
goals = [
    GoalData(
        id="goal_1",
        title="Revenue Target",
        description="Achieve $1M revenue",
        target_date=datetime.now() + timedelta(days=60),
        current_progress=0.75,
        target_value=1000000.0,
        current_value=750000.0,
        owner="Finance Team",
        category="Revenue"
    ),
    # Add more goals as needed
]

# Generate the weekly CEO briefing
report = generator.generate_weekly_briefing(tasks, transactions, goals)
print(f"Report generated: {report.report_id}")
```

## Advanced Data Analysis Examples

### Using the Advanced Data Analyzer
```python
from business_audit_generator.scripts.data_analyzer import AdvancedDataAnalyzer

analyzer = AdvancedDataAnalyzer()

# Analyze a complete dataset
analysis_results = analyzer.analyze_complete_dataset(
    [task.__dict__ for task in tasks],
    [trans.__dict__ for trans in transactions],
    [goal.__dict__ for goal in goals]
)

print(f"Data Quality Score: {analysis_results['summary']['quality_score']:.2f}")
print(f"Anomalies Found: {analysis_results['summary']['anomaly_count']}")

# Access specific analysis results
task_anomalies = analysis_results['anomalies']['tasks']
financial_trends = analysis_results['trends']['financial']
goal_correlations = analysis_results['correlations']['correlated_pairs']

for anomaly in task_anomalies[:3]:  # Show first 3 anomalies
    print(f"Task Anomaly: {anomaly['anomaly_type']} - {anomaly['severity']}")
```

### Custom Data Analysis
```python
# Perform custom analysis using individual analyzers
from business_audit_generator.scripts.data_analyzer import (
    DataValidator, AnomalyDetector, TrendAnalyzer, CorrelationAnalyzer
)

validator = DataValidator()
anomaly_detector = AnomalyDetector()
trend_analyzer = TrendAnalyzer()
correlation_analyzer = CorrelationAnalyzer()

# Validate data quality
task_quality = validator.validate_task_data([task.__dict__ for task in tasks])
print(f"Task Data Quality: {task_quality.overall_score:.2f}")

# Detect anomalies
import pandas as pd
tasks_df = pd.DataFrame([task.__dict__ for task in tasks])
anomalies = anomaly_detector.detect_task_anomalies(tasks_df)
print(f"Task Anomalies: {len(anomalies)}")

# Analyze trends
trends = trend_analyzer.analyze_task_trends(tasks_df)
print(f"Task Trend: {trends.trend_direction} (strength: {trends.trend_strength:.2f})")
```

## Report Generation Examples

### Generating Different Report Formats
```python
from business_audit_generator.scripts.report_generator import ReportGenerator

report_gen = ReportGenerator()

# Generate report with multiple output formats
result = report_gen.generate_and_distribute_weekly_briefing(
    [task.__dict__ for task in tasks],
    [trans.__dict__ for trans in transactions],
    [goal.__dict__ for goal in goals],
    distribution_list=['ceo@company.com', 'executive-team@company.com'],
    output_formats=['html', 'email', 'pdf']
)

print(f"Reports generated: {list(result['formatted_reports'].keys())}")
for fmt, path in result['formatted_reports'].items():
    print(f"  {fmt}: {path}")
```

### Custom Report Formatting
```python
# Generate just the report without distribution
report = report_gen.generate_weekly_ceo_briefing(
    [task.__dict__ for task in tasks],
    [trans.__dict__ for trans in transactions],
    [goal.__dict__ for goal in goals]
)

# Format in specific formats
formatted_reports = report_gen.format_report(
    report,
    output_formats=['html', 'email']
)

print("Custom formatted reports generated")
```

### Creating Executive Dashboards
```python
from business_audit_generator.scripts.report_generator import ExecutiveDashboard

dashboard = ExecutiveDashboard()

# Create dashboard data from report
dashboard_data = dashboard.create_dashboard_data(report)

# Display summary cards
print("Executive Dashboard Summary:")
for card in dashboard_data['summary_cards']:
    print(f"  {card['title']}: {card['value']} ({card['trend']})")

# Display risk assessment
risk_data = dashboard_data['risk_assessment']
print(f"\nRisk Assessment:")
print(f"  High Risk Items: {risk_data['high_risk_items']}")
print(f"  Medium Risk Items: {risk_data['medium_risk_items']}")
print(f"  Low Risk Items: {risk_data['low_risk_items']}")
```

## Configuration Examples

### Loading Custom Configuration
```python
from business_audit_generator.scripts.config_manager import ConfigManager

# Load custom configuration
config_manager = ConfigManager("./custom_config.json")
custom_config = config_manager.config

# Access specific configuration sections
analysis_config = config_manager.get_analysis_config()
reporting_config = config_manager.get_reporting_config()
metric_config = config_manager.get_metric_thresholds_config()

print(f"Task completion threshold: {metric_config.task_completion_threshold}")
print(f"Report frequency: {reporting_config.report_frequency.value}")
print(f"Output formats: {reporting_config.output_formats}")
```

### Modifying Configuration Programmatically
```python
# Update configuration programmatically
config_manager.update_config(
    task_completion_threshold=0.85,
    financial_variance_threshold=0.05,
    goal_progress_threshold=0.80
)

# Save updated configuration
config_manager.save_config()

print("Configuration updated and saved")
```

## Integration Examples

### Integration with Data Sources
```python
# Example of integrating with external data sources
import requests
from datetime import datetime, timedelta

def fetch_task_data_from_api(api_url: str, auth_token: str) -> list:
    """Fetch task data from an external task management system"""
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{api_url}/tasks", headers=headers)
    response.raise_for_status()

    tasks_data = response.json()

    # Convert API response to TaskData objects
    tasks = []
    for task_data in tasks_data:
        task = TaskData(
            id=task_data['id'],
            title=task_data['title'],
            status=task_data['status'],
            assigned_to=task_data['assignee'],
            created_date=datetime.fromisoformat(task_data['created_date']),
            due_date=datetime.fromisoformat(task_data['due_date']) if task_data.get('due_date') else None,
            completed_date=datetime.fromisoformat(task_data['completed_date']) if task_data.get('completed_date') else None,
            priority=task_data.get('priority', 'medium'),
            category=task_data.get('category', 'general')
        )
        tasks.append(task)

    return tasks

def fetch_financial_data_from_api(api_url: str, auth_token: str) -> list:
    """Fetch financial data from an external financial system"""
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{api_url}/transactions", headers=headers)
    response.raise_for_status()

    transactions_data = response.json()

    # Convert API response to FinancialTransaction objects
    transactions = []
    for trans_data in transactions_data:
        transaction = FinancialTransaction(
            id=trans_data['id'],
            date=datetime.fromisoformat(trans_data['date']),
            amount=trans_data['amount'],
            category=trans_data['category'],
            vendor=trans_data['vendor'],
            description=trans_data['description'],
            transaction_type=trans_data['type']
        )
        transactions.append(transaction)

    return transactions

def fetch_goal_data_from_api(api_url: str, auth_token: str) -> list:
    """Fetch goal data from an external goal tracking system"""
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{api_url}/goals", headers=headers)
    response.raise_for_status()

    goals_data = response.json()

    # Convert API response to GoalData objects
    goals = []
    for goal_data in goals_data:
        goal = GoalData(
            id=goal_data['id'],
            title=goal_data['title'],
            description=goal_data['description'],
            target_date=datetime.fromisoformat(goal_data['target_date']),
            current_progress=goal_data['current_progress'],
            target_value=goal_data['target_value'],
            current_value=goal_data['current_value'],
            owner=goal_data['owner'],
            category=goal_data.get('category', 'business')
        )
        goals.append(goal)

    return goals
```

### Integration with Claude Code Workflows
```python
def generate_claude_business_insights():
    """Example of integrating business audit generation with Claude Code workflows"""

    # Fetch data from various systems
    tasks = fetch_task_data_from_api("https://api.taskmanager.com", "your_token")
    transactions = fetch_financial_data_from_api("https://api.accounting.com", "your_token")
    goals = fetch_goal_data_from_api("https://api.goalsystem.com", "your_token")

    # Generate business audit report
    generator = BusinessAuditGenerator()
    report = generator.generate_weekly_briefing(tasks, transactions, goals)

    # Perform advanced analysis
    analyzer = AdvancedDataAnalyzer()
    analysis = analyzer.analyze_complete_dataset(
        [t.__dict__ for t in tasks],
        [f.__dict__ for f in transactions],
        [g.__dict__ for g in goals]
    )

    # Generate insights
    insights = {
        "executive_summary": report.summary,
        "key_accomplishments": report.key_accomplishments,
        "areas_of_concern": report.concerns,
        "recommendations": report.recommendations,
        "data_quality": analysis["data_quality"],
        "anomalies": analysis["anomalies"],
        "trends": analysis["trends"]
    }

    return insights
```

## Scheduling Examples

### Integration with Scheduler
```python
# Example of integrating with the scheduler-cron-integration skill
from scheduler_cron_integration.scripts.job_manager import create_job_manager

def generate_weekly_briefing_task():
    """Task function for generating weekly briefings"""
    # Fetch current data
    tasks = fetch_task_data_from_api("https://api.taskmanager.com", "your_token")
    transactions = fetch_financial_data_from_api("https://api.accounting.com", "your_token")
    goals = fetch_goal_data_from_api("https://api.goalsystem.com", "your_token")

    # Generate report
    generator = BusinessAuditGenerator()
    report = generator.generate_weekly_briefing(tasks, transactions, goals)

    # Format and distribute
    report_gen = ReportGenerator()
    result = report_gen.generate_and_distribute_weekly_briefing(
        [t.__dict__ for t in tasks],
        [f.__dict__ for f in transactions],
        [g.__dict__ for g in goals],
        distribution_list=['ceo@company.com', 'executive-team@company.com'],
        output_formats=['html', 'email']
    )

    print(f"Weekly briefing generated: {result['report_id']}")
    return result

# Schedule the weekly briefing
job_manager = create_job_manager()
job_manager.create_job(
    job_id="weekly_ceo_briefing",
    name="Weekly CEO Briefing",
    cron_expression="0 8 * * 1",  # Every Monday at 8 AM
    callback=generate_weekly_briefing_task,
    description="Generate and distribute weekly CEO briefing"
)

print("Weekly briefing scheduled successfully")
```

## Error Handling Examples

### Comprehensive Error Handling
```python
def robust_report_generation():
    """Example of robust error handling for report generation"""
    try:
        # Fetch data with error handling
        try:
            tasks = fetch_task_data_from_api("https://api.taskmanager.com", "your_token")
        except Exception as e:
            print(f"Error fetching task data: {e}")
            tasks = []  # Use empty list as fallback

        try:
            transactions = fetch_financial_data_from_api("https://api.accounting.com", "your_token")
        except Exception as e:
            print(f"Error fetching financial data: {e}")
            transactions = []

        try:
            goals = fetch_goal_data_from_api("https://api.goalsystem.com", "your_token")
        except Exception as e:
            print(f"Error fetching goal data: {e}")
            goals = []

        # Validate data quality
        analyzer = AdvancedDataAnalyzer()
        quality_check = analyzer.validate_task_data([t.__dict__ for t in tasks])

        if quality_check.overall_score < 0.5:
            print(f"Data quality too low: {quality_check.overall_score}")
            # Could implement fallback logic here
            return None

        # Generate report
        generator = BusinessAuditGenerator()
        report = generator.generate_weekly_briefing(tasks, transactions, goals)

        # Format and distribute
        report_gen = ReportGenerator()
        result = report_gen.generate_and_distribute_weekly_briefing(
            [t.__dict__ for t in tasks],
            [f.__dict__ for f in transactions],
            [g.__dict__ for g in goals],
            distribution_list=['ceo@company.com'],
            output_formats=['html']
        )

        return result

    except Exception as e:
        print(f"Unexpected error in report generation: {e}")
        import traceback
        traceback.print_exc()
        return None
```

## Custom Analysis Examples

### Creating Custom Analysis Functions
```python
def custom_kpi_analysis(tasks, transactions, goals):
    """Example of custom KPI analysis"""
    from business_audit_generator.scripts.business_audit_core import DataAnalyzer

    analyzer = DataAnalyzer()

    # Perform standard analysis
    task_analysis = analyzer.analyze_tasks(tasks)
    financial_analysis = analyzer.analyze_finances(transactions)
    goal_analysis = analyzer.analyze_goals(goals)

    # Calculate custom KPIs
    kpis = {
        "project_health_score": calculate_project_health(task_analysis, goal_analysis),
        "financial_efficiency_ratio": calculate_financial_efficiency(financial_analysis),
        "goal_alignment_index": calculate_goal_alignment(task_analysis, goal_analysis),
        "resource_utilization_rate": calculate_resource_utilization(tasks)
    }

    return {
        "standard_analysis": {
            "tasks": task_analysis,
            "finances": financial_analysis,
            "goals": goal_analysis
        },
        "custom_kpis": kpis
    }

def calculate_project_health(task_analysis, goal_analysis):
    """Calculate a composite health score for projects"""
    task_score = task_analysis.get('completion_rate', 0) * 0.4
    goal_score = goal_analysis.get('overall_progress', 0) * 0.6
    return task_score + goal_score

def calculate_financial_efficiency(financial_analysis):
    """Calculate financial efficiency ratio"""
    total_income = financial_analysis.get('total_income', 1)  # Avoid division by zero
    total_spending = financial_analysis.get('total_spending', 0)
    return (total_income - total_spending) / total_income if total_income != 0 else 0

def calculate_goal_alignment(task_analysis, goal_analysis):
    """Calculate alignment between task completion and goal progress"""
    task_completion = task_analysis.get('completion_rate', 0)
    goal_progress = goal_analysis.get('overall_progress', 0)
    return (task_completion + goal_progress) / 2

def calculate_resource_utilization(tasks):
    """Calculate resource utilization based on task assignments"""
    if not tasks:
        return 0

    # Count unique assignees
    assignees = set(task.assigned_to for task in tasks if task.assigned_to)
    total_tasks = len(tasks)

    # Calculate utilization (simplified)
    avg_tasks_per_person = total_tasks / len(assignees) if assignees else 0
    ideal_load = 5  # Assumption: 5 tasks per person is ideal

    return min(1.0, avg_tasks_per_person / ideal_load)
```

These examples demonstrate the comprehensive capabilities of the Business Audit Generator skill for analyzing business data and generating executive-level reports like the Monday Morning CEO Briefing.