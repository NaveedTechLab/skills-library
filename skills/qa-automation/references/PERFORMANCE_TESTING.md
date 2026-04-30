# Performance Testing for QA Automation

## Overview

This document provides comprehensive guidance on implementing performance testing in a pytest-based test suite. It covers load testing, stress testing, scalability testing, and performance metric tracking.

## Performance Testing Types

### 1. Load Testing

Load testing verifies system behavior under expected load conditions.

```python
# tests/performance/test_load_testing.py
import pytest
import time
import asyncio
import aiohttp
import statistics
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
import matplotlib.pyplot as plt
import pandas as pd

# Result container
TestResult = namedtuple('TestResult', [
    'request_id', 'response_time', 'status_code',
    'success', 'timestamp', 'error_message'
])

class LoadTester:
    """Load testing framework"""

    def __init__(self, base_url, concurrency=10, duration=60):
        self.base_url = base_url
        self.concurrency = concurrency
        self.duration = duration
        self.results = []

    async def make_request(self, session, method, endpoint, payload=None):
        """Make a single request and record results"""
        start_time = time.perf_counter()

        try:
            if method.upper() == 'GET':
                response = await session.get(f"{self.base_url}{endpoint}")
            elif method.upper() == 'POST':
                response = await session.post(f"{self.base_url}{endpoint}", json=payload)
            elif method.upper() == 'PUT':
                response = await session.put(f"{self.base_url}{endpoint}", json=payload)
            elif method.upper() == 'DELETE':
                response = await session.delete(f"{self.base_url}{endpoint}")

            response_time = time.perf_counter() - start_time

            result = TestResult(
                request_id=id(payload) if payload else hash(endpoint),
                response_time=response_time,
                status_code=response.status,
                success=response.status == 200,
                timestamp=time.time(),
                error_message=None
            )

            return result

        except Exception as e:
            response_time = time.perf_counter() - start_time

            result = TestResult(
                request_id=id(payload) if payload else hash(endpoint),
                response_time=response_time,
                status_code=500,
                success=False,
                timestamp=time.time(),
                error_message=str(e)
            )

            return result

    async def run_load_test(self, method, endpoint, payload=None, rate=10):
        """Run load test with specified request rate"""
        self.results = []
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < self.duration:
                # Calculate how many requests to send in this second
                requests_this_second = min(rate, self.concurrency)

                # Send requests concurrently
                tasks = []
                for _ in range(requests_this_second):
                    task = self.make_request(session, method, endpoint, payload)
                    tasks.append(task)

                batch_results = await asyncio.gather(*tasks)
                self.results.extend(batch_results)

                # Sleep to maintain target rate
                elapsed = time.time() - start_time
                remaining = max(0, 1.0 - (elapsed % 1.0))
                if remaining > 0:
                    await asyncio.sleep(remaining)

    def get_statistics(self):
        """Calculate performance statistics"""
        if not self.results:
            return {}

        response_times = [r.response_time for r in self.results]
        success_rates = [1 if r.success else 0 for r in self.results]

        stats = {
            'total_requests': len(self.results),
            'successful_requests': sum(success_rates),
            'failed_requests': len(self.results) - sum(success_rates),
            'success_rate': sum(success_rates) / len(self.results),
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'std_dev_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            'p95_response_time': sorted(response_times)[int(0.95 * len(response_times))] if response_times else 0,
            'p99_response_time': sorted(response_times)[int(0.99 * len(response_times))] if response_times else 0,
        }

        # Calculate requests per second
        if self.results:
            start_time = min(r.timestamp for r in self.results)
            end_time = max(r.timestamp for r in self.results)
            duration = end_time - start_time
            if duration > 0:
                stats['requests_per_second'] = stats['total_requests'] / duration

        return stats

    def generate_report(self):
        """Generate performance test report"""
        stats = self.get_statistics()

        report = f"""
Load Test Report
==============
Duration: {self.duration} seconds
Concurrency: {self.concurrency}
Total Requests: {stats.get('total_requests', 0)}

Performance Metrics:
- Success Rate: {stats.get('success_rate', 0):.2%}
- Avg Response Time: {stats.get('avg_response_time', 0):.3f}s
- Median Response Time: {stats.get('median_response_time', 0):.3f}s
- P95 Response Time: {stats.get('p95_response_time', 0):.3f}s
- P99 Response Time: {stats.get('p99_response_time', 0):.3f}s
- Min Response Time: {stats.get('min_response_time', 0):.3f}s
- Max Response Time: {stats.get('max_response_time', 0):.3f}s
- Throughput: {stats.get('requests_per_second', 0):.2f} req/s

Reliability Metrics:
- Successful Requests: {stats.get('successful_requests', 0)}
- Failed Requests: {stats.get('failed_requests', 0)}
        """

        return report

# Pytest fixture for load testing
@pytest.fixture
def load_tester():
    """Load tester fixture"""
    return LoadTester(base_url="https://test-api.myapp.com", concurrency=20, duration=30)

def test_customer_creation_load(load_tester):
    """Test customer creation under load"""
    payload = {
        'name': 'Load Test User',
        'email': 'load@test.com',
        'phone': '+1234567890'
    }

    # Run load test
    asyncio.run(load_tester.run_load_test('POST', '/customers', payload, rate=10))

    # Get statistics
    stats = load_tester.get_statistics()

    # Assert performance requirements
    assert stats['success_rate'] >= 0.95, f"Success rate too low: {stats['success_rate']:.2%}"
    assert stats['avg_response_time'] <= 0.5, f"Avg response time too high: {stats['avg_response_time']:.3f}s"
    assert stats['p95_response_time'] <= 1.0, f"P95 response time too high: {stats['p95_response_time']:.3f}s"

    # Print report
    print(load_tester.generate_report())
```

