# Business Audit Generator Skill

## Overview
The Business Audit Generator skill implements logic that analyzes tasks, transactions, and goals to generate the weekly "Monday Morning CEO Briefing". This skill provides comprehensive business intelligence by aggregating and analyzing various business metrics, KPIs, and performance indicators to produce executive-level reports.

## Features

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

## Components

### Core Modules
- `business_audit_core.py`: Main business audit engine and data structures
- `data_analyzer.py`: Advanced data analysis and anomaly detection
- `report_generator.py`: Report generation and formatting
- `config_manager.py`: Configuration management system
- `SKILL.md`: Main skill documentation

### Reference Materials
- `references/usage_examples.md`: Comprehensive usage examples
- `assets/example_config.json`: Example configuration file
- `assets/requirements.txt`: Dependencies

### Test Suite
- `test_business_audit_generator.py`: Comprehensive test suite

## Usage

### Installation
```bash
pip install -r .claude/skills/business-audit-generator/assets/requirements.txt
```

### Basic Usage
```python
from business_audit_generator.scripts.business_audit_core import BusinessAuditGenerator

# Create a business audit generator
generator = BusinessAuditGenerator()

# Create sample data (in practice, you'd fetch from your data sources)
from business_audit_generator.scripts.business_audit_core import TaskData, FinancialTransaction, GoalData
from datetime import datetime, timedelta

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
    )
    # Add more tasks as needed
]

transactions = [
    FinancialTransaction(
        id="trans_1",
        date=datetime.now() - timedelta(days=5),
        amount=-5000.00,
        category="Marketing",
        vendor="Marketing Agency",
        description="Q1 Campaign",
        transaction_type="expense"
    )
    # Add more transactions as needed
]

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
    )
    # Add more goals as needed
]

# Generate the weekly CEO briefing
report = generator.generate_weekly_briefing(tasks, transactions, goals)
print(f"Report summary: {report.summary}")
```

### Advanced Usage
```python
from business_audit_generator.scripts.data_analyzer import AdvancedDataAnalyzer
from business_audit_generator.scripts.report_generator import ReportGenerator

# Analyze data with advanced analyzer
analyzer = AdvancedDataAnalyzer()
analysis_results = analyzer.analyze_complete_dataset(
    [t.__dict__ for t in tasks],
    [tr.__dict__ for tr in transactions],
    [g.__dict__ for g in goals]
)

# Generate reports with multiple output formats
report_gen = ReportGenerator()
result = report_gen.generate_and_distribute_weekly_briefing(
    [t.__dict__ for t in tasks],
    [tr.__dict__ for tr in transactions],
    [g.__dict__ for g in goals],
    distribution_list=['ceo@company.com', 'executive-team@company.com'],
    output_formats=['html', 'email', 'pdf']
)
```

### Configuration
The skill supports multiple configuration approaches:

1. **Default Configuration**: Automatically creates sensible defaults
2. **Custom Configuration**: Load from JSON/YAML files
3. **Runtime Configuration**: Update settings dynamically

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

## Integration

### With Claude Code
- Integrate with existing workflows
- Automate data collection processes
- Generate natural language summaries

### With Data Sources
- Task management systems (Jira, Asana, Trello)
- Financial systems (QuickBooks, SAP, Oracle)
- CRM systems (Salesforce, HubSpot)
- Goal tracking platforms (OKRs, KPIs)

## Testing

The skill includes a comprehensive test suite that validates:
- Module imports and basic functionality
- Data analysis capabilities
- Report generation and formatting
- Configuration management
- Error handling

Run the tests with:
```bash
python test_business_audit_generator.py
```

## Examples

For comprehensive examples of usage scenarios, see:
- `references/usage_examples.md`
- Various analysis patterns and configurations
- Integration examples with data sources
- Advanced customization scenarios