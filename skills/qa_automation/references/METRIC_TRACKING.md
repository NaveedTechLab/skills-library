# Metric Tracking for QA Automation

## Overview

This document provides comprehensive guidance on implementing performance and quality metric tracking in a pytest-based test suite. It covers latency tracking, accuracy measurement, escalation rate monitoring, and reporting mechanisms.

## Performance Metric Tracking

### 1. Latency Measurement and Tracking

```python
# tests/metrics/test_latency_tracking.py
import pytest
import time
import statistics
from collections import deque, defaultdict
from datetime import datetime, timedelta
import json
import csv
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class OperationType(Enum):
    """Types of operations to track"""
    CUSTOMER_CREATION = "customer_creation"
    TICKET_CREATION = "ticket_creation"
    DATA_QUERY = "data_query"
    API_CALL = "api_call"
    AUTHENTICATION = "authentication"
    NOTIFICATION = "notification"

@dataclass
class LatencySample:
    """Single latency measurement"""
    operation: OperationType
    duration: float  # in seconds
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

class LatencyTracker:
    """Latency tracking system"""

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.samples: Dict[OperationType, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.aggregated_stats = defaultdict(dict)

    def record_latency(self, operation: OperationType, duration: float,
                      success: bool = True, error_message: Optional[str] = None,
                      tags: Optional[Dict[str, str]] = None):
        """Record a latency measurement"""
        sample = LatencySample(
            operation=operation,
            duration=duration,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
            tags=tags
        )

        self.samples[operation].append(sample)

    def get_current_stats(self, operation: OperationType,
                         time_window_minutes: int = 5) -> Dict[str, float]:
        """Get current latency statistics for an operation"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)

        # Filter samples within time window
        recent_samples = [
            sample for sample in self.samples[operation]
            if sample.timestamp >= cutoff_time
        ]

        if not recent_samples:
            return {}

        durations = [s.duration for s in recent_samples if s.success]

        if not durations:
            return {}

        # Calculate statistics
        stats = {
            'count': len(recent_samples),
            'success_count': len(durations),
            'failure_count': len(recent_samples) - len(durations),
            'success_rate': len(durations) / len(recent_samples),
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'min': min(durations),
            'max': max(durations),
            'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0
        }

        # Calculate percentiles
        sorted_durations = sorted(durations)
        if sorted_durations:
            stats['p90'] = sorted_durations[int(0.90 * len(sorted_durations))]
            stats['p95'] = sorted_durations[int(0.95 * len(sorted_durations))]
            stats['p99'] = sorted_durations[int(0.99 * len(sorted_durations))]

        return stats

    def get_trend_data(self, operation: OperationType,
                      hours_back: int = 24) -> List[Dict]:
        """Get trend data for plotting"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        hourly_data = defaultdict(list)

        for sample in self.samples[operation]:
            if sample.timestamp >= cutoff_time:
                hour_key = sample.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_key].append(sample)

        trend_data = []
        for hour, samples in sorted(hourly_data.items()):
            durations = [s.duration for s in samples if s.success]

            if durations:
                trend_data.append({
                    'timestamp': hour.isoformat(),
                    'avg_latency': statistics.mean(durations),
                    'min_latency': min(durations),
                    'max_latency': max(durations),
                    'p95_latency': sorted(durations)[int(0.95 * len(durations))] if durations else 0,
                    'total_requests': len(samples),
                    'success_rate': len(durations) / len(samples)
                })

        return trend_data

    def export_to_csv(self, operation: OperationType, filepath: str):
        """Export latency data to CSV"""
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'operation', 'duration', 'success', 'error_message']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for sample in self.samples[operation]:
                writer.writerow({
                    'timestamp': sample.timestamp.isoformat(),
                    'operation': sample.operation.value,
                    'duration': sample.duration,
                    'success': sample.success,
                    'error_message': sample.error_message or ''
                })

# Global latency tracker instance
LATENCY_TRACKER = LatencyTracker()

class LatencyMeasurement:
    """Context manager for measuring latency"""

    def __init__(self, operation: OperationType, tags: Optional[Dict[str, str]] = None):
        self.operation = operation
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time

        success = exc_type is None
        error_message = str(exc_val) if exc_type else None

        LATENCY_TRACKER.record_latency(
            operation=self.operation,
            duration=duration,
            success=success,
            error_message=error_message,
            tags=self.tags
        )

@pytest.fixture
def latency_tracker():
    """Latency tracker fixture"""
    return LATENCY_TRACKER

def test_customer_creation_latency(latency_tracker):
    """Test customer creation with latency tracking"""
    import requests

    with LatencyMeasurement(OperationType.CUSTOMER_CREATION, tags={'test_case': 'basic_creation'}):
        response = requests.post("https://test-api.myapp.com/customers", json={
            'name': 'Latency Test User',
            'email': 'latency@test.com',
            'phone': '+1234567890'
        })

    # Verify response
    assert response.status_code in [200, 201]

    # Check current stats
    stats = latency_tracker.get_current_stats(OperationType.CUSTOMER_CREATION)

    print(f"Customer Creation Stats: {stats}")

    # Assert performance requirements
    assert stats.get('mean', float('inf')) < 0.5, f"Mean latency too high: {stats.get('mean', 0)}"
    assert stats.get('p95', float('inf')) < 1.0, f"P95 latency too high: {stats.get('p95', 0)}"

def test_api_endpoint_latency_tracking(latency_tracker):
    """Test API endpoint with comprehensive latency tracking"""
    import requests

    # Test multiple operations
    operations = [
        ('POST', '/customers'),
        ('GET', '/customers/1'),
        ('PUT', '/customers/1'),
        ('DELETE', '/customers/1')
    ]

    for method, endpoint in operations:
        with LatencyMeasurement(
            OperationType.API_CALL,
            tags={'method': method, 'endpoint': endpoint}
        ):
            if method == 'POST':
                response = requests.post(f"https://test-api.myapp.com{endpoint}", json={
                    'name': 'API Test User',
                    'email': 'api@test.com',
                    'phone': '+1234567890'
                })
            elif method == 'GET':
                response = requests.get(f"https://test-api.myapp.com{endpoint}")
            elif method == 'PUT':
                response = requests.put(f"https://test-api.myapp.com{endpoint}", json={
                    'name': 'Updated User'
                })
            elif method == 'DELETE':
                response = requests.delete(f"https://test-api.myapp.com{endpoint}")

    # Get comprehensive stats
    stats = latency_tracker.get_current_stats(OperationType.API_CALL)

    print(f"API Call Stats: {stats}")

    # Verify performance metrics
    assert stats['success_rate'] >= 0.95
    assert stats.get('mean', float('inf')) < 1.0
```