### 2. Stress Testing

Stress testing pushes the system beyond normal operational capacity.

```python
# tests/performance/test_stress_testing.py
import pytest
import asyncio
import aiohttp
import time
from contextlib import contextmanager

class StressTester:
    """Stress testing framework"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []

    @contextmanager
    def measure_system_resources(self):
        """Context manager to measure system resources"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()

        yield

        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = process.cpu_percent()

        print(f"Memory usage: {start_memory:.2f}MB -> {end_memory:.2f}MB")
        print(f"CPU usage: {start_cpu}% -> {end_cpu}%")

    async def run_stress_test(self, method, endpoint, payload=None, max_concurrency=100):
        """Run stress test with increasing load"""
        self.results = []

        # Test with increasing concurrency levels
        concurrency_levels = [10, 25, 50, 75, 100]

        for concurrency in concurrency_levels:
            print(f"Testing with {concurrency} concurrent requests...")

            async with aiohttp.ClientSession() as session:
                # Create all tasks
                tasks = []
                for i in range(concurrency):
                    task = self.make_request(session, method, endpoint, payload)
                    tasks.append(task)

                # Execute all tasks concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and add valid results
                valid_results = [r for r in batch_results if not isinstance(r, Exception)]
                self.results.extend(valid_results)

                # Calculate and report metrics for this level
                stats = self.calculate_stats(valid_results)
                print(f"  Level {concurrency}: Success Rate: {stats['success_rate']:.2%}, "
                      f"Avg RT: {stats['avg_response_time']:.3f}s")

                # Brief pause between levels
                await asyncio.sleep(2)

    async def make_request(self, session, method, endpoint, payload=None):
        """Make a single request for stress test"""
        start_time = time.perf_counter()

        try:
            if method.upper() == 'GET':
                response = await session.get(f"{self.base_url}{endpoint}")
            elif method.upper() == 'POST':
                response = await session.post(f"{self.base_url}{endpoint}", json=payload)

            response_time = time.perf_counter() - start_time

            return TestResult(
                request_id=id(payload) if payload else hash(endpoint),
                response_time=response_time,
                status_code=response.status,
                success=response.status == 200,
                timestamp=time.time(),
                error_message=None
            )

        except Exception as e:
            response_time = time.perf_counter() - start_time

            return TestResult(
                request_id=id(payload) if payload else hash(endpoint),
                response_time=response_time,
                status_code=500,
                success=False,
                timestamp=time.time(),
                error_message=str(e)
            )

    def calculate_stats(self, results):
        """Calculate statistics for a batch of results"""
        if not results:
            return {}

        response_times = [r.response_time for r in results]
        success_rates = [1 if r.success else 0 for r in results]

        return {
            'total_requests': len(results),
            'successful_requests': sum(success_rates),
            'success_rate': sum(success_rates) / len(results) if results else 0,
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'error_count': len(results) - sum(success_rates)
        }

def test_customer_creation_stress():
    """Test customer creation under stress conditions"""
    stress_tester = StressTester(base_url="https://test-api.myapp.com")

    payload = {
        'name': 'Stress Test User',
        'email': 'stress@test.com',
        'phone': '+1234567890'
    }

    # Run stress test
    asyncio.run(stress_tester.run_stress_test('POST', '/customers', payload))

    # Analyze results
    all_stats = stress_tester.calculate_stats(stress_tester.results)

    # Even under stress, should maintain some level of service
    assert all_stats['success_rate'] >= 0.80, f"Stress test failure: {all_stats['success_rate']:.2%} success rate"

    print(f"Stress test completed. Final stats: {all_stats}")
```

