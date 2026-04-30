#!/usr/bin/env python3
"""
Report Generator for Business Audit Generator

Generates comprehensive reports including the weekly "Monday Morning CEO Briefing"
"""

import asyncio
import datetime
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from jinja2 import Template, Environment, FileSystemLoader
from io import StringIO

import structlog
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from business_audit_core import (
    BusinessAuditReport, PerformanceMetric, RiskAssessment,
    PerformanceLevel, RiskLevel, ReportPeriod
)
from data_analyzer import AdvancedDataAnalyzer

logger = structlog.get_logger()


class ChartGenerator:
    """Generates visual charts for business reports"""

    def __init__(self, output_dir: str = "./charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logger.bind(component="ChartGenerator")

    def generate_task_completion_chart(self, task_analysis: Dict, period: str = "weekly") -> str:
        """Generate a chart showing task completion rates"""
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))

            # Sample data for demonstration
            categories = ['On Time', 'Completed Late', 'In Progress', 'Not Started', 'Overdue']

            # Calculate proportions based on task analysis
            total_tasks = task_analysis.get('total_tasks', 1)
            if total_tasks == 0:
                values = [0, 0, 0, 0, 0]
            else:
                completed_on_time = task_analysis.get('completed_tasks', 0) - 2  # Assume 2 were late
                completed_late = 2  # Placeholder
                in_progress = task_analysis.get('in_progress_tasks', 0)
                not_started = total_tasks - task_analysis.get('completed_tasks', 0) - in_progress
                overdue = task_analysis.get('overdue_tasks', 0)

                values = [completed_on_time, completed_late, in_progress, not_started, overdue]

            colors = ['#2ecc71', '#f39c12', '#3498db', '#95a5a6', '#e74c3c']  # Green, Orange, Blue, Gray, Red

            bars = ax.bar(categories, values, color=colors)

            ax.set_title(f'Task Status Distribution - {period.title()}', fontsize=14, fontweight='bold')
            ax.set_ylabel('Number of Tasks')

            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value}', ha='center', va='bottom')

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Save chart
            chart_filename = f"task_completion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = self.output_dir / chart_filename
            plt.savefig(chart_path)
            plt.close()

            self.logger.info("Task completion chart generated", chart_path=str(chart_path))
            return str(chart_path)

        except Exception as e:
            self.logger.error("Error generating task completion chart", error=str(e))
            return ""

    def generate_financial_trend_chart(self, financial_analysis: Dict, period: str = "weekly") -> str:
        """Generate a chart showing financial trends"""
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))

            # Sample data for demonstration - in a real scenario, this would come from historical data
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=8, freq='4D')
            spending = np.random.uniform(10000, 50000, size=8)
            income = np.random.uniform(20000, 80000, size=8)
            net_flow = income - spending

            ax.plot(dates, spending, marker='o', linewidth=2, label='Spending', color='#e74c3c')
            ax.plot(dates, income, marker='s', linewidth=2, label='Income', color='#2ecc71')
            ax.plot(dates, net_flow, marker='^', linewidth=2, label='Net Flow', color='#3498db')

            ax.set_title(f'Financial Trends - {period.title()}', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Amount ($)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
            plt.xticks(rotation=45)

            plt.tight_layout()

            # Save chart
            chart_filename = f"financial_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = self.output_dir / chart_filename
            plt.savefig(chart_path)
            plt.close()

            self.logger.info("Financial trends chart generated", chart_path=str(chart_path))
            return str(chart_path)

        except Exception as e:
            self.logger.error("Error generating financial trends chart", error=str(e))
            return ""

    def generate_goal_progress_chart(self, goal_analysis: Dict, period: str = "weekly") -> str:
        """Generate a chart showing goal progress"""
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))

            # Sample data for demonstration
            if goal_analysis.get('total_goals', 0) > 0:
                # Create sample goal progress data
                n_goals = min(goal_analysis['total_goals'], 10)  # Limit to 10 goals for clarity
                goal_names = [f"Goal {i+1}" for i in range(n_goals)]
                progress_values = np.random.uniform(0.3, 1.0, size=n_goals)  # Random progress between 30-100%

                # Color code based on progress
                colors = []
                for progress in progress_values:
                    if progress >= 0.9:
                        colors.append('#2ecc71')  # Green for high progress
                    elif progress >= 0.7:
                        colors.append('#f1c40f')  # Yellow for medium progress
                    elif progress >= 0.5:
                        colors.append('#f39c12')  # Orange for lower progress
                    else:
                        colors.append('#e74c3c')  # Red for low progress

                bars = ax.barh(goal_names, progress_values, color=colors)

                ax.set_title(f'Goal Progress Overview - {period.title()}', fontsize=14, fontweight='bold')
                ax.set_xlabel('Progress (%)')
                ax.set_xlim(0, 1.0)

                # Add percentage labels
                for bar, progress in zip(bars, progress_values):
                    width = bar.get_width()
                    ax.text(width, bar.get_y() + bar.get_height()/2.,
                            f'{progress:.0%}', ha='left', va='center')
            else:
                ax.text(0.5, 0.5, 'No Goals Data Available', horizontalalignment='center',
                       verticalalignment='center', transform=ax.transAxes, fontsize=14)
                ax.set_title(f'Goal Progress Overview - {period.title()}', fontsize=14, fontweight='bold')

            plt.tight_layout()

            # Save chart
            chart_filename = f"goal_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = self.output_dir / chart_filename
            plt.savefig(chart_path)
            plt.close()

            self.logger.info("Goal progress chart generated", chart_path=str(chart_path))
            return str(chart_path)

        except Exception as e:
            self.logger.error("Error generating goal progress chart", error=str(e))
            return ""

    def generate_performance_metrics_chart(self, performance_metrics: List[PerformanceMetric]) -> str:
        """Generate a chart showing performance metrics"""
        try:
            if not performance_metrics:
                return ""

            # Create figure
            fig, ax = plt.subplots(figsize=(12, 8))

            metric_names = [metric.name for metric in performance_metrics]
            current_values = [metric.current_value for metric in performance_metrics]
            target_values = [metric.target_value for metric in performance_metrics]

            x = np.arange(len(metric_names))
            width = 0.35

            bars1 = ax.bar(x - width/2, current_values, width, label='Current', color='#3498db')
            bars2 = ax.bar(x + width/2, target_values, width, label='Target', color='#e74c3c')

            ax.set_title('Performance Metrics Comparison', fontsize=14, fontweight='bold')
            ax.set_ylabel('Value')
            ax.set_xticks(x)
            ax.set_xticklabels(metric_names, rotation=45, ha='right')
            ax.legend()

            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(f'{height:.2f}',
                              xy=(bar.get_x() + bar.get_width() / 2, height),
                              xytext=(0, 3),
                              textcoords="offset points",
                              ha='center', va='bottom')

            plt.tight_layout()

            # Save chart
            chart_filename = f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = self.output_dir / chart_filename
            plt.savefig(chart_path)
            plt.close()

            self.logger.info("Performance metrics chart generated", chart_path=str(chart_path))
            return str(chart_path)

        except Exception as e:
            self.logger.error("Error generating performance metrics chart", error=str(e))
            return ""


