#!/usr/bin/env python3
"""
Data Analyzer for Business Audit Generator

Advanced data analysis system for tasks, transactions, and goals
"""

import asyncio
import datetime
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from collections import defaultdict
import warnings

import structlog
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

logger = structlog.get_logger()


class DataSourceType(Enum):
    """Types of data sources"""
    TASKS = "tasks"
    FINANCIAL = "financial"
    GOALS = "goals"
    OPERATIONAL = "operational"
    CUSTOMERS = "customers"
    SALES = "sales"


class DataQualityScore(Enum):
    """Data quality scores"""
    EXCELLENT = 1.0
    GOOD = 0.8
    FAIR = 0.6
    POOR = 0.4
    CRITICAL = 0.2


@dataclass
class DataQualityMetrics:
    """Metrics for assessing data quality"""
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    validity: float
    overall_score: float

    def get_quality_level(self) -> DataQualityScore:
        """Get the quality level based on overall score"""
        if self.overall_score >= 0.9:
            return DataQualityScore.EXCELLENT
        elif self.overall_score >= 0.7:
            return DataQualityScore.GOOD
        elif self.overall_score >= 0.5:
            return DataQualityScore.FAIR
        elif self.overall_score >= 0.3:
            return DataQualityScore.POOR
        else:
            return DataQualityScore.CRITICAL