### 3. Scalability Testing

Scalability testing evaluates how the system performs as load increases.

```python
# tests/performance/test_scalability.py
import pytest
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

class ScalabilityTester:
    """Scalability testing framework"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.scalability_data = []

    def run_scalability_test(self, method, endpoint, payload=None, load_levels=None):
        """Run scalability test with different load levels"""
        if load_levels is None:
            load_levels = [10, 25, 50, 75, 100, 150, 200]  # requests per second

        for load in load_levels:
            print(f"Testing at {load} requests per second...")

            # Run load test at this level
            load_tester = LoadTester(self.base_url, concurrency=load, duration=30)
            asyncio.run(load_tester.run_load_test(method, endpoint, payload, rate=load))

            stats = load_tester.get_statistics()

            # Record scalability data
            scalability_point = {
                'load_level': load,
                'throughput': stats.get('requests_per_second', 0),
                'avg_response_time': stats.get('avg_response_time', 0),
                'p95_response_time': stats.get('p95_response_time', 0),
                'success_rate': stats.get('success_rate', 0),
                'errors': stats.get('failed_requests', 0)
            }

            self.scalability_data.append(scalability_point)
            print(f"  Throughput: {scalability_point['throughput']:.2f}, "
                  f"Response Time: {scalability_point['avg_response_time']:.3f}s")

    def analyze_scalability(self):
        """Analyze scalability data"""
        if not self.scalability_data:
            return {}

        # Extract data points
        load_levels = [point['load_level'] for point in self.scalability_data]
        response_times = [point['avg_response_time'] for point in self.scalability_data]
        success_rates = [point['success_rate'] for point in self.scalability_data]

        # Calculate scalability metrics
        scalability_metrics = {
            'linear_regression_slope': 0,
            'performance_degradation_start': None,
            'optimal_throughput': 0,
            'breakpoint_load': 0
        }

        # Calculate linear regression to detect performance degradation
        if len(load_levels) > 1:
            slope, intercept, r_value, p_value, std_err = stats.linregress(load_levels, response_times)
            scalability_metrics['linear_regression_slope'] = slope

            # Identify where performance starts degrading significantly
            for i, (load, rt) in enumerate(zip(load_levels, response_times)):
                if i > 0 and rt > response_times[i-1] * 2:  # Response time doubled
                    scalability_metrics['performance_degradation_start'] = load
                    break

        # Find optimal throughput
        max_efficiency_idx = np.argmax([
            point['throughput'] / point['avg_response_time'] if point['avg_response_time'] > 0 else 0
            for point in self.scalability_data
        ])
        scalability_metrics['optimal_throughput'] = self.scalability_data[max_efficiency_idx]['load_level']

        # Find breakpoint (where success rate drops significantly)
        for point in self.scalability_data:
            if point['success_rate'] < 0.90:  # Less than 90% success rate
                scalability_metrics['breakpoint_load'] = point['load_level']
                break

        return scalability_metrics

    def plot_scalability_graph(self):
        """Plot scalability graph"""
        if not self.scalability_data:
            return

        load_levels = [point['load_level'] for point in self.scalability_data]
        response_times = [point['avg_response_time'] for point in self.scalability_data]
        success_rates = [point['success_rate'] for point in self.scalability_data]
        throughputs = [point['throughput'] for point in self.scalability_data]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))

        # Response time vs load
        ax1.plot(load_levels, response_times, marker='o', color='blue')
        ax1.set_xlabel('Load Level (req/s)')
        ax1.set_ylabel('Average Response Time (s)')
        ax1.set_title('Response Time vs Load')
        ax1.grid(True)

        # Success rate vs load
        ax2.plot(load_levels, success_rates, marker='s', color='green')
        ax2.set_xlabel('Load Level (req/s)')
        ax2.set_ylabel('Success Rate')
        ax2.set_title('Success Rate vs Load')
        ax2.grid(True)
        ax2.set_ylim(0, 1.05)

        # Throughput vs load
        ax3.plot(load_levels, throughputs, marker='^', color='red')
        ax3.set_xlabel('Load Level (req/s)')
        ax3.set_ylabel('Actual Throughput (req/s)')
        ax3.set_title('Throughput vs Load')
        ax3.grid(True)

        plt.tight_layout()
        plt.savefig('scalability_analysis.png')
        plt.show()

def test_scalability_analysis():
    """Test scalability of customer creation endpoint"""
    scalability_tester = ScalabilityTester(base_url="https://test-api.myapp.com")

    payload = {
        'name': 'Scalability Test User',
        'email': 'scalability@test.com',
        'phone': '+1234567890'
    }

    # Run scalability test
    scalability_tester.run_scalability_test('POST', '/customers', payload)

    # Analyze results
    metrics = scalability_tester.analyze_scalability()

    print("Scalability Analysis Results:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Assert scalability requirements
    assert metrics['optimal_throughput'] > 50, "System not scalable enough"

    # Plot results
    scalability_tester.plot_scalability_graph()
```