class ReportFormatter:
    """Formats business audit reports in various output formats"""

    def __init__(self, templates_dir: str = "./templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.logger = logger.bind(component="ReportFormatter")

    def create_html_template(self) -> str:
        """Create a default HTML template for reports"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { background-color: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .summary { font-size: 18px; line-height: 1.6; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .positive { color: #27ae60; }
        .negative { color: #e74c3c; }
        .neutral { color: #f39c12; }
        .chart-container { text-align: center; margin: 20px 0; }
        .recommendations { background-color: #ecf0f1; padding: 15px; border-left: 4px solid #3498db; }
        .risks { background-color: #fdf2f2; border-left: 4px solid #e74c3c; padding: 15px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ report_title }}</h1>
        <p>Generated: {{ report_date }} | Period: {{ period }}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div class="summary">{{ summary|safe }}</div>
    </div>

    <div class="section">
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Task Performance</h3>
                <p><strong>Completion Rate:</strong> {{ "%.2f"|format(task_analysis.completion_rate * 100) }}%</p>
                <p><strong>Total Tasks:</strong> {{ task_analysis.total_tasks }}</p>
                <p><strong>Completed:</strong> {{ task_analysis.completed_tasks }}</p>
                <p><strong>Overdue:</strong> {{ task_analysis.overdue_tasks }}</p>
            </div>

            <div class="metric-card">
                <h3>Financial Performance</h3>
                <p><strong>Total Spending:</strong> ${{ "%.2f"|format(financial_analysis.total_spending) }}</p>
                <p><strong>Total Income:</strong> ${{ "%.2f"|format(financial_analysis.total_income) }}</p>
                <p><strong>Net Flow:</strong> ${{ "%.2f"|format(financial_analysis.net_flow) }}</p>
                <p><strong>Status:</strong> <span class="{% if financial_analysis.net_flow >= 0 %}positive{% else %}negative{% endif %}">{{ financial_analysis.trending|title }}</span></p>
            </div>

            <div class="metric-card">
                <h3>Goal Progress</h3>
                <p><strong>Overall Progress:</strong> {{ "%.2f"|format(goal_progress.overall_progress * 100) }}%</p>
                <p><strong>Total Goals:</strong> {{ goal_progress.total_goals }}</p>
                <p><strong>On Track:</strong> {{ goal_progress.goals_on_track }}</p>
                <p><strong>Behind:</strong> {{ goal_progress.goals_behind }}</p>
            </div>
        </div>
    </div>

    {% if charts %}
    <div class="section">
        <h2>Visual Analytics</h2>
        {% for chart_path in charts %}
        <div class="chart-container">
            <img src="{{ chart_path }}" alt="Analytics Chart" style="max-width: 100%;">
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if key_accomplishments %}
    <div class="section">
        <h2>Key Accomplishments</h2>
        <ul>
            {% for accomplishment in key_accomplishments %}
            <li>{{ accomplishment }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if concerns %}
    <div class="section risks">
        <h2>Areas of Concern</h2>
        <ul>
            {% for concern in concerns %}
            <li>{{ concern }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if recommendations %}
    <div class="section recommendations">
        <h2>Recommendations</h2>
        <ol>
            {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
            {% endfor %}
        </ol>
    </div>
    {% endif %}

    {% if next_steps %}
    <div class="section">
        <h2>Next Steps</h2>
        <ol>
            {% for step in next_steps %}
            <li>{{ step }}</li>
            {% endfor %}
        </ol>
    </div>
    {% endif %}
</body>
</html>
        """

        template_path = self.templates_dir / "report_template.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

        return str(template_path)

    def create_email_template(self) -> str:
        """Create a default email template for reports"""
        email_template = """
Subject: {{ report_title }} - {{ period }}

Hi Team,

{{ summary }}

Key Accomplishments:
{% for accomplishment in key_accomplishments %}
• {{ accomplishment }}
{% endfor %}

Areas of Concern:
{% for concern in concerns %}
• {{ concern }}
{% endfor %}

Recommendations:
{% for recommendation in recommendations %}
• {{ recommendation }}
{% endfor %}

Next Steps:
{% for step in next_steps %}
• {{ step }}
{% endfor %}

Best regards,
Business Audit Generator

---
This report was automatically generated on {{ report_date }}.
        """

        template_path = self.templates_dir / "email_template.txt"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(email_template)

        return str(template_path)

    def generate_html_report(self, report: BusinessAuditReport, charts: List[str] = None) -> str:
        """Generate an HTML report"""
        # Create template if it doesn't exist
        template_path = self.templates_dir / "report_template.html"
        if not template_path.exists():
            self.create_html_template()

        # Load template
        env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        template = env.get_template("report_template.html")

        # Prepare data for template
        report_data = {
            'report_title': 'Monday Morning CEO Briefing',
            'report_date': report.report_date.strftime('%Y-%m-%d %H:%M:%S'),
            'period': report.period,
            'summary': report.summary,
            'task_analysis': report.task_analysis,
            'financial_analysis': report.financial_analysis,
            'goal_progress': report.goal_progress,
            'key_accomplishments': report.key_accomplishments,
            'concerns': report.concerns,
            'recommendations': report.recommendations,
            'next_steps': report.next_steps,
            'charts': charts or []
        }

        # Render template
        html_output = template.render(**report_data)

        return html_output

    def generate_email_content(self, report: BusinessAuditReport) -> str:
        """Generate email content for the report"""
        # Create template if it doesn't exist
        template_path = self.templates_dir / "email_template.txt"
        if not template_path.exists():
            self.create_email_template()

        # Load template
        env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        template = env.get_template("email_template.txt")

        # Prepare data for template
        report_data = {
            'report_title': 'Monday Morning CEO Briefing',
            'period': report.period,
            'summary': report.summary,
            'key_accomplishments': report.key_accomplishments,
            'concerns': report.concerns,
            'recommendations': report.recommendations,
            'next_steps': report.next_steps,
            'report_date': report.report_date.strftime('%Y-%m-%d')
        }

        # Render template
        email_output = template.render(**report_data)

        return email_output

    def generate_pdf_report(self, report: BusinessAuditReport, charts: List[str] = None) -> str:
        """Generate a PDF report (placeholder implementation)"""
        # Note: Actual PDF generation would require additional libraries like reportlab or weasyprint
        # This is a placeholder that creates a text file with report content

        pdf_content = f"""
MONDAY MORNING CEO BRIEFING
===========================

Report Date: {report.report_date.strftime('%Y-%m-%d %H:%M:%S')}
Period: {report.period}

EXECUTIVE SUMMARY
-----------------
{report.summary}


TASK ANALYSIS
-------------
Completion Rate: {report.task_analysis.get('completion_rate', 0):.2%}
Total Tasks: {report.task_analysis.get('total_tasks', 0)}
Completed: {report.task_analysis.get('completed_tasks', 0)}
Overdue: {report.task_analysis.get('overdue_tasks', 0)}


FINANCIAL ANALYSIS
------------------
Total Spending: ${report.financial_analysis.get('total_spending', 0):,.2f}
Total Income: ${report.financial_analysis.get('total_income', 0):,.2f}
Net Flow: ${report.financial_analysis.get('net_flow', 0):,.2f}
Status: {report.financial_analysis.get('trending', 'Unknown').title()}


GOAL PROGRESS
-------------
Overall Progress: {report.goal_progress.get('overall_progress', 0):.2%}
Total Goals: {report.goal_progress.get('total_goals', 0)}
On Track: {report.goal_progress.get('goals_on_track', 0)}
Behind: {report.goal_progress.get('goals_behind', 0)}


KEY ACCOMPLISHMENTS
-------------------
"""
        for accomplishment in report.key_accomplishments:
            pdf_content += f"• {accomplishment}\n"

        pdf_content += "\nAREAS OF CONCERN\n----------------\n"
        for concern in report.concerns:
            pdf_content += f"• {concern}\n"

        pdf_content += "\nRECOMMENDATIONS\n---------------\n"
        for recommendation in report.recommendations:
            pdf_content += f"• {recommendation}\n"

        pdf_content += "\nNEXT STEPS\n----------\n"
        for step in report.next_steps:
            pdf_content += f"• {step}\n"

        # Save to file
        pdf_filename = f"CEO_Briefing_{report.report_date.strftime('%Y%m%d_%H%M%S')}.txt"
        pdf_path = Path(".") / pdf_filename
        with open(pdf_path, 'w', encoding='utf-8') as f:
            f.write(pdf_content)

        self.logger.info("PDF report generated (text format)", report_path=str(pdf_path))
        return str(pdf_path)


class ReportGenerator:
    """Main report generator that coordinates all report generation activities"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.chart_generator = ChartGenerator(output_dir="./charts")
        self.formatter = ReportFormatter(templates_dir="./templates")
        self.logger = logger.bind(component="ReportGenerator")

    def generate_weekly_ceo_briefing(self,
                                   tasks: List[Dict],
                                   transactions: List[Dict],
                                   goals: List[Dict],
                                   period_start: Optional[datetime] = None,
                                   period_end: Optional[datetime] = None) -> BusinessAuditReport:
        """Generate the weekly CEO briefing report"""

        # Use the business audit core to generate the basic report
        from business_audit_core import BusinessAuditGenerator
        generator = BusinessAuditGenerator()

        # Convert dictionaries back to dataclasses if needed
        from business_audit_core import TaskData, FinancialTransaction, GoalData

        # Create dataclass instances from dictionaries
        task_objects = []
        for task in tasks:
            if isinstance(task, dict):
                task_objects.append(TaskData(
                    id=task.get('id', ''),
                    title=task.get('title', ''),
                    status=task.get('status', ''),
                    assigned_to=task.get('assigned_to', ''),
                    created_date=pd.to_datetime(task.get('created_date')) if task.get('created_date') else datetime.now(),
                    due_date=pd.to_datetime(task.get('due_date')) if task.get('due_date') else None,
                    completed_date=pd.to_datetime(task.get('completed_date')) if task.get('completed_date') else None,
                    priority=task.get('priority', 'medium'),
                    category=task.get('category', 'general'),
                    estimated_hours=task.get('estimated_hours'),
                    actual_hours=task.get('actual_hours'),
                    project_id=task.get('project_id')
                ))
            else:
                task_objects.append(task)

        transaction_objects = []
        for trans in transactions:
            if isinstance(trans, dict):
                transaction_objects.append(FinancialTransaction(
                    id=trans.get('id', ''),
                    date=pd.to_datetime(trans.get('date')) if trans.get('date') else datetime.now(),
                    amount=trans.get('amount', 0.0),
                    category=trans.get('category', ''),
                    vendor=trans.get('vendor', ''),
                    description=trans.get('description', ''),
                    transaction_type=trans.get('transaction_type', 'expense'),
                    project_id=trans.get('project_id'),
                    department=trans.get('department'),
                    currency=trans.get('currency', 'USD'),
                    approved=trans.get('approved', True)
                ))
            else:
                transaction_objects.append(trans)

        goal_objects = []
        for goal in goals:
            if isinstance(goal, dict):
                goal_objects.append(GoalData(
                    id=goal.get('id', ''),
                    title=goal.get('title', ''),
                    description=goal.get('description', ''),
                    target_date=pd.to_datetime(goal.get('target_date')) if goal.get('target_date') else datetime.now() + timedelta(days=30),
                    current_progress=goal.get('current_progress', 0.0),
                    target_value=goal.get('target_value', 1.0),
                    current_value=goal.get('current_value', 0.0),
                    owner=goal.get('owner', ''),
                    category=goal.get('category', 'business'),
                    baseline_value=goal.get('baseline_value', 0.0),
                    milestones=goal.get('milestones', [])
                ))
            else:
                goal_objects.append(goal)

        # Generate the base report
        report = generator.generate_weekly_briefing(
            task_objects, transaction_objects, goal_objects,
            period_start, period_end
        )

        self.logger.info("Weekly CEO briefing generated", report_id=report.report_id)
        return report

    def generate_visual_reports(self, report: BusinessAuditReport) -> List[str]:
        """Generate visual charts for the report"""
        charts = []

        # Generate task completion chart
        task_chart = self.chart_generator.generate_task_completion_chart(
            report.task_analysis,
            "weekly"
        )
        if task_chart:
            charts.append(task_chart)

        # Generate financial trends chart
        financial_chart = self.chart_generator.generate_financial_trend_chart(
            report.financial_analysis,
            "weekly"
        )
        if financial_chart:
            charts.append(financial_chart)

        # Generate goal progress chart
        goal_chart = self.chart_generator.generate_goal_progress_chart(
            report.goal_progress,
            "weekly"
        )
        if goal_chart:
            charts.append(goal_chart)

        # Generate performance metrics chart
        perf_chart = self.chart_generator.generate_performance_metrics_chart(
            report.performance_metrics
        )
        if perf_chart:
            charts.append(perf_chart)

        self.logger.info("Visual reports generated", chart_count=len(charts))
        return charts

    def format_report(self, report: BusinessAuditReport, output_formats: List[str] = None) -> Dict[str, str]:
        """Format the report in specified output formats"""
        if output_formats is None:
            output_formats = ['html', 'email']

        formatted_reports = {}

        if 'html' in output_formats:
            charts = self.generate_visual_reports(report)
            html_content = self.formatter.generate_html_report(report, charts)
            html_filename = f"CEO_Briefing_{report.report_date.strftime('%Y%m%d_%H%M%S')}.html"
            html_path = self.output_dir / html_filename
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            formatted_reports['html'] = str(html_path)

        if 'email' in output_formats:
            email_content = self.formatter.generate_email_content(report)
            email_filename = f"CEO_Briefing_{report.report_date.strftime('%Y%m%d_%H%M%S')}_email.txt"
            email_path = self.output_dir / email_filename
            with open(email_path, 'w', encoding='utf-8') as f:
                f.write(email_content)
            formatted_reports['email'] = str(email_path)

        if 'pdf' in output_formats:
            pdf_path = self.formatter.generate_pdf_report(report)
            formatted_reports['pdf'] = pdf_path

        self.logger.info("Report formatted", formats=list(formatted_reports.keys()))
        return formatted_reports

    def distribute_report(self, report_paths: Dict[str, str], distribution_list: List[str]) -> bool:
        """Distribute the report to specified recipients"""
        # This is a placeholder for actual distribution logic
        # In a real implementation, this would send emails or upload to shared locations
        self.logger.info("Report distribution initiated",
                        distribution_count=len(distribution_list),
                        report_formats=list(report_paths.keys()))

        # For now, just log what would be distributed
        for fmt, path in report_paths.items():
            self.logger.info(f"Report {fmt} prepared at: {path}")

        return True

    def generate_and_distribute_weekly_briefing(self,
                                              tasks: List[Dict],
                                              transactions: List[Dict],
                                              goals: List[Dict],
                                              distribution_list: List[str] = None,
                                              output_formats: List[str] = None,
                                              period_start: Optional[datetime] = None,
                                              period_end: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate and distribute the complete weekly briefing"""

        # Set default distribution list and output formats
        if distribution_list is None:
            distribution_list = ['ceo@company.com']
        if output_formats is None:
            output_formats = ['html', 'email', 'pdf']

        # Generate the report
        report = self.generate_weekly_ceo_briefing(
            tasks, transactions, goals, period_start, period_end
        )

        # Format the report
        formatted_reports = self.format_report(report, output_formats)

        # Distribute the report
        success = self.distribute_report(formatted_reports, distribution_list)

        result = {
            'report_id': report.report_id,
            'report_date': report.report_date,
            'formatted_reports': formatted_reports,
            'distribution_list': distribution_list,
            'success': success
        }

        self.logger.info("Weekly briefing generated and distributed",
                        report_id=report.report_id,
                        success=success)
        return result


class ExecutiveDashboard:
    """Generates executive dashboards from business audit data"""

    def __init__(self):
        self.report_generator = ReportGenerator()
        self.logger = logger.bind(component="ExecutiveDashboard")

    def create_dashboard_data(self, report: BusinessAuditReport) -> Dict[str, Any]:
        """Create dashboard data structure from report"""
        dashboard_data = {
            'summary_cards': [
                {
                    'title': 'Task Completion Rate',
                    'value': f"{report.task_analysis.get('completion_rate', 0):.1%}",
                    'change': self._calculate_change(report.task_analysis.get('completion_rate', 0)),
                    'trend': report.task_analysis.get('trending', 'neutral'),
                    'color': self._get_status_color(report.task_analysis.get('completion_rate', 0), 0.8)
                },
                {
                    'title': 'Net Financial Flow',
                    'value': f"${report.financial_analysis.get('net_flow', 0):,.0f}",
                    'change': self._calculate_change(report.financial_analysis.get('net_flow', 0)),
                    'trend': report.financial_analysis.get('trending', 'neutral'),
                    'color': self._get_status_color(report.financial_analysis.get('net_flow', 0), 0)
                },
                {
                    'title': 'Goal Achievement',
                    'value': f"{report.goal_progress.get('overall_progress', 0):.1%}",
                    'change': self._calculate_change(report.goal_progress.get('overall_progress', 0)),
                    'trend': report.goal_progress.get('trending', 'neutral'),
                    'color': self._get_status_color(report.goal_progress.get('overall_progress', 0), 0.75)
                }
            ],
            'key_metrics': {
                'total_tasks': report.task_analysis.get('total_tasks', 0),
                'completed_tasks': report.task_analysis.get('completed_tasks', 0),
                'total_spending': report.financial_analysis.get('total_spending', 0),
                'total_income': report.financial_analysis.get('total_income', 0),
                'total_goals': report.goal_progress.get('total_goals', 0),
                'goals_on_track': report.goal_progress.get('goals_on_track', 0)
            },
            'recent_activity': [
                f"{len(report.key_accomplishments)} key accomplishments",
                f"{len(report.concerns)} areas of concern",
                f"{len(report.recommendations)} recommendations"
            ],
            'upcoming_deadlines': [],  # Would be populated from tasks
            'risk_assessment': {
                'high_risk_items': len([r for r in report.risk_assessments if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]),
                'medium_risk_items': len([r for r in report.risk_assessments if r.level == RiskLevel.MEDIUM]),
                'low_risk_items': len([r for r in report.risk_assessments if r.level == RiskLevel.LOW])
            }
        }

        return dashboard_data

    def _calculate_change(self, value: float) -> str:
        """Calculate percentage change indicator"""
        # Placeholder implementation - in reality, this would compare to previous period
        import random
        change_percent = random.uniform(-10, 10)  # Random for demo
        return f"{'+' if change_percent >= 0 else ''}{change_percent:.1f}%"

    def _get_status_color(self, value: float, threshold: float) -> str:
        """Get color based on value vs threshold"""
        if value >= threshold:
            return "green"
        elif value >= threshold * 0.7:
            return "yellow"
        else:
            return "red"


def create_sample_report_generator():
    """Create and return a configured report generator"""
    return ReportGenerator()


if __name__ == "__main__":
    # Demo of report generator functionality
    print("Report Generator Demo")
    print("=" * 40)

    # Create sample data
    from business_audit_core import create_sample_tasks, create_sample_transactions, create_sample_goals

    print("Creating sample data...")
    tasks = create_sample_tasks(30)
    transactions = create_sample_transactions(25)
    goals = create_sample_goals(10)

    print(f"Created {len(tasks)} tasks, {len(transactions)} transactions, {len(goals)} goals")

    # Create report generator
    generator = ReportGenerator()

    print("\nGenerating weekly CEO briefing...")

    # Convert data to dictionaries for the generator
    task_dicts = [asdict(task) for task in tasks]
    transaction_dicts = [asdict(trans) for trans in transactions]
    goal_dicts = [asdict(goal) for goal in goals]

    result = generator.generate_and_distribute_weekly_briefing(
        task_dicts, transaction_dicts, goal_dicts,
        distribution_list=['ceo@company.com', 'executive-team@company.com'],
        output_formats=['html', 'email']
    )

    print(f"\nReport Generation Result:")
    print(f"  Report ID: {result['report_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Formatted Reports: {list(result['formatted_reports'].keys())}")

    for fmt, path in result['formatted_reports'].items():
        print(f"    {fmt.upper()}: {path}")

    # Create dashboard data
    print("\nCreating dashboard data...")
    from business_audit_core import BusinessAuditGenerator
    core_gen = BusinessAuditGenerator()
    report = core_gen.generate_weekly_briefing(
        tasks, transactions, goals
    )

    dashboard = ExecutiveDashboard()
    dashboard_data = dashboard.create_dashboard_data(report)

    print(f"\nDashboard Summary Cards: {len(dashboard_data['summary_cards'])}")
    for card in dashboard_data['summary_cards']:
        print(f"  {card['title']}: {card['value']} ({card['trend']})")

    print(f"\nKey Metrics:")
    for key, value in dashboard_data['key_metrics'].items():
        print(f"  {key}: {value}")

    print(f"\nRisk Assessment:")
    print(f"  High Risk: {dashboard_data['risk_assessment']['high_risk_items']}")
    print(f"  Medium Risk: {dashboard_data['risk_assessment']['medium_risk_items']}")
    print(f"  Low Risk: {dashboard_data['risk_assessment']['low_risk_items']}")