@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection"""
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: str
    affected_fields: List[str]
    severity: str  # low, medium, high, critical
    suggested_action: str


@dataclass
class TrendAnalysisResult:
    """Result of trend analysis"""
    trend_direction: str  # increasing, decreasing, stable, volatile
    trend_strength: float  # -1 to 1
    confidence: float
    period: str
    seasonal_components: Optional[Dict[str, float]] = None
    forecast: Optional[Dict[str, float]] = None


@dataclass
class CorrelationAnalysisResult:
    """Result of correlation analysis"""
    correlated_pairs: List[tuple]
    correlation_matrix: Dict[str, Dict[str, float]]
    causation_indicators: List[str]


class DataValidator:
    """Validates incoming data for quality and consistency"""

    def __init__(self):
        self.logger = logger.bind(component="DataValidator")

    def validate_task_data(self, data: List[Dict]) -> DataQualityMetrics:
        """Validate task data quality"""
        if not data:
            return DataQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        total_records = len(data)
        valid_records = 0
        complete_fields = 0
        total_fields = total_records * 8  # assuming 8 common task fields

        required_fields = ['id', 'title', 'status', 'created_date']

        for record in data:
            is_valid = True
            for field in required_fields:
                if field not in record or record[field] is None:
                    is_valid = False
                    break

            if is_valid:
                valid_records += 1

            # Count complete fields
            for field in record:
                if record[field] is not None and record[field] != "":
                    complete_fields += 1

        completeness = complete_fields / total_fields if total_fields > 0 else 0.0
        accuracy = valid_records / total_records if total_records > 0 else 0.0
        consistency = self._check_consistency(data)
        timeliness = self._check_timeliness(data, 'created_date')
        validity = self._check_validity(data)

        overall_score = (completeness + accuracy + consistency + timeliness + validity) / 5

        return DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity,
            overall_score=overall_score
        )

    def validate_financial_data(self, data: List[Dict]) -> DataQualityMetrics:
        """Validate financial data quality"""
        if not data:
            return DataQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        total_records = len(data)
        valid_records = 0
        complete_fields = 0
        total_fields = total_records * 6  # assuming 6 common financial fields

        required_fields = ['id', 'date', 'amount', 'category', 'vendor']

        for record in data:
            is_valid = True
            for field in required_fields:
                if field not in record or record[field] is None:
                    is_valid = False
                    break

            # Additional validation for amount field
            if 'amount' in record and not isinstance(record['amount'], (int, float)):
                is_valid = False

            if is_valid:
                valid_records += 1

            # Count complete fields
            for field in record:
                if record[field] is not None and record[field] != "":
                    complete_fields += 1

        completeness = complete_fields / total_fields if total_fields > 0 else 0.0
        accuracy = valid_records / total_records if total_records > 0 else 0.0
        consistency = self._check_consistency(data)
        timeliness = self._check_timeliness(data, 'date')
        validity = self._check_validity(data)

        overall_score = (completeness + accuracy + consistency + timeliness + validity) / 5

        return DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity,
            overall_score=overall_score
        )

    def validate_goal_data(self, data: List[Dict]) -> DataQualityMetrics:
        """Validate goal data quality"""
        if not data:
            return DataQualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        total_records = len(data)
        valid_records = 0
        complete_fields = 0
        total_fields = total_records * 7  # assuming 7 common goal fields

        required_fields = ['id', 'title', 'target_date', 'current_progress', 'target_value', 'current_value']

        for record in data:
            is_valid = True
            for field in required_fields:
                if field not in record or record[field] is None:
                    is_valid = False
                    break

            # Additional validation for progress and values
            if ('current_progress' in record and
                (record['current_progress'] < 0 or record['current_progress'] > 1)):
                is_valid = False

            if ('target_value' in record and not isinstance(record['target_value'], (int, float))):
                is_valid = False

            if ('current_value' in record and not isinstance(record['current_value'], (int, float))):
                is_valid = False

            if is_valid:
                valid_records += 1

            # Count complete fields
            for field in record:
                if record[field] is not None and record[field] != "":
                    complete_fields += 1

        completeness = complete_fields / total_fields if total_fields > 0 else 0.0
        accuracy = valid_records / total_records if total_records > 0 else 0.0
        consistency = self._check_consistency(data)
        timeliness = self._check_timeliness(data, 'target_date')
        validity = self._check_validity(data)

        overall_score = (completeness + accuracy + consistency + timeliness + validity) / 5

        return DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity,
            overall_score=overall_score
        )

    def _check_consistency(self, data: List[Dict]) -> float:
        """Check data consistency"""
        if not data:
            return 0.0

        # Check for consistent date formats, enum values, etc.
        consistency_score = 1.0

        # Example: check if status fields have consistent values
        if data and 'status' in data[0]:
            status_values = set()
            for record in data:
                if 'status' in record and record['status'] is not None:
                    status_values.add(str(record['status']).lower())

            # If too many variations, lower consistency score
            if len(status_values) > 10:  # arbitrary threshold
                consistency_score *= 0.8

        return consistency_score

    def _check_timeliness(self, data: List[Dict], date_field: str) -> float:
        """Check data timeliness"""
        if not data or date_field not in data[0]:
            return 0.0

        recent_count = 0
        total_count = len(data)

        # Consider data timely if it's from the last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)

        for record in data:
            if date_field in record and record[date_field]:
                try:
                    record_date = pd.to_datetime(record[date_field])
                    if record_date >= cutoff_date:
                        recent_count += 1
                except:
                    continue  # Skip invalid dates

        return recent_count / total_count if total_count > 0 else 0.0

    def _check_validity(self, data: List[Dict]) -> float:
        """Check data validity"""
        if not data:
            return 0.0

        valid_count = 0
        total_count = len(data)

        for record in data:
            # Basic validation checks
            is_valid = True
            for key, value in record.items():
                if value is None:
                    continue
                if isinstance(value, str) and len(value.strip()) == 0:
                    continue
                if isinstance(value, (int, float)) and pd.isna(value):
                    is_valid = False
                    break
            if is_valid:
                valid_count += 1

        return valid_count / total_count if total_count > 0 else 0.0


class AnomalyDetector:
    """Detects anomalies in business data"""

    def __init__(self):
        self.logger = logger.bind(component="AnomalyDetector")

    def detect_task_anomalies(self, tasks_df: pd.DataFrame) -> List[AnomalyDetectionResult]:
        """Detect anomalies in task data"""
        anomalies = []

        # Check for unusual task completion patterns
        if 'status' in tasks_df.columns and 'created_date' in tasks_df.columns:
            # Convert dates if needed
            tasks_df['created_date'] = pd.to_datetime(tasks_df['created_date'])

            # Look for unusually high completion rates in short periods
            daily_completions = tasks_df.groupby(tasks_df['created_date'].dt.date)['status'].apply(
                lambda x: (x == 'completed').sum()
            )

            if len(daily_completions) > 1:
                mean_completions = daily_completions.mean()
                std_completions = daily_completions.std()

                if std_completions > 0:
                    z_scores = np.abs(stats.zscore(daily_completions))
                    anomalous_days = daily_completions[z_scores > 2]  # 2 standard deviations

                    for date, count in anomalous_days.items():
                        if count > mean_completions * 2:  # More than 2x the mean
                            anomalies.append(AnomalyDetectionResult(
                                is_anomaly=True,
                                anomaly_score=z_scores[date],
                                anomaly_type="Unusual task completion volume",
                                affected_fields=["status", "created_date"],
                                severity="medium" if z_scores[date] < 3 else "high",
                                suggested_action="Investigate cause of high task completion volume"
                            ))

        # Check for unusually long-running tasks
        if 'created_date' in tasks_df.columns and 'status' in tasks_df.columns:
            incomplete_tasks = tasks_df[tasks_df['status'] != 'completed'].copy()
            if not incomplete_tasks.empty:
                incomplete_tasks['age_days'] = (
                    datetime.now() - pd.to_datetime(incomplete_tasks['created_date'])
                ).dt.days

                # Tasks older than 30 days might be concerning
                old_tasks = incomplete_tasks[incomplete_tasks['age_days'] > 30]
                if len(old_tasks) > len(tasks_df) * 0.1:  # More than 10% of tasks are old
                    anomalies.append(AnomalyDetectionResult(
                        is_anomaly=True,
                        anomaly_score=1.0,
                        anomaly_type="High proportion of old incomplete tasks",
                        affected_fields=["status", "created_date"],
                        severity="high",
                        suggested_action="Review task management and resource allocation"
                    ))

        return anomalies

    def detect_financial_anomalies(self, financial_df: pd.DataFrame) -> List[AnomalyDetectionResult]:
        """Detect anomalies in financial data"""
        anomalies = []

        if 'amount' not in financial_df.columns:
            return anomalies

        # Convert amounts to numeric if they're not already
        financial_df['amount'] = pd.to_numeric(financial_df['amount'], errors='coerce')
        valid_amounts = financial_df.dropna(subset=['amount'])

        if len(valid_amounts) < 2:
            return anomalies

        # Use Z-score to detect amount anomalies
        amounts = valid_amounts['amount']
        z_scores = np.abs(stats.zscore(amounts))

        # Find anomalies (values > 3 standard deviations)
        anomalous_indices = valid_amounts.index[z_scores > 3]

        for idx in anomalous_indices:
            record = valid_amounts.loc[idx]
            anomalies.append(AnomalyDetectionResult(
                is_anomaly=True,
                anomaly_score=float(z_scores[idx]),
                anomaly_type="Unusual transaction amount",
                affected_fields=["amount", "vendor", "category"],
                severity="high" if z_scores[idx] > 4 else "medium",
                suggested_action=f"Review transaction ID {record.get('id', 'unknown')} for accuracy"
            ))

        # Check for unusual spending patterns by category
        if 'category' in financial_df.columns and 'date' in financial_df.columns:
            financial_df['date'] = pd.to_datetime(financial_df['date'])
            monthly_spending = financial_df.groupby([
                financial_df['date'].dt.to_period('M'),
                'category'
            ])['amount'].sum().abs()

            # Look for sudden spikes in spending by category
            for category in financial_df['category'].unique():
                category_monthly = monthly_spending.xs(category, level=1, drop_level=False)
                if len(category_monthly) > 2:
                    mean_spending = category_monthly.mean()
                    current_spending = category_monthly.iloc[-1] if len(category_monthly) > 0 else 0

                    if mean_spending > 0 and current_spending > mean_spending * 2:
                        anomalies.append(AnomalyDetectionResult(
                            is_anomaly=True,
                            anomaly_score=1.0,
                            anomaly_type=f"Sudden increase in {category} spending",
                            affected_fields=["amount", "category", "date"],
                            severity="medium",
                            suggested_action=f"Review {category} spending for the latest month"
                        ))

        return anomalies

    def detect_goal_anomalies(self, goals_df: pd.DataFrame) -> List[AnomalyDetectionResult]:
        """Detect anomalies in goal data"""
        anomalies = []

        if 'current_progress' not in goals_df.columns:
            return anomalies

        # Convert progress to numeric if needed
        goals_df['current_progress'] = pd.to_numeric(goals_df['current_progress'], errors='coerce')
        valid_progress = goals_df.dropna(subset=['current_progress'])

        if len(valid_progress) == 0:
            return anomalies

        # Look for goals with impossible progress values
        impossible_progress = valid_progress[
            (valid_progress['current_progress'] < 0) |
            (valid_progress['current_progress'] > 1)
        ]

        for idx in impossible_progress.index:
            record = valid_progress.loc[idx]
            anomalies.append(AnomalyDetectionResult(
                is_anomaly=True,
                anomaly_score=1.0,
                anomaly_type="Impossible progress value",
                affected_fields=["current_progress", "target_value", "current_value"],
                severity="critical",
                suggested_action=f"Correct progress value for goal {record.get('id', 'unknown')}: {record['current_progress']}"
            ))

        # Look for goals with negative progression
        if 'current_value' in goals_df.columns and 'target_value' in goals_df.columns:
            goals_df['current_value'] = pd.to_numeric(goals_df['current_value'], errors='coerce')
            goals_df['target_value'] = pd.to_numeric(goals_df['target_value'], errors='coerce')

            valid_goals = goals_df.dropna(subset=['current_value', 'target_value'])

            # Check if current value exceeds target significantly (could indicate data error)
            overachievers = valid_goals[
                (valid_goals['current_value'] > valid_goals['target_value'] * 2)
            ]

            for idx in overachievers.index:
                record = valid_goals.loc[idx]
                anomalies.append(AnomalyDetectionResult(
                    is_anomaly=True,
                    anomaly_score=1.0,
                    anomaly_type="Overachievement exceeding expectations",
                    affected_fields=["current_value", "target_value", "current_progress"],
                    severity="medium",
                    suggested_action=f"Verify accuracy of goal {record.get('id', 'unknown')} values"
                ))

        return anomalies


class TrendAnalyzer:
    """Analyzes trends in business data"""

    def __init__(self):
        self.logger = logger.bind(component="TrendAnalyzer")

    def analyze_task_trends(self, tasks_df: pd.DataFrame, period: str = "weekly") -> TrendAnalysisResult:
        """Analyze trends in task data"""
        if tasks_df.empty or 'created_date' not in tasks_df.columns:
            return TrendAnalysisResult("stable", 0.0, 0.0, period)

        tasks_df['created_date'] = pd.to_datetime(tasks_df['created_date'])
        tasks_df['period'] = tasks_df['created_date'].dt.to_period(period[0].upper())

        # Count tasks by period
        task_counts = tasks_df.groupby('period').size()

        if len(task_counts) < 2:
            return TrendAnalysisResult("stable", 0.0, 0.5, period)

        # Calculate trend using linear regression
        x = np.arange(len(task_counts))
        y = task_counts.values.astype(float)

        # Handle case where all values are the same
        if len(set(y)) == 1:
            return TrendAnalysisResult("stable", 0.0, 1.0, period)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        trend_strength = slope / (np.mean(y) + 1e-8)  # Normalize by mean to get relative strength
        confidence = min(1.0, r_value**2)  # R-squared as confidence

        if abs(trend_strength) < 0.01:  # Very weak trend
            trend_direction = "stable"
        elif trend_strength > 0.01:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"

        return TrendAnalysisResult(
            trend_direction=trend_direction,
            trend_strength=float(trend_strength),
            confidence=float(confidence),
            period=period
        )

    def analyze_financial_trends(self, financial_df: pd.DataFrame, period: str = "weekly") -> TrendAnalysisResult:
        """Analyze trends in financial data"""
        if financial_df.empty or 'date' not in financial_df.columns or 'amount' not in financial_df.columns:
            return TrendAnalysisResult("stable", 0.0, 0.0, period)

        financial_df['date'] = pd.to_datetime(financial_df['date'])
        financial_df['period'] = financial_df['date'].dt.to_period(period[0].upper())

        # Calculate net flow by period (income - expenses)
        financial_df['amount'] = pd.to_numeric(financial_df['amount'], errors='coerce')
        net_flows = financial_df.groupby('period')['amount'].sum()

        if len(net_flows) < 2:
            return TrendAnalysisResult("stable", 0.0, 0.5, period)

        # Calculate trend using linear regression
        x = np.arange(len(net_flows))
        y = net_flows.values.astype(float)

        # Handle case where all values are the same
        if len(set(y)) == 1:
            return TrendAnalysisResult("stable", 0.0, 1.0, period)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        trend_strength = slope / (np.mean(np.abs(y)) + 1e-8)  # Normalize by mean absolute value
        confidence = min(1.0, r_value**2)  # R-squared as confidence

        if abs(trend_strength) < 0.01:  # Very weak trend
            trend_direction = "stable"
        elif trend_strength > 0.01:
            trend_direction = "improving"  # Positive cash flow trend
        else:
            trend_direction = "declining"  # Negative cash flow trend

        return TrendAnalysisResult(
            trend_direction=trend_direction,
            trend_strength=float(trend_strength),
            confidence=float(confidence),
            period=period,
            forecast=self._generate_forecast(y, period)
        )

    def analyze_goal_trends(self, goals_df: pd.DataFrame, period: str = "weekly") -> TrendAnalysisResult:
        """Analyze trends in goal data"""
        if goals_df.empty or 'current_progress' not in goals_df.columns:
            return TrendAnalysisResult("stable", 0.0, 0.0, period)

        # Calculate average progress
        goals_df['current_progress'] = pd.to_numeric(goals_df['current_progress'], errors='coerce')
        avg_progress = goals_df['current_progress'].dropna().mean()

        # For goals, we can't really calculate a time-based trend without date information
        # So we'll return a stability indicator based on how close to target the average progress is
        if pd.isna(avg_progress):
            return TrendAnalysisResult("stable", 0.0, 0.0, period)

        if avg_progress >= 0.9:
            trend_direction = "ahead_of_schedule"
        elif avg_progress >= 0.7:
            trend_direction = "on_track"
        elif avg_progress >= 0.5:
            trend_direction = "behind_schedule"
        else:
            trend_direction = "significantly_behind"

        return TrendAnalysisResult(
            trend_direction=trend_direction,
            trend_strength=float(avg_progress),
            confidence=0.7,  # Medium confidence for goal progress
            period=period
        )

    def _generate_forecast(self, historical_data: np.array, period: str) -> Dict[str, float]:
        """Generate simple forecast based on historical data"""
        if len(historical_data) < 3:
            return {}

        # Simple linear extrapolation
        x = np.arange(len(historical_data))
        slope, intercept = np.polyfit(x, historical_data, 1)

        # Forecast next period
        next_x = len(historical_data)
        forecast_value = slope * next_x + intercept

        return {
            "next_period_estimate": float(forecast_value),
            "trend_slope": float(slope)
        }


class CorrelationAnalyzer:
    """Analyzes correlations between different business metrics"""

    def __init__(self):
        self.logger = logger.bind(component="CorrelationAnalyzer")

    def analyze_correlations(self, tasks_df: pd.DataFrame, financial_df: pd.DataFrame,
                           goals_df: pd.DataFrame) -> CorrelationAnalysisResult:
        """Analyze correlations between task, financial, and goal data"""
        correlations = {}

        # Prepare numerical data for correlation analysis
        numerical_data = pd.DataFrame()

        # Add task-related metrics if available
        if not tasks_df.empty:
            if 'status' in tasks_df.columns:
                # Create a completion rate metric
                completion_rate = (tasks_df['status'] == 'completed').mean()
                numerical_data['task_completion_rate'] = [completion_rate] * max(len(tasks_df), len(financial_df), len(goals_df))

        # Add financial metrics if available
        if not financial_df.empty and 'amount' in financial_df.columns:
            financial_df['amount'] = pd.to_numeric(financial_df['amount'], errors='coerce')
            avg_amount = financial_df['amount'].mean()
            total_amount = financial_df['amount'].sum()
            numerical_data['avg_transaction_amount'] = [avg_amount] * max(len(tasks_df), len(financial_df), len(goals_df))
            numerical_data['total_financial_flow'] = [total_amount] * max(len(tasks_df), len(financial_df), len(goals_df))

        # Add goal metrics if available
        if not goals_df.empty and 'current_progress' in goals_df.columns:
            goals_df['current_progress'] = pd.to_numeric(goals_df['current_progress'], errors='coerce')
            avg_progress = goals_df['current_progress'].mean()
            numerical_data['average_goal_progress'] = [avg_progress] * max(len(tasks_df), len(financial_df), len(goals_df))

        # Calculate correlations
        correlation_pairs = []
        if len(numerical_data.columns) > 1:
            corr_matrix = numerical_data.corr()

            # Extract correlation pairs above threshold
            for col1 in corr_matrix.columns:
                for col2 in corr_matrix.columns:
                    if col1 != col2 and abs(corr_matrix.loc[col1, col2]) > 0.3:  # Threshold for significance
                        correlation_pairs.append((col1, col2, corr_matrix.loc[col1, col2]))
        else:
            corr_matrix = pd.DataFrame()  # Empty matrix

        # Identify potential causation indicators
        causation_indicators = []
        if 'task_completion_rate' in numerical_data.columns and 'average_goal_progress' in numerical_data.columns:
            if abs(numerical_data['task_completion_rate'].iloc[0] - numerical_data['average_goal_progress'].iloc[0]) < 0.1:
                causation_indicators.append("Task completion rate aligns with goal progress, suggesting correlation")

        return CorrelationAnalysisResult(
            correlated_pairs=[(pair[0], pair[1]) for pair in correlation_pairs],  # Just the pairs, not the values
            correlation_matrix=corr_matrix.to_dict() if not corr_matrix.empty else {},
            causation_indicators=causation_indicators
        )


class AdvancedDataAnalyzer:
    """Advanced data analysis system combining all analysis capabilities"""

    def __init__(self):
        self.validator = DataValidator()
        self.anomaly_detector = AnomalyDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.logger = logger.bind(component="AdvancedDataAnalyzer")

    def analyze_complete_dataset(self, tasks: List[Dict], financial: List[Dict], goals: List[Dict]) -> Dict[str, Any]:
        """Analyze a complete dataset with tasks, financial, and goal data"""
        # Convert to DataFrames
        tasks_df = pd.DataFrame(tasks) if tasks else pd.DataFrame()
        financial_df = pd.DataFrame(financial) if financial else pd.DataFrame()
        goals_df = pd.DataFrame(goals) if goals else pd.DataFrame()

        # Validate data quality
        task_quality = self.validator.validate_task_data(tasks)
        financial_quality = self.validator.validate_financial_data(financial)
        goal_quality = self.validator.validate_goal_data(goals)

        # Detect anomalies
        task_anomalies = self.anomaly_detector.detect_task_anomalies(tasks_df) if not tasks_df.empty else []
        financial_anomalies = self.anomaly_detector.detect_financial_anomalies(financial_df) if not financial_df.empty else []
        goal_anomalies = self.anomaly_detector.detect_goal_anomalies(goals_df) if not goals_df.empty else []

        # Analyze trends
        task_trends = self.trend_analyzer.analyze_task_trends(tasks_df) if not tasks_df.empty else None
        financial_trends = self.trend_analyzer.analyze_financial_trends(financial_df) if not financial_df.empty else None
        goal_trends = self.trend_analyzer.analyze_goal_trends(goals_df) if not goals_df.empty else None

        # Analyze correlations
        correlations = self.correlation_analyzer.analyze_correlations(tasks_df, financial_df, goals_df)

        # Compile results
        analysis_results = {
            "data_quality": {
                "tasks": asdict(task_quality),
                "financial": asdict(financial_quality),
                "goals": asdict(goal_quality)
            },
            "anomalies": {
                "tasks": [asdict(anomaly) for anomaly in task_anomalies],
                "financial": [asdict(anomaly) for anomaly in financial_anomalies],
                "goals": [asdict(anomaly) for anomaly in goal_anomalies]
            },
            "trends": {
                "tasks": asdict(task_trends) if task_trends else None,
                "financial": asdict(financial_trends) if financial_trends else None,
                "goals": asdict(goal_trends) if goal_trends else None
            },
            "correlations": {
                "correlated_pairs": correlations.correlated_pairs,
                "matrix": correlations.correlation_matrix,
                "causation_indicators": correlations.causation_indicators
            },
            "summary": {
                "total_tasks": len(tasks),
                "total_financial_records": len(financial),
                "total_goals": len(goals),
                "quality_score": self._calculate_overall_quality_score([task_quality, financial_quality, goal_quality]),
                "anomaly_count": len(task_anomalies) + len(financial_anomalies) + len(goal_anomalies)
            }
        }

        self.logger.info("Complete dataset analysis completed",
                        total_records=len(tasks) + len(financial) + len(goals),
                        anomaly_count=analysis_results["summary"]["anomaly_count"])

        return analysis_results

    def _calculate_overall_quality_score(self, quality_metrics: List[DataQualityMetrics]) -> float:
        """Calculate overall data quality score from multiple sources"""
        if not quality_metrics:
            return 0.0

        total_score = sum(metric.overall_score for metric in quality_metrics)
        return total_score / len(quality_metrics)


# Backward compatibility with the analysis in business_audit_core
class LegacyDataAnalyzerAdapter:
    """Adapts the new advanced analyzer to work with the legacy system"""

    def __init__(self):
        self.advanced_analyzer = AdvancedDataAnalyzer()

    def analyze_tasks(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Analyze tasks in the format expected by the legacy system"""
        from business_audit_core import DataAnalyzer as LegacyAnalyzer
        legacy = LegacyAnalyzer()

        # Use the legacy analyzer for basic metrics
        legacy_result = legacy.analyze_tasks(tasks)

        # Enhance with advanced analysis
        if tasks:
            df = pd.DataFrame(tasks)
            anomalies = self.advanced_analyzer.anomaly_detector.detect_task_anomalies(df)
            trend = self.advanced_analyzer.trend_analyzer.analyze_task_trends(df)

            # Add advanced metrics to legacy result
            legacy_result["anomalies_detected"] = len(anomalies)
            legacy_result["trend_analysis"] = {
                "direction": trend.trend_direction if trend else "unknown",
                "strength": trend.trend_strength if trend else 0.0,
                "confidence": trend.confidence if trend else 0.0
            }

        return legacy_result

    def analyze_finances(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze finances in the format expected by the legacy system"""
        from business_audit_core import DataAnalyzer as LegacyAnalyzer
        legacy = LegacyAnalyzer()

        # Use the legacy analyzer for basic metrics
        legacy_result = legacy.analyze_finances(transactions)

        # Enhance with advanced analysis
        if transactions:
            df = pd.DataFrame(transactions)
            anomalies = self.advanced_analyzer.anomaly_detector.detect_financial_anomalies(df)
            trend = self.advanced_analyzer.trend_analyzer.analyze_financial_trends(df)

            # Add advanced metrics to legacy result
            legacy_result["anomalies_detected"] = len(anomalies)
            legacy_result["trend_analysis"] = {
                "direction": trend.trend_direction if trend else "unknown",
                "strength": trend.trend_strength if trend else 0.0,
                "confidence": trend.confidence if trend else 0.0
            }

        return legacy_result

    def analyze_goals(self, goals: List[Dict]) -> Dict[str, Any]:
        """Analyze goals in the format expected by the legacy system"""
        from business_audit_core import DataAnalyzer as LegacyAnalyzer
        legacy = LegacyAnalyzer()

        # Use the legacy analyzer for basic metrics
        legacy_result = legacy.analyze_goals(goals)

        # Enhance with advanced analysis
        if goals:
            df = pd.DataFrame(goals)
            anomalies = self.advanced_analyzer.anomaly_detector.detect_goal_anomalies(df)
            trend = self.advanced_analyzer.trend_analyzer.analyze_goal_trends(df)

            # Add advanced metrics to legacy result
            legacy_result["anomalies_detected"] = len(anomalies)
            legacy_result["trend_analysis"] = {
                "direction": trend.trend_direction if trend else "unknown",
                "strength": trend.trend_strength if trend else 0.0,
                "confidence": trend.confidence if trend else 0.0
            }

        return legacy_result


def create_sample_data_analyzer():
    """Create and return a configured data analyzer"""
    return AdvancedDataAnalyzer()


if __name__ == "__main__":
    # Demo of data analyzer functionality
    print("Data Analyzer Demo")
    print("=" * 40)

    # Create sample data
    from business_audit_core import create_sample_tasks, create_sample_transactions, create_sample_goals

    print("Creating sample data...")
    tasks = create_sample_tasks(50)
    financial = create_sample_transactions(50)
    goals = create_sample_goals(15)

    print(f"Created {len(tasks)} tasks, {len(financial)} financial records, {len(goals)} goals")

    # Create analyzer and run analysis
    analyzer = AdvancedDataAnalyzer()

    print("\nRunning complete dataset analysis...")
    results = analyzer.analyze_complete_dataset(
        [task.__dict__ for task in tasks],
        [trans.__dict__ for trans in financial],
        [goal.__dict__ for goal in goals]
    )

    print(f"\nAnalysis Summary:")
    print(f"  Quality Score: {results['summary']['quality_score']:.2f}")
    print(f"  Anomalies Found: {results['summary']['anomaly_count']}")
    print(f"  Data Records: {results['summary']['total_tasks']} tasks, {results['summary']['total_financial_records']} financial, {results['summary']['total_goals']} goals")

    print(f"\nTask Quality: {results['data_quality']['tasks']['overall_score']:.2f}")
    print(f"Financial Quality: {results['data_quality']['financial']['overall_score']:.2f}")
    print(f"Goal Quality: {results['data_quality']['goals']['overall_score']:.2f}")

    print(f"\nTrend Analysis:")
    if results['trends']['tasks']:
        print(f"  Tasks: {results['trends']['tasks']['trend_direction']} (strength: {results['trends']['tasks']['trend_strength']:.2f})")
    if results['trends']['financial']:
        print(f"  Finance: {results['trends']['financial']['trend_direction']} (strength: {results['trends']['financial']['trend_strength']:.2f})")
    if results['trends']['goals']:
        print(f"  Goals: {results['trends']['goals']['trend_direction']} (strength: {results['trends']['goals']['trend_strength']:.2f})")

    print(f"\nCorrelations Found: {len(results['correlations']['correlated_pairs'])}")
    for pair in results['correlations']['correlated_pairs'][:3]:  # Show first 3
        print(f"  {pair[0]} <-> {pair[1]}")