### 2. Accuracy Measurement

```python
# tests/metrics/test_accuracy_measurement.py
import pytest
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class ClassificationResult:
    """Result of a classification operation"""
    predicted: str
    actual: str
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = None

class AccuracyTracker:
    """Accuracy tracking system"""

    def __init__(self):
        self.classification_results: List[ClassificationResult] = []

    def record_classification(self, predicted: str, actual: str,
                           confidence: float = 1.0,
                           metadata: Dict[str, Any] = None):
        """Record a classification result"""
        result = ClassificationResult(
            predicted=predicted,
            actual=actual,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.classification_results.append(result)

    def get_overall_accuracy(self) -> float:
        """Get overall accuracy rate"""
        if not self.classification_results:
            return 0.0

        correct_predictions = sum(
            1 for result in self.classification_results
            if result.predicted == result.actual
        )
        return correct_predictions / len(self.classification_results)

    def get_accuracy_by_category(self) -> Dict[str, float]:
        """Get accuracy rate by category"""
        category_counts = {}
        category_correct = {}

        for result in self.classification_results:
            category = result.actual
            if category not in category_counts:
                category_counts[category] = 0
                category_correct[category] = 0

            category_counts[category] += 1
            if result.predicted == result.actual:
                category_correct[category] += 1

        return {
            category: category_correct[category] / category_counts[category]
            for category in category_counts
        }

    def get_sklearn_metrics(self) -> Dict[str, float]:
        """Get detailed sklearn-style metrics"""
        if not self.classification_results:
            return {}

        y_true = [r.actual for r in self.classification_results]
        y_pred = [r.predicted for r in self.classification_results]

        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro'),
            'precision_micro': precision_score(y_true, y_pred, average='micro'),
            'recall_macro': recall_score(y_true, y_pred, average='macro'),
            'recall_micro': recall_score(y_true, y_pred, average='micro'),
            'f1_macro': f1_score(y_true, y_pred, average='macro'),
            'f1_micro': f1_score(y_true, y_pred, average='micro')
        }

        return metrics

    def get_confidence_correlation(self) -> float:
        """Get correlation between confidence and correctness"""
        if not self.classification_results:
            return 0.0

        confidences = []
        correctness = []  # 1 for correct, 0 for incorrect

        for result in self.classification_results:
            confidences.append(result.confidence)
            correctness.append(1 if result.predicted == result.actual else 0)

        if len(set(confidences)) == 1:  # All confidences are the same
            return 0.0

        correlation_matrix = np.corrcoef(confidences, correctness)
        return correlation_matrix[0, 1]

    def get_trend_analysis(self, days_back: int = 7) -> Dict[str, Any]:
        """Get trend analysis for recent accuracy"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_back)

        recent_results = [
            r for r in self.classification_results
            if r.timestamp >= cutoff_date
        ]

        if not recent_results:
            return {}

        # Calculate daily accuracy
        daily_accuracy = {}
        for result in recent_results:
            day = result.timestamp.date()
            if day not in daily_accuracy:
                daily_accuracy[day] = {'total': 0, 'correct': 0}

            daily_accuracy[day]['total'] += 1
            if result.predicted == result.actual:
                daily_accuracy[day]['correct'] += 1

        # Calculate daily accuracy rates
        daily_rates = {
            str(day): data['correct'] / data['total']
            for day, data in daily_accuracy.items()
        }

        # Calculate improvement trend
        daily_values = list(daily_rates.values())
        if len(daily_values) > 1:
            trend = (daily_values[-1] - daily_values[0]) / len(daily_values)
        else:
            trend = 0

        return {
            'daily_accuracy_rates': daily_rates,
            'overall_recent_accuracy': sum(d['correct'] for d in daily_accuracy.values()) /
                                     sum(d['total'] for d in daily_accuracy.values()),
            'improvement_trend': trend,
            'total_evaluations': len(recent_results)
        }

    def export_results(self, filepath: str):
        """Export classification results to JSON"""
        results_data = [
            {
                'predicted': r.predicted,
                'actual': r.actual,
                'confidence': r.confidence,
                'timestamp': r.timestamp.isoformat(),
                'metadata': r.metadata
            }
            for r in self.classification_results
        ]

        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)

ACCURACY_TRACKER = AccuracyTracker()

@pytest.fixture
def accuracy_tracker():
    """Accuracy tracker fixture"""
    return ACCURACY_TRACKER

def test_classification_accuracy(accuracy_tracker):
    """Test classification accuracy tracking"""
    # Simulate classification results
    test_cases = [
        ('account', 'account', 0.95),
        ('billing', 'billing', 0.88),
        ('technical', 'technical', 0.92),
        ('account', 'billing', 0.75),  # Incorrect classification
        ('general', 'general', 0.90),
        ('account', 'account', 0.96),
        ('billing', 'account', 0.65),  # Incorrect classification
        ('technical', 'technical', 0.94),
    ]

    for predicted, actual, confidence in test_cases:
        accuracy_tracker.record_classification(predicted, actual, confidence)

    # Check overall accuracy
    overall_accuracy = accuracy_tracker.get_overall_accuracy()
    assert overall_accuracy >= 0.75, f"Overall accuracy too low: {overall_accuracy}"

    # Check category-specific accuracy
    category_accuracy = accuracy_tracker.get_accuracy_by_category()
    print(f"Category accuracy: {category_accuracy}")

    # Check detailed metrics
    detailed_metrics = accuracy_tracker.get_sklearn_metrics()
    print(f"Detailed metrics: {detailed_metrics}")

    # Check confidence correlation
    confidence_corr = accuracy_tracker.get_confidence_correlation()
    print(f"Confidence correlation: {confidence_corr}")

    # Assert accuracy requirements
    assert detailed_metrics['accuracy'] >= 0.75
    assert detailed_metrics['f1_macro'] >= 0.70

def test_automated_resolution_accuracy(accuracy_tracker):
    """Test automated resolution accuracy"""
    # Simulate customer support query resolution
    queries_and_resolutions = [
        # (query, expected_resolution, actual_resolution, confidence)
        ("Reset my password", "password_reset", "password_reset", 0.95),
        ("Invoice issue", "billing_issue", "billing_issue", 0.88),
        ("App crashes", "technical_support", "technical_support", 0.92),
        ("Change plan", "plan_change", "billing_issue", 0.70),  # Incorrect
        ("Contact sales", "sales_contact", "sales_contact", 0.90),
        ("Update payment", "payment_update", "payment_update", 0.96),
        ("Bug report", "technical_support", "account_issue", 0.65),  # Incorrect
        ("Feature request", "feature_request", "feature_request", 0.89),
    ]

    for query, expected, actual, confidence in queries_and_resolutions:
        accuracy_tracker.record_classification(
            predicted=actual,
            actual=expected,
            confidence=confidence,
            metadata={'query': query}
        )

    # Verify accuracy meets requirements
    accuracy = accuracy_tracker.get_overall_accuracy()
    assert accuracy >= 0.75, f"Resolution accuracy too low: {accuracy}"

    print(f"Automated resolution accuracy: {accuracy}")
```

### 3. Escalation Rate Tracking

```python
# tests/metrics/test_escalation_tracking.py
import pytest
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import statistics

class EscalationReason(Enum):
    """Reasons for escalation"""
    COMPLEX_ISSUE = "complex_issue"
    CUSTOMER_UNSATISFIED = "customer_unsatisfied"
    TECHNICAL_LIMITATION = "technical_limitation"
    TIME_CONSTRAINT = "time_constraint"
    POLICY_VIOLATION = "policy_violation"
    UNKNOWN = "unknown"

class ResolutionOutcome(Enum):
    """Outcomes of resolution attempts"""
    RESOLVED_AUTOMATICALLY = "resolved_automatically"
    ESCALATED_TO_AGENT = "escalated_to_agent"
    ESCALATED_TO_SPECIALIST = "escalated_to_specialist"
    RESOLUTION_FAILED = "resolution_failed"
    CUSTOMER_HUNG_UP = "customer_hung_up"

@dataclass
class InteractionRecord:
    """Record of a customer interaction"""
    interaction_id: str
    customer_id: str
    query: str
    resolution_outcome: ResolutionOutcome
    escalation_reason: Optional[EscalationReason] = None
    resolution_time: float  # in seconds
    resolution_attempts: int = 1
    agent_handoff_required: bool = False
    timestamp: datetime = None
    metadata: Dict[str, any] = None

class EscalationTracker:
    """Escalation rate tracking system"""

    def __init__(self):
        self.interactions: List[InteractionRecord] = []
        self.escalation_reasons: Dict[EscalationReason, int] = defaultdict(int)

    def record_interaction(self, interaction_id: str, customer_id: str,
                          query: str, resolution_outcome: ResolutionOutcome,
                          escalation_reason: Optional[EscalationReason] = None,
                          resolution_time: float = 0.0,
                          resolution_attempts: int = 1,
                          agent_handoff_required: bool = False,
                          metadata: Dict[str, any] = None):
        """Record a customer interaction"""
        record = InteractionRecord(
            interaction_id=interaction_id,
            customer_id=customer_id,
            query=query,
            resolution_outcome=resolution_outcome,
            escalation_reason=escalation_reason,
            resolution_time=resolution_time,
            resolution_attempts=resolution_attempts,
            agent_handoff_required=agent_handoff_required,
            timestamp=datetime.now(),
            metadata=metadata
        )

        self.interactions.append(record)

        if escalation_reason:
            self.escalation_reasons[escalation_reason] += 1

    def get_escalation_rate(self, time_window_hours: int = 24) -> float:
        """Get escalation rate within time window"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        recent_interactions = [
            i for i in self.interactions
            if i.timestamp >= cutoff_time
        ]

        if not recent_interactions:
            return 0.0

        escalated_interactions = [
            i for i in recent_interactions
            if i.resolution_outcome in [ResolutionOutcome.ESCALATED_TO_AGENT,
                                      ResolutionOutcome.ESCALATED_TO_SPECIALIST]
        ]

        return len(escalated_interactions) / len(recent_interactions)

    def get_resolution_distribution(self) -> Dict[ResolutionOutcome, float]:
        """Get distribution of resolution outcomes"""
        if not self.interactions:
            return {}

        outcome_counts = defaultdict(int)
        for interaction in self.interactions:
            outcome_counts[interaction.resolution_outcome] += 1

        return {
            outcome: count / len(self.interactions)
            for outcome, count in outcome_counts.items()
        }

    def get_escalation_reasons_breakdown(self) -> Dict[EscalationReason, float]:
        """Get breakdown of escalation reasons"""
        if not self.escalation_reasons:
            return {}

        total_escalations = sum(self.escalation_reasons.values())
        return {
            reason: count / total_escalations
            for reason, count in self.escalation_reasons.items()
        }

    def get_time_based_metrics(self, time_window_hours: int = 24) -> Dict[str, float]:
        """Get time-based performance metrics"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        recent_interactions = [
            i for i in self.interactions
            if i.timestamp >= cutoff_time
        ]

        if not recent_interactions:
            return {}

        resolution_times = [i.resolution_time for i in recent_interactions]
        resolution_attempts = [i.resolution_attempts for i in recent_interactions]

        metrics = {}

        if resolution_times:
            metrics.update({
                'avg_resolution_time': statistics.mean(resolution_times),
                'median_resolution_time': statistics.median(resolution_times),
                'p95_resolution_time': sorted(resolution_times)[int(0.95 * len(resolution_times))],
                'min_resolution_time': min(resolution_times),
                'max_resolution_time': max(resolution_times)
            })

        if resolution_attempts:
            metrics['avg_resolution_attempts'] = statistics.mean(resolution_attempts)

        return metrics

    def get_first_contact_resolution_rate(self) -> float:
        """Get first contact resolution rate"""
        if not self.interactions:
            return 0.0

        resolved_on_first_attempt = [
            i for i in self.interactions
            if i.resolution_attempts == 1 and i.resolution_outcome == ResolutionOutcome.RESOLVED_AUTOMATICALLY
        ]

        return len(resolved_on_first_attempt) / len(self.interactions)

    def get_trend_analysis(self, days_back: int = 7) -> Dict[str, any]:
        """Get trend analysis for escalation metrics"""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        daily_metrics = defaultdict(list)

        for interaction in self.interactions:
            if interaction.timestamp.date() >= cutoff_date.date():
                day = interaction.timestamp.date()

                # Calculate daily metrics
                daily_metrics[day].append(interaction)

        trend_data = {}
        for day, day_interactions in daily_metrics.items():
            total = len(day_interactions)
            resolved_auto = len([i for i in day_interactions
                               if i.resolution_outcome == ResolutionOutcome.RESOLVED_AUTOMATICALLY])
            escalated = len([i for i in day_interactions
                           if i.resolution_outcome in [ResolutionOutcome.ESCALATED_TO_AGENT,
                                                     ResolutionOutcome.ESCALATED_TO_SPECIALIST]])

            if total > 0:
                trend_data[str(day)] = {
                    'total_interactions': total,
                    'resolution_rate': resolved_auto / total,
                    'escalation_rate': escalated / total,
                    'avg_resolution_time': statistics.mean([i.resolution_time for i in day_interactions])
                }

        return trend_data

ESC_TRACKER = EscalationTracker()

@pytest.fixture
def escalation_tracker():
    """Escalation tracker fixture"""
    return ESC_TRACKER

def test_escalation_rate_tracking(escalation_tracker):
    """Test escalation rate tracking"""
    # Simulate customer interactions
    test_interactions = [
        # (outcome, reason, time, attempts)
        (ResolutionOutcome.RESOLVED_AUTOMATICALLY, None, 45.0, 1),
        (ResolutionOutcome.ESCALATED_TO_AGENT, EscalationReason.COMPLEX_ISSUE, 120.0, 2),
        (ResolutionOutcome.RESOLVED_AUTOMATICALLY, None, 30.0, 1),
        (ResolutionOutcome.ESCALATED_TO_SPECIALIST, EscalationReason.TECHNICAL_LIMITATION, 180.0, 3),
        (ResolutionOutcome.RESOLVED_AUTOMATICALLY, None, 60.0, 1),
        (ResolutionOutcome.ESCALATED_TO_AGENT, EscalationReason.CUSTOMER_UNSATISFIED, 90.0, 2),
        (ResolutionOutcome.RESOLVED_AUTOMATICALLY, None, 40.0, 1),
        (ResolutionOutcome.RESOLUTION_FAILED, EscalationReason.UNKNOWN, 200.0, 4),
    ]

    for i, (outcome, reason, time_taken, attempts) in enumerate(test_interactions):
        escalation_tracker.record_interaction(
            interaction_id=f"interaction_{i}",
            customer_id=f"customer_{i}",
            query=f"Query {i}",
            resolution_outcome=outcome,
            escalation_reason=reason,
            resolution_time=time_taken,
            resolution_attempts=attempts
        )

    # Check escalation rate
    escalation_rate = escalation_tracker.get_escalation_rate(time_window_hours=1)
    print(f"Escalation rate: {escalation_rate:.2%}")

    # Check resolution distribution
    resolution_dist = escalation_tracker.get_resolution_distribution()
    print(f"Resolution distribution: {resolution_dist}")

    # Check escalation reasons
    reasons_breakdown = escalation_tracker.get_escalation_reasons_breakdown()
    print(f"Escalation reasons: {reasons_breakdown}")

    # Check time-based metrics
    time_metrics = escalation_tracker.get_time_based_metrics()
    print(f"Time metrics: {time_metrics}")

    # Check first contact resolution rate
    fcr_rate = escalation_tracker.get_first_contact_resolution_rate()
    print(f"First contact resolution rate: {fcr_rate:.2%}")

    # Assert requirements
    assert escalation_rate <= 0.5, f"Escalation rate too high: {escalation_rate:.2%}"
    assert fcr_rate >= 0.5, f"FCR rate too low: {fcr_rate:.2%}"

def test_automated_vs_manual_resolution(escalation_tracker):
    """Test comparison between automated and manual resolution"""
    import random

    # Simulate a mix of automated and complex queries
    automated_queries = [
        "Reset my password",
        "Update my email",
        "Cancel subscription",
        "Change plan",
        "Update payment method"
    ]

    complex_queries = [
        "Complex billing dispute",
        "Integration issue with third-party app",
        "Data migration problem",
        "Custom feature request",
        "Enterprise account setup"
    ]

    # Process automated queries (higher success rate)
    for i, query in enumerate(automated_queries * 3):  # 15 automated interactions
        success = random.random() > 0.1  # 90% success rate for automated
        outcome = ResolutionOutcome.RESOLVED_AUTOMATICALLY if success else ResolutionOutcome.ESCALATED_TO_AGENT

        escalation_tracker.record_interaction(
            interaction_id=f"auto_{i}",
            customer_id=f"auto_cust_{i}",
            query=query,
            resolution_outcome=outcome,
            resolution_time=random.uniform(30, 90),  # 30-90 seconds for automated
            resolution_attempts=1 if success else random.randint(1, 3)
        )

    # Process complex queries (lower success rate)
    for i, query in enumerate(complex_queries * 5):  # 25 complex interactions
        success = random.random() > 0.7  # 30% success rate for complex
        outcome = ResolutionOutcome.RESOLVED_AUTOMATICALLY if success else ResolutionOutcome.ESCALATED_TO_SPECIALIST

        escalation_tracker.record_interaction(
            interaction_id=f"complex_{i}",
            customer_id=f"complex_cust_{i}",
            query=query,
            resolution_outcome=outcome,
            escalation_reason=EscalationReason.COMPLEX_ISSUE if not success else None,
            resolution_time=random.uniform(120, 300),  # 2-5 minutes for complex
            resolution_attempts=1 if success else random.randint(2, 5)
        )

    # Get overall metrics
    total_interactions = len(escalation_tracker.interactions)
    escalation_rate = escalation_tracker.get_escalation_rate()
    fcr_rate = escalation_tracker.get_first_contact_resolution_rate()
    time_metrics = escalation_tracker.get_time_based_metrics()

    print(f"Total interactions: {total_interactions}")
    print(f"Overall escalation rate: {escalation_rate:.2%}")
    print(f"First contact resolution rate: {fcr_rate:.2%}")
    print(f"Average resolution time: {time_metrics.get('avg_resolution_time', 0):.2f}s")

    # These metrics should reflect the mix of automated and complex queries
    assert total_interactions == 40
    assert 0.1 <= escalation_rate <= 0.6  # Should be between 10% and 60%
    assert 0.3 <= fcr_rate <= 0.9  # Should be between 30% and 90%
```

## Comprehensive Metrics Dashboard

### 1. Metrics Aggregation and Reporting

```python
# tests/metrics/test_comprehensive_metrics.py
import pytest
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import seaborn as sns

class MetricsDashboard:
    """Comprehensive metrics dashboard combining all tracking systems"""

    def __init__(self, latency_tracker, accuracy_tracker, escalation_tracker):
        self.latency_tracker = latency_tracker
        self.accuracy_tracker = accuracy_tracker
        self.escalation_tracker = escalation_tracker

    def generate_comprehensive_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate comprehensive metrics report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'time_period': f'Last {days_back} days',
            'performance_metrics': {},
            'quality_metrics': {},
            'escalation_metrics': {},
            'recommendations': []
        }

        # Add performance metrics
        for op_type in OperationType:
            stats = self.latency_tracker.get_current_stats(op_type, time_window_minutes=days_back*24*60)
            if stats:
                report['performance_metrics'][op_type.value] = stats

        # Add quality metrics
        report['quality_metrics'] = {
            'overall_accuracy': self.accuracy_tracker.get_overall_accuracy(),
            'accuracy_by_category': self.accuracy_tracker.get_accuracy_by_category(),
            'detailed_metrics': self.accuracy_tracker.get_sklearn_metrics(),
            'confidence_correlation': self.accuracy_tracker.get_confidence_correlation(),
            'trend_analysis': self.accuracy_tracker.get_trend_analysis(days_back)
        }

        # Add escalation metrics
        report['escalation_metrics'] = {
            'escalation_rate': self.escalation_tracker.get_escalation_rate(time_window_hours=days_back*24),
            'resolution_distribution': self.escalation_tracker.get_resolution_distribution(),
            'escalation_reasons': self.escalation_tracker.get_escalation_reasons_breakdown(),
            'time_metrics': self.escalation_tracker.get_time_based_metrics(time_window_hours=days_back*24),
            'first_contact_resolution_rate': self.escalation_tracker.get_first_contact_resolution_rate(),
            'trend_analysis': self.escalation_tracker.get_trend_analysis(days_back)
        }

        # Generate recommendations
        self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict[str, Any]):
        """Generate recommendations based on metrics"""
        recs = []

        # Performance recommendations
        for op_name, stats in report['performance_metrics'].items():
            if stats.get('p95', 0) > 1.0:
                recs.append(f"Performance: {op_name} 95th percentile latency is high ({stats['p95']:.3f}s)")
            if stats.get('success_rate', 1.0) < 0.95:
                recs.append(f"Reliability: {op_name} success rate is low ({stats['success_rate']:.2%})")

        # Quality recommendations
        if report['quality_metrics']['overall_accuracy'] < 0.85:
            recs.append(f"Quality: Overall accuracy is low ({report['quality_metrics']['overall_accuracy']:.2%})")

        # Escalation recommendations
        if report['escalation_metrics']['escalation_rate'] > 0.3:
            recs.append(f"Efficiency: Escalation rate is high ({report['escalation_metrics']['escalation_rate']:.2%})")

        report['recommendations'] = recs

    def export_to_dashboard_format(self, filepath: str):
        """Export metrics in dashboard-ready format"""
        report = self.generate_comprehensive_report()

        # Format for dashboard consumption
        dashboard_data = {
            'summary': {
                'total_interactions': len(self.escalation_tracker.interactions),
                'avg_latency': report['performance_metrics'].get('api_call', {}).get('mean', 0),
                'accuracy_rate': report['quality_metrics']['overall_accuracy'],
                'escalation_rate': report['escalation_metrics']['escalation_rate'],
                'fcr_rate': report['escalation_metrics']['first_contact_resolution_rate']
            },
            'trends': {
                'latency_trend': self.latency_tracker.get_trend_data(OperationType.API_CALL),
                'accuracy_trend': self.accuracy_tracker.get_trend_analysis()['daily_accuracy_rates'],
                'escalation_trend': self.escalation_tracker.get_trend_analysis()
            },
            'details': report
        }

        with open(filepath, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)

@pytest.fixture
def metrics_dashboard(latency_tracker, accuracy_tracker, escalation_tracker):
    """Metrics dashboard fixture"""
    return MetricsDashboard(latency_tracker, accuracy_tracker, escalation_tracker)

def test_comprehensive_metrics_report(metrics_dashboard):
    """Test comprehensive metrics report generation"""
    # First, populate the trackers with some test data
    import requests

    # Simulate some API calls for latency tracking
    for i in range(10):
        with LatencyMeasurement(OperationType.API_CALL, tags={'test': 'comprehensive'}):
            try:
                response = requests.get("https://httpbin.org/delay/1", timeout=5)
                success = response.status_code == 200
            except:
                success = False

    # Add some accuracy measurements
    for i in range(10):
        predicted = "category_a" if i < 7 else "category_b"  # 70% accuracy for demo
        actual = "category_a" if i < 5 else "category_b"   # 5 correct out of 10
        metrics_dashboard.accuracy_tracker.record_classification(predicted, actual, confidence=0.8)

    # Add some escalation measurements
    for i in range(10):
        if i < 3:  # 30% escalation rate for demo
            outcome = ResolutionOutcome.ESCALATED_TO_AGENT
            reason = EscalationReason.COMPLEX_ISSUE
        else:
            outcome = ResolutionOutcome.RESOLVED_AUTOMATICALLY
            reason = None

        metrics_dashboard.escalation_tracker.record_interaction(
            interaction_id=f"demo_{i}",
            customer_id=f"demo_cust_{i}",
            query=f"Demo query {i}",
            resolution_outcome=outcome,
            escalation_reason=reason,
            resolution_time=45.0 + (i * 10),  # Increasing resolution time
            resolution_attempts=1
        )

    # Generate comprehensive report
    report = metrics_dashboard.generate_comprehensive_report(days_back=1)

    print(f"Comprehensive Report Summary:")
    print(f"  Performance Metrics: {len(report['performance_metrics'])} operations tracked")
    print(f"  Quality Metrics: {report['quality_metrics']['overall_accuracy']:.2%} accuracy")
    print(f"  Escalation Metrics: {report['escalation_metrics']['escalation_rate']:.2%} escalation rate")
    print(f"  Recommendations: {len(report['recommendations'])} issues identified")

    # Export to dashboard format
    metrics_dashboard.export_to_dashboard_format('comprehensive_metrics.json')

    # Verify report structure
    assert 'generated_at' in report
    assert 'performance_metrics' in report
    assert 'quality_metrics' in report
    assert 'escalation_metrics' in report
    assert 'recommendations' in report

    print("Comprehensive metrics report generated successfully!")
```

## Metrics Validation and Alerts

### 1. Threshold-Based Alerting

```python
# tests/metrics/test_alerting.py
import pytest
from datetime import datetime, timedelta
from typing import Dict, Callable
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class MetricsAlertSystem:
    """System for alerting on metric thresholds"""

    def __init__(self):
        self.thresholds = {}
        self.alert_history = []
        self.subscribers = []

    def set_threshold(self, metric_name: str, threshold_value: float,
                     comparison_operator: str = 'gt'):
        """Set threshold for a metric"""
        self.thresholds[metric_name] = {
            'value': threshold_value,
            'operator': comparison_operator,  # 'gt', 'lt', 'eq', 'ge', 'le'
            'last_triggered': None
        }

    def check_thresholds(self, metrics: Dict[str, float]) -> List[Dict[str, any]]:
        """Check if any metrics exceed thresholds"""
        alerts = []

        for metric_name, value in metrics.items():
            if metric_name in self.thresholds:
                threshold = self.thresholds[metric_name]

                # Evaluate condition based on operator
                condition_met = False
                if threshold['operator'] == 'gt':
                    condition_met = value > threshold['value']
                elif threshold['operator'] == 'lt':
                    condition_met = value < threshold['value']
                elif threshold['operator'] == 'ge':
                    condition_met = value >= threshold['value']
                elif threshold['operator'] == 'le':
                    condition_met = value <= threshold['value']
                elif threshold['operator'] == 'eq':
                    condition_met = abs(value - threshold['value']) < 0.001

                if condition_met:
                    alert = {
                        'metric': metric_name,
                        'value': value,
                        'threshold': threshold['value'],
                        'timestamp': datetime.now(),
                        'severity': 'HIGH' if threshold['value'] * 2 < value else 'MEDIUM'
                    }

                    # Avoid duplicate alerts within 10 minutes
                    if not self._recent_duplicate(alert):
                        alerts.append(alert)
                        self.alert_history.append(alert)
                        threshold['last_triggered'] = alert['timestamp']

        return alerts

    def _recent_duplicate(self, alert: Dict[str, any]) -> bool:
        """Check if similar alert was triggered recently"""
        cutoff_time = datetime.now() - timedelta(minutes=10)

        for recent_alert in self.alert_history:
            if (recent_alert['metric'] == alert['metric'] and
                recent_alert['timestamp'] > cutoff_time):
                return True

        return False

    def send_alerts(self, alerts: List[Dict[str, any]], message: str = None):
        """Send alerts to subscribers"""
        if not alerts:
            return

        subject = f"Performance Alert - {len(alerts)} Issues Detected"

        if not message:
            message = "\n".join([
                f"- {a['metric']}: {a['value']:.3f} (threshold: {a['threshold']})"
                for a in alerts
            ])

        # In a real system, this would send emails, Slack messages, etc.
        print(f"ALERT: {subject}")
        print(f"Message: {message}")

        # Log alert
        for alert in alerts:
            print(f"  {alert['severity']} - {alert['metric']}: {alert['value']:.3f}")

ALERT_SYSTEM = MetricsAlertSystem()

@pytest.fixture
def alert_system():
    """Alert system fixture"""
    return ALERT_SYSTEM

def test_latency_threshold_alerting(alert_system, latency_tracker):
    """Test latency threshold alerting"""
    # Set up thresholds
    alert_system.set_threshold('customer_creation_p95', 0.5, 'gt')  # Alert if P95 > 0.5s
    alert_system.set_threshold('api_call_mean', 1.0, 'gt')         # Alert if mean > 1.0s

    # Add some high-latency samples to trigger alerts
    for i in range(5):
        # Record high latency (will trigger alerts)
        LATENCY_TRACKER.record_latency(
            OperationType.CUSTOMER_CREATION,
            duration=0.8 + (i * 0.1),  # Increasing latency
            success=True
        )
        LATENCY_TRACKER.record_latency(
            OperationType.API_CALL,
            duration=1.2 + (i * 0.1),
            success=True
        )

    # Check current metrics
    customer_stats = latency_tracker.get_current_stats(OperationType.CUSTOMER_CREATION)
    api_stats = latency_tracker.get_current_stats(OperationType.API_CALL)

    # Check for alerts
    metrics_to_check = {
        'customer_creation_p95': customer_stats.get('p95', 0),
        'api_call_mean': api_stats.get('mean', 0)
    }

    alerts = alert_system.check_thresholds(metrics_to_check)

    print(f"Detected {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  {alert['severity']} - {alert['metric']}: {alert['value']:.3f}")

    # Should have alerts for both metrics exceeding thresholds
    assert len(alerts) >= 2
    assert any(a['metric'] == 'customer_creation_p95' for a in alerts)
    assert any(a['metric'] == 'api_call_mean' for a in alerts)

def test_accuracy_threshold_alerting(alert_system, accuracy_tracker):
    """Test accuracy threshold alerting"""
    # Set up accuracy threshold
    alert_system.set_threshold('overall_accuracy', 0.80, 'lt')  # Alert if accuracy < 80%

    # Add some low accuracy results to trigger alert
    low_accuracy_cases = [
        ('category_a', 'category_b', 0.7),  # Wrong prediction
        ('category_b', 'category_a', 0.6),  # Wrong prediction
        ('category_c', 'category_d', 0.8),  # Wrong prediction
        ('category_a', 'category_a', 0.9),  # Correct
        ('category_b', 'category_b', 0.85), # Correct
    ]

    for predicted, actual, confidence in low_accuracy_cases:
        accuracy_tracker.record_classification(predicted, actual, confidence)

    # Check accuracy
    current_accuracy = accuracy_tracker.get_overall_accuracy()

    # Check for alerts
    metrics_to_check = {
        'overall_accuracy': current_accuracy
    }

    alerts = alert_system.check_thresholds(metrics_to_check)

    print(f"Accuracy: {current_accuracy:.2%}")
    if alerts:
        print(f"Accuracy alert triggered: {alerts[0]['metric']} = {alerts[0]['value']:.3f}")

    # With 2 out of 5 wrong, accuracy is 60%, which should trigger the alert
    assert current_accuracy == 0.6  # 3/5 correct = 60%
    assert len(alerts) >= 1
    assert alerts[0]['metric'] == 'overall_accuracy'
    assert alerts[0]['value'] == 0.6

print("Metric tracking system initialized successfully!")
```

This comprehensive metric tracking guide provides all the necessary techniques and patterns for implementing effective performance and quality metric tracking in a pytest-based test suite.