## Performance Monitoring and Tracking

### 1. Real-time Performance Tracking

```python
# tests/performance/test_realtime_monitoring.py
import pytest
import time
import threading
import psutil
import os
from dataclasses import dataclass
from typing import Dict, List
import json
from datetime import datetime

@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read: float
    disk_io_write: float
    network_io_sent: float
    network_io_recv: float
    active_connections: int
    threads_count: int

class PerformanceMonitor:
    """Real-time performance monitor"""

    def __init__(self, interval=1.0):
        self.interval = interval
        self.snapshots: List[PerformanceSnapshot] = []
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process(os.getpid())

    def start_monitoring(self):
        """Start performance monitoring in background thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            snapshot = self._take_snapshot()
            self.snapshots.append(snapshot)
            time.sleep(self.interval)

    def _take_snapshot(self):
        """Take a performance snapshot"""
        # Get system-level metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()

        # Get process-level metrics
        process_memory = self.process.memory_info()
        disk_io = self.process.io_counters()
        connections = self.process.connections()
        threads = self.process.num_threads()

        # Get network I/O (system-wide)
        net_io = psutil.net_io_counters()

        return PerformanceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_info.percent,
            memory_used_mb=process_memory.rss / 1024 / 1024,
            disk_io_read=disk_io.read_bytes,
            disk_io_write=disk_io.write_bytes,
            network_io_sent=net_io.bytes_sent,
            network_io_recv=net_io.bytes_recv,
            active_connections=len(connections),
            threads_count=threads
        )

    def get_summary(self):
        """Get performance summary"""
        if not self.snapshots:
            return {}

        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_used_mb for s in self.snapshots]

        return {
            'duration': self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
            'max_cpu_percent': max(cpu_values),
            'avg_memory_mb': sum(memory_values) / len(memory_values),
            'max_memory_mb': max(memory_values),
            'final_active_connections': self.snapshots[-1].active_connections,
            'final_threads_count': self.snapshots[-1].threads_count,
            'total_snapshots': len(self.snapshots)
        }

    def export_to_json(self, filepath):
        """Export performance data to JSON"""
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'snapshots': [
                {
                    'timestamp': s.timestamp,
                    'cpu_percent': s.cpu_percent,
                    'memory_percent': s.memory_percent,
                    'memory_used_mb': s.memory_used_mb,
                    'disk_io_read': s.disk_io_read,
                    'disk_io_write': s.disk_io_write,
                    'network_io_sent': s.network_io_sent,
                    'network_io_recv': s.network_io_recv,
                    'active_connections': s.active_connections,
                    'threads_count': s.threads_count
                }
                for s in self.snapshots
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

@pytest.fixture
def performance_monitor():
    """Performance monitor fixture"""
    monitor = PerformanceMonitor(interval=0.5)
    monitor.start_monitoring()
    yield monitor
    monitor.stop_monitoring()

def test_customer_creation_with_performance_monitoring(performance_monitor):
    """Test customer creation with performance monitoring"""
    import requests

    # Make several customer creation requests
    start_time = time.time()

    for i in range(50):
        response = requests.post("https://test-api.myapp.com/customers", json={
            'name': f'Test User {i}',
            'email': f'test{i}@example.com',
            'phone': f'+123456789{i:02d}'
        })
        assert response.status_code in [200, 201], f"Request {i} failed: {response.status_code}"

    end_time = time.time()

    # Stop monitoring and get results
    summary = performance_monitor.get_summary()

    print(f"Performance during test:")
    print(f"  Duration: {summary['duration']:.2f}s")
    print(f"  Avg CPU: {summary['avg_cpu_percent']:.2f}%")
    print(f"  Max CPU: {summary['max_cpu_percent']:.2f}%")
    print(f"  Avg Memory: {summary['avg_memory_mb']:.2f}MB")
    print(f"  Max Memory: {summary['max_memory_mb']:.2f}MB")

    # Assert performance requirements
    assert summary['avg_cpu_percent'] < 80, f"CPU usage too high: {summary['avg_cpu_percent']:.2f}%"
    assert summary['max_memory_mb'] < 1000, f"Memory usage too high: {summary['max_memory_mb']:.2f}MB"

    # Export data for further analysis
    performance_monitor.export_to_json('performance_data.json')
```

### 2. Continuous Performance Tracking

```python
# tests/performance/test_continuous_tracking.py
import pytest
import time
from datetime import datetime, timedelta
import sqlite3
from contextlib import contextmanager

class PerformanceTracker:
    """Continuous performance tracking system"""

    def __init__(self, db_path="performance_tracker.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the performance tracking database"""
        with self.get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    response_time REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    cpu_percent REAL,
                    memory_mb REAL,
                    additional_metadata TEXT
                )
            ''')

            # Create indexes for better query performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_test_name ON performance_metrics(test_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_operation ON performance_metrics(operation)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_metrics(timestamp)')

    @contextmanager
    def get_db_connection(self):
        """Get database connection with automatic commit/rollback"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_metric(self, test_name, operation, response_time, success,
                     error_message=None, cpu_percent=None, memory_mb=None,
                     additional_metadata=None):
        """Record a performance metric"""
        metadata_str = json.dumps(additional_metadata) if additional_metadata else None

        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO performance_metrics
                (test_name, operation, response_time, success, error_message,
                 cpu_percent, memory_mb, additional_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (test_name, operation, response_time, success, error_message,
                  cpu_percent, memory_mb, metadata_str))

    def get_trend_data(self, test_name, operation, days_back=30):
        """Get trend data for a specific test and operation"""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT
                    date(timestamp) as day,
                    avg(response_time) as avg_response_time,
                    percentile(response_time, 95) as p95_response_time,
                    avg(cpu_percent) as avg_cpu,
                    avg(memory_mb) as avg_memory,
                    count(*) as total_requests,
                    sum(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests
                FROM performance_metrics
                WHERE test_name = ? AND operation = ? AND timestamp > ?
                GROUP BY date(timestamp)
                ORDER BY day DESC
            ''', (test_name, operation, cutoff_date.isoformat()))

            return cursor.fetchall()

    def get_performance_report(self, test_name, operation, days_back=7):
        """Generate a performance report"""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT
                    avg(response_time) as avg_response_time,
                    percentile(response_time, 95) as p95_response_time,
                    percentile(response_time, 99) as p99_response_time,
                    avg(cpu_percent) as avg_cpu,
                    avg(memory_mb) as avg_memory,
                    count(*) as total_requests,
                    sum(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests,
                    sum(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_requests
                FROM performance_metrics
                WHERE test_name = ? AND operation = ? AND timestamp > ?
            ''', (test_name, operation, cutoff_date.isoformat()))

            row = cursor.fetchone()

            if row:
                total_req, success_req, failed_req = row[5], row[6], row[7]
                success_rate = (success_req / total_req * 100) if total_req > 0 else 0

                return {
                    'test_name': test_name,
                    'operation': operation,
                    'days_back': days_back,
                    'avg_response_time': row[0],
                    'p95_response_time': row[1],
                    'p99_response_time': row[2],
                    'avg_cpu': row[3],
                    'avg_memory': row[4],
                    'total_requests': total_req,
                    'successful_requests': success_req,
                    'failed_requests': failed_req,
                    'success_rate': success_rate
                }

        return None

# Pytest plugin for automatic performance tracking
@pytest.fixture
def performance_tracker():
    """Performance tracker fixture"""
    tracker = PerformanceTracker()
    return tracker

@pytest.fixture
def track_performance(performance_tracker):
    """Performance tracking decorator fixture"""
    def _track(test_name, operation):
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()

                # Capture initial system metrics
                import psutil
                process = psutil.Process()
                initial_cpu = process.cpu_percent()
                initial_memory = process.memory_info().rss / 1024 / 1024

                try:
                    result = func(*args, **kwargs)
                    success = True
                    error_msg = None
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    raise
                finally:
                    end_time = time.perf_counter()
                    response_time = end_time - start_time

                    # Capture final system metrics
                    final_cpu = process.cpu_percent()
                    final_memory = process.memory_info().rss / 1024 / 1024

                    # Record the metric
                    performance_tracker.record_metric(
                        test_name=test_name,
                        operation=operation,
                        response_time=response_time,
                        success=success,
                        error_message=error_msg,
                        cpu_percent=(initial_cpu + final_cpu) / 2,
                        memory_mb=(initial_memory + final_memory) / 2
                    )

                return result
            return wrapper
        return decorator
    return _track

def test_customer_creation_with_tracking(track_performance):
    """Test customer creation with automatic performance tracking"""
    import requests

    # Apply performance tracking to the test
    @track_performance("customer_creation_test", "create_customer_api_call")
    def make_customer_request():
        response = requests.post("https://test-api.myapp.com/customers", json={
            'name': 'Tracked Test User',
            'email': 'tracked@example.com',
            'phone': '+1234567890'
        })
        return response

    # Make the request
    response = make_customer_request()
    assert response.status_code in [200, 201]

def test_generate_performance_report(performance_tracker):
    """Test generating performance reports"""
    # This would typically be run after collecting performance data
    report = performance_tracker.get_performance_report(
        test_name="customer_creation_test",
        operation="create_customer_api_call",
        days_back=7
    )

    if report:
        print(f"Performance Report for {report['test_name']} - {report['operation']}:")
        print(f"  Avg Response Time: {report['avg_response_time']:.3f}s")
        print(f"  P95 Response Time: {report['p95_response_time']:.3f}s")
        print(f"  P99 Response Time: {report['p99_response_time']:.3f}s")
        print(f"  Success Rate: {report['success_rate']:.2f}%")
        print(f"  Avg CPU: {report['avg_cpu']:.2f}%")
        print(f"  Avg Memory: {report['avg_memory']:.2f}MB")

        # Assert performance requirements
        assert report['success_rate'] >= 95.0, f"Success rate too low: {report['success_rate']:.2f}%"
        assert report['p95_response_time'] <= 1.0, f"P95 response time too high: {report['p95_response_time']:.3f}s"
```

This comprehensive performance testing guide provides all the necessary techniques and patterns for implementing effective performance testing in a pytest-based test suite.