# Business Audit Generator

## Description
The Business Audit Generator skill implements logic that analyzes tasks, transactions, and goals to generate the weekly "Monday Morning CEO Briefing". This skill provides comprehensive business intelligence by aggregating and analyzing various business metrics, KPIs, and performance indicators to produce executive-level reports.

## Purpose
This skill automates the creation of weekly executive briefings by:
- Aggregating and analyzing task completion rates and progress
- Evaluating financial transactions and spending patterns
- Tracking goal achievement against targets
- Generating insights and recommendations
- Creating formatted reports suitable for executive consumption
- Identifying trends, anomalies, and opportunities

## Key Features

### Data Analysis
- Task completion rate analysis
- Transaction categorization and trend analysis
- Goal progress tracking and milestone identification
- Performance metric calculation
- Anomaly detection in business operations

### Report Generation
- Executive summary creation
- Visual chart and graph generation
- Trend analysis and forecasting
- Comparative analysis (week-over-week, month-over-month)
- Risk assessment and opportunity identification

### Data Sources Integration
- Task management systems integration
- Financial transaction systems
- Goal tracking platforms
- CRM and sales data
- Operational metrics collection

### Output Formats
- Weekly CEO briefing reports
- Executive dashboard summaries
- Email notifications and distributions
- PDF and HTML report generation
- API endpoints for integration

## Configuration

### Default Configuration
```json
{
  "analysis": {
    "include_task_completion": true,
    "include_financial_metrics": true,
    "include_goal_progress": true,
    "include_sales_data": true,
    "include_operational_metrics": true
  },
  "reporting": {
    "report_title": "Monday Morning CEO Briefing",
    "report_frequency": "weekly",
    "report_day": "monday",
    "report_time": "08:00",
    "output_formats": ["pdf", "html", "email"],
    "distribution_list": ["ceo@company.com"]
  },
  "metrics": {
    "task_completion_threshold": 0.8,
    "financial_variance_threshold": 0.1,
    "goal_progress_threshold": 0.75,
    "risk_identification_criteria": {
      "low": 0.2,
      "medium": 0.5,
      "high": 0.8
    }
  },
  "data_sources": {
    "task_system_url": "https://tasks.company.com/api",
    "finance_system_url": "https://finance.company.com/api",
    "crm_system_url": "https://crm.company.com/api",
    "goals_system_url": "https://goals.company.com/api"
  }
}
```

### Example Report Structure
```json
{
  "report_date": "2024-01-15T08:00:00Z",
  "period": "2024-W03",
  "summary": {
    "overall_performance": "positive",
    "key_accomplishments": ["Goal milestone achieved", "Budget variance under threshold"],
    "concerns": ["Task completion below threshold", "Sales slightly behind target"]
  },
  "task_analysis": {
    "completion_rate": 0.78,
    "total_tasks": 156,
    "completed_tasks": 122,
    "overdue_tasks": 8,
    "trending": "slightly_down"
  },
  "financial_analysis": {
    "total_spending": 45678.90,
    "budget_variance": -0.05,
    "top_categories": {
      "marketing": 15678.50,
      "operations": 12345.67,
      "rd": 8765.43
    },
    "trending": "stable"
  },
  "goal_progress": {
    "q1_goals": {
      "revenue_target": 0.68,
      "customer_acquisition": 0.72,
      "product_launch": 0.85
    },
    "milestones_achieved": 3,
    "milestones_pending": 2,
    "trending": "on_track"
  },
  "recommendations": [
    "Increase focus on overdue tasks to meet quarterly goals",
    "Review marketing spend efficiency for better ROI"
  ],
  "risks": [
    "Task completion rate approaching concern threshold"
  ]
}
```

## Usage Scenarios

### Basic Report Generation
```python
from business_audit_generator import BusinessAuditGenerator

generator = BusinessAuditGenerator()
report = generator.generate_weekly_briefing()
print(report.summary)
```

### Custom Data Analysis
```python
# Analyze specific data sets
task_data = get_task_data()
financial_data = get_financial_data()
goal_data = get_goal_data()

analysis = generator.analyze_data_sets(
    tasks=task_data,
    finances=financial_data,
    goals=goal_data
)

# Generate custom report
custom_report = generator.generate_custom_report(analysis)
```

### Scheduled Generation
```python
# Integrate with scheduler for weekly generation
from scheduler_cron_integration import Scheduler

scheduler = Scheduler()
job_id = scheduler.schedule_job(
    name="weekly_ceo_briefing",
    cron_expression="0 8 * * 1",  # Every Monday at 8 AM
    callback=generator.generate_and_send_briefing,
    description="Generate and send weekly CEO briefing"
)
```

## Integration Points

### With Task Management Systems
- Pull task completion data
- Analyze workload distribution
- Identify bottlenecks and resource allocation issues

### With Financial Systems
- Aggregate spending data
- Analyze budget variances
- Track expense category trends

### With Goal Tracking Platforms
- Monitor goal progress
- Calculate achievement rates
- Identify milestone completions

### With Claude Code
- Integrate with existing workflows
- Automate data collection processes
- Generate natural language summaries

## Data Processing Pipeline

### Data Collection Phase
1. Fetch task data from task management systems
2. Retrieve financial transactions from accounting systems
3. Collect goal progress from tracking platforms
4. Gather operational metrics from various sources

### Data Analysis Phase
1. Clean and normalize data
2. Calculate performance metrics
3. Identify trends and patterns
4. Detect anomalies and outliers
5. Assess risk factors

### Report Generation Phase
1. Compile analyzed data into report structure
2. Generate executive summaries
3. Create visualizations
4. Format for distribution
5. Send to stakeholders

## Security Considerations
- Secure data access with proper authentication
- Encrypt sensitive financial data
- Implement access controls for reports
- Audit data access and report generation

## Performance Considerations
- Efficient data processing algorithms
- Caching for frequently accessed data
- Asynchronous processing for large datasets
- Optimized database queries

## Dependencies
- `pandas` for data analysis
- `matplotlib` for visualization
- `jinja2` for report templating
- `requests` for API integrations
- `structlog` for structured logging