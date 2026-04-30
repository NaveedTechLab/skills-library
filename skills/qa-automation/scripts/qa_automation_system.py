#!/usr/bin/env python3
"""
QA Automation System
Builds the pytest-based test suite for the transition from prototype to production.
Implements E2E tests, edge-case validation, and performance metric tracking (latency, accuracy, escalation rates).
"""

import os
import sys
import json
import time
import yaml
import logging
import subprocess
import tempfile
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import csv
import statistics

# Import required libraries
try:
    import pytest
    import requests
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    import psutil
    import pandas as pd
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QAAutomationSystem:
    """Main QA Automation System for test suite management"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.test_results = []
        self.performance_metrics = {}
        self.quality_metrics = {}
        self.escalation_metrics = {}

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration for the QA system"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)

        # Default configuration
        return {
            'test_paths': ['tests/unit', 'tests/integration', 'tests/e2e'],
            'output_dir': 'test_reports',
            'performance_thresholds': {
                'latency_avg': 0.5,
                'latency_p95': 1.0,
                'success_rate': 0.95
            },
            'quality_thresholds': {
                'accuracy_rate': 0.85,
                'first_contact_resolution': 0.70
            },
            'escalation_thresholds': {
                'escalation_rate': 0.30
            }
        }

    def setup_test_environment(self):
        """Setup test environment with necessary directories and configurations"""
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different test types
        for subdir in ['unit', 'integration', 'e2e', 'performance', 'edge_case']:
            (output_dir / subdir).mkdir(exist_ok=True)

        logger.info(f"Test environment setup in {output_dir}")

    def run_pytest_tests(self, test_path: str = None, markers: str = None) -> Dict[str, Any]:
        """Run pytest tests and return results"""
        if not test_path:
            test_path = "tests/"

        # Create temporary file for pytest output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            output_file = temp_file.name

        # Build pytest command
        cmd = [
            'pytest',
            test_path,
            f'--json-report',
            f'--json-report-file={output_file}',
            f'--cov=myapp',
            f'--cov-report=html:test_reports/coverage_html',
            f'--cov-report=xml:test_reports/coverage.xml',
            f'--junitxml=test_reports/junit.xml'
        ]

        if markers:
            cmd.append(f'-m {markers}')

        logger.info(f"Running tests: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

            # Parse pytest results
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    pytest_results = json.load(f)

                # Clean up temp file
                os.unlink(output_file)

                return pytest_results

            logger.error("Pytest output file not found")
            return {}

        except Exception as e:
            logger.error(f"Error running pytest: {e}")
            return {}

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests"""
        logger.info("Running unit tests...")
        return self.run_pytest_tests("tests/unit", markers="not integration and not e2e")

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        logger.info("Running integration tests...")
        return self.run_pytest_tests("tests/integration", markers="integration")

    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests"""
        logger.info("Running end-to-end tests...")
        return self.run_pytest_tests("tests/e2e", markers="e2e")

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        logger.info("Running performance tests...")
        return self.run_pytest_tests("tests/performance", markers="performance")

    def run_edge_case_tests(self) -> Dict[str, Any]:
        """Run edge case tests"""
        logger.info("Running edge case tests...")
        return self.run_pytest_tests("tests/edge_cases", markers="edge_case")

    def measure_api_latency(self, url: str, method: str = 'GET', headers: Dict = None,
                          payload: Dict = None, iterations: int = 10) -> Dict[str, float]:
        """Measure API endpoint latency"""
        logger.info(f"Measuring latency for {method} {url}")

        latencies = []

        for i in range(iterations):
            start_time = time.perf_counter()

            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers)
                elif method.upper() == 'POST':
                    response = requests.post(url, json=payload, headers=headers)
                elif method.upper() == 'PUT':
                    response = requests.put(url, json=payload, headers=headers)
                elif method.upper() == 'DELETE':
                    response = requests.delete(url, headers=headers)

                end_time = time.perf_counter()
                latencies.append(end_time - start_time)

            except Exception as e:
                logger.error(f"Error measuring latency: {e}")
                latencies.append(float('inf'))  # Mark as failed

        if not latencies:
            return {}

        # Calculate statistics
        results = {
            'count': len(latencies),
            'success_count': len([l for l in latencies if l != float('inf')]),
            'avg_latency': statistics.mean([l for l in latencies if l != float('inf')]) if any(l != float('inf') for l in latencies) else 0,
            'median_latency': statistics.median([l for l in latencies if l != float('inf')]) if any(l != float('inf') for l in latencies) else 0,
            'min_latency': min([l for l in latencies if l != float('inf')]) if any(l != float('inf') for l in latencies) else 0,
            'max_latency': max([l for l in latencies if l != float('inf')]) if any(l != float('inf') for l in latencies) else 0,
        }

        # Calculate percentiles
        successful_latencies = [l for l in latencies if l != float('inf')]
        if successful_latencies:
            sorted_latencies = sorted(successful_latencies)
            results['p90_latency'] = sorted_latencies[int(0.90 * len(sorted_latencies))]
            results['p95_latency'] = sorted_latencies[int(0.95 * len(sorted_latencies))]
            results['p99_latency'] = sorted_latencies[int(0.99 * len(sorted_latencies))]

        self.performance_metrics['api_latency'] = results
        return results

    def measure_system_resources(self, duration: int = 30) -> Dict[str, Any]:
        """Measure system resource usage during test execution"""
        logger.info(f"Measuring system resources for {duration} seconds...")

        cpu_percentages = []
        memory_percentages = []
        disk_usages = []

        start_time = time.time()
        while time.time() - start_time < duration:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent

            cpu_percentages.append(cpu_percent)
            memory_percentages.append(memory_percent)
            disk_usages.append(disk_usage)

        results = {
            'cpu': {
                'avg': statistics.mean(cpu_percentages),
                'max': max(cpu_percentages),
                'min': min(cpu_percentages),
                'samples': len(cpu_percentages)
            },
            'memory': {
                'avg': statistics.mean(memory_percentages),
                'max': max(memory_percentages),
                'min': min(memory_percentages),
                'samples': len(memory_percentages)
            },
            'disk': {
                'avg': statistics.mean(disk_usages),
                'max': max(disk_usages),
                'min': min(disk_usages),
                'samples': len(disk_usages)
            }
        }

        self.performance_metrics['system_resources'] = results
        return results

    def evaluate_accuracy(self, predictions: List[str], actuals: List[str]) -> Dict[str, float]:
        """Evaluate accuracy of predictions against actual values"""
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have the same length")

        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        total = len(predictions)

        accuracy = correct / total if total > 0 else 0

        results = {
            'accuracy_rate': accuracy,
            'correct_predictions': correct,
            'total_predictions': total,
            'error_rate': 1 - accuracy
        }

        self.quality_metrics['accuracy'] = results
        return results

    def evaluate_escalation_rate(self, total_interactions: int, escalations: int) -> Dict[str, float]:
        """Evaluate escalation rate"""
        escalation_rate = escalations / total_interactions if total_interactions > 0 else 0

        results = {
            'escalation_rate': escalation_rate,
            'total_interactions': total_interactions,
            'escalations': escalations,
            'resolutions_without_escalation': total_interactions - escalations
        }

        self.escalation_metrics['rate'] = results
        return results

    def run_complete_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite and collect all metrics"""
        logger.info("Starting complete test suite...")

        results = {
            'timestamp': datetime.now().isoformat(),
            'unit_tests': self.run_unit_tests(),
            'integration_tests': self.run_integration_tests(),
            'e2e_tests': self.run_e2e_tests(),
            'performance_tests': self.run_performance_tests(),
            'edge_case_tests': self.run_edge_case_tests(),
            'api_latency': self.measure_api_latency('https://httpbin.org/get', 'GET', iterations=5),
            'system_resources': self.measure_system_resources(duration=10),
        }

        # Calculate additional metrics
        self.calculate_composite_metrics(results)

        # Generate reports
        self.generate_test_report(results)
        self.generate_performance_report()
        self.generate_quality_report()
        self.generate_escalation_report()

        logger.info("Complete test suite finished.")
        return results

    def calculate_composite_metrics(self, results: Dict[str, Any]):
        """Calculate composite metrics from test results"""
        # Calculate overall success rate from pytest results
        all_tests = []
        for test_type in ['unit_tests', 'integration_tests', 'e2e_tests', 'performance_tests', 'edge_case_tests']:
            if test_type in results and 'summary' in results[test_type]:
                all_tests.append(results[test_type]['summary'])

        if all_tests:
            total_passed = sum(test.get('passed', 0) for test in all_tests)
            total_tests = sum(
                test.get('passed', 0) + test.get('failed', 0) + test.get('skipped', 0)
                for test in all_tests
            )

            overall_success_rate = total_passed / total_tests if total_tests > 0 else 0

            self.performance_metrics['overall_success_rate'] = overall_success_rate

    def generate_test_report(self, results: Dict[str, Any]):
        """Generate comprehensive test report"""
        report_path = Path(self.config['output_dir']) / 'test_report.json'

        report = {
            'generated_at': datetime.now().isoformat(),
            'configuration': self.config,
            'results': results,
            'metrics': {
                'performance': self.performance_metrics,
                'quality': self.quality_metrics,
                'escalation': self.escalation_metrics
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Test report generated at {report_path}")

    def generate_performance_report(self):
        """Generate performance-specific report"""
        if not self.performance_metrics:
            logger.warning("No performance metrics to report")
            return

        report_path = Path(self.config['output_dir']) / 'performance_report.csv'

        with open(report_path, 'w', newline='') as csvfile:
            fieldnames = ['metric', 'value', 'unit', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            # Flatten performance metrics
            for category, metrics in self.performance_metrics.items():
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            writer.writerow({
                                'metric': f"{category}.{key}",
                                'value': value,
                                'unit': 'seconds' if 'latency' in key else ('%' if 'rate' in key else ''),
                                'timestamp': datetime.now().isoformat()
                            })

        logger.info(f"Performance report generated at {report_path}")

    def generate_quality_report(self):
        """Generate quality-specific report"""
        if not self.quality_metrics:
            logger.warning("No quality metrics to report")
            return

        report_path = Path(self.config['output_dir']) / 'quality_report.csv'

        with open(report_path, 'w', newline='') as csvfile:
            fieldnames = ['metric', 'value', 'unit', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            # Flatten quality metrics
            for category, metrics in self.quality_metrics.items():
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            writer.writerow({
                                'metric': f"{category}.{key}",
                                'value': value,
                                'unit': '%' if 'rate' in key else '',
                                'timestamp': datetime.now().isoformat()
                            })

        logger.info(f"Quality report generated at {report_path}")

    def generate_escalation_report(self):
        """Generate escalation-specific report"""
        if not self.escalation_metrics:
            logger.warning("No escalation metrics to report")
            return

        report_path = Path(self.config['output_dir']) / 'escalation_report.csv'

        with open(report_path, 'w', newline='') as csvfile:
            fieldnames = ['metric', 'value', 'unit', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            # Flatten escalation metrics
            for category, metrics in self.escalation_metrics.items():
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            writer.writerow({
                                'metric': f"{category}.{key}",
                                'value': value,
                                'unit': '%' if 'rate' in key else '',
                                'timestamp': datetime.now().isoformat()
                            })

        logger.info(f"Escalation report generated at {report_path}")

    def validate_metrics_against_thresholds(self) -> Dict[str, List[str]]:
        """Validate all metrics against defined thresholds"""
        violations = {
            'performance': [],
            'quality': [],
            'escalation': []
        }

        # Check performance thresholds
        perf_thresholds = self.config.get('performance_thresholds', {})
        for metric, threshold in perf_thresholds.items():
            if metric in self.performance_metrics:
                actual = self.performance_metrics[metric]
                if isinstance(actual, (int, float)) and actual > threshold:
                    violations['performance'].append(f"{metric}: {actual} > {threshold}")

        # Check quality thresholds
        quality_thresholds = self.config.get('quality_thresholds', {})
        for metric, threshold in quality_thresholds.items():
            if metric in self.quality_metrics:
                actual = self.quality_metrics[metric]
                if isinstance(actual, (int, float)) and actual < threshold:
                    violations['quality'].append(f"{metric}: {actual} < {threshold}")

        # Check escalation thresholds
        esc_thresholds = self.config.get('escalation_thresholds', {})
        for metric, threshold in esc_thresholds.items():
            if metric in self.escalation_metrics:
                actual = self.escalation_metrics[metric]
                if isinstance(actual, (int, float)) and actual > threshold:
                    violations['escalation'].append(f"{metric}: {actual} > {threshold}")

        return violations

def main():
    """Main function to run the QA Automation System"""
    parser = argparse.ArgumentParser(description='QA Automation System')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--test-path', type=str, help='Path to specific tests to run')
    parser.add_argument('--markers', type=str, help='Pytest markers to run')
    parser.add_argument('--report-only', action='store_true', help='Generate reports from existing data')

    args = parser.parse_args()

    print("QA Automation System")
    print("=" * 50)

    # Initialize the QA system
    qa_system = QAAutomationSystem(args.config)

    # Setup test environment
    qa_system.setup_test_environment()

    if not args.report_only:
        # Run tests based on arguments
        if args.test_path:
            if args.markers:
                results = qa_system.run_pytest_tests(args.test_path, args.markers)
            else:
                results = qa_system.run_pytest_tests(args.test_path)
        else:
            # Run complete test suite
            results = qa_system.run_complete_test_suite()

        print(f"Test execution completed. Results stored in {qa_system.config['output_dir']}")
    else:
        print("Generating reports from existing data...")
        # Just generate reports from existing metrics
        qa_system.generate_test_report({})
        qa_system.generate_performance_report()
        qa_system.generate_quality_report()
        qa_system.generate_escalation_report()

    # Validate metrics against thresholds
    violations = qa_system.validate_metrics_against_thresholds()

    print("\nThreshold Violations:")
    for category, violation_list in violations.items():
        if violation_list:
            print(f"  {category.title()}:")
            for violation in violation_list:
                print(f"    - {violation}")
        else:
            print(f"  {category.title()}: No violations")

    if any(violations.values()):
        print("\n⚠️  Some metrics violated defined thresholds!")
        return 1
    else:
        print("\n✅ All metrics are within defined thresholds!")
        return 0

if __name__ == "__main__":
    sys.exit(main())