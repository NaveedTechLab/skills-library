#!/usr/bin/env python3
"""
Health Monitor for Watchdog Process Manager

Monitors system and process health, tracks metrics, and provides health reporting.
"""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: Optional[float]
    network_io: Dict[str, int]
    process_count: int


@dataclass
class ProcessMetrics:
    """Individual process metrics"""
    name: str
    pid: int
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    num_threads: int
    connections: int
    created_at: datetime


class HealthMonitor:
    """Monitors system and process health"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.system_history: List[SystemMetrics] = []
        self.process_history: Dict[str, List[ProcessMetrics]] = {}
        self.max_history = 100  # Keep last 100 measurements

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load health monitoring configuration"""
        default_config = {
            "system_thresholds": {
                "cpu_percent": 90,
                "memory_percent": 90,
                "disk_percent": 90,
                "process_count": 1000
            },
            "process_thresholds": {
                "cpu_percent": 80,
                "memory_mb": 1024,
                "num_threads": 100
            },
            "collection_interval": 30,  # seconds
            "alert_on_violation": True
        }

        if config_path and Path(config_path).exists():
            path = Path(config_path)
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                else:
                    file_config = json.load(f)
            default_config.update(file_config)

        return default_config

    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect system-wide metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk usage (root partition)
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100

        # Load average (Unix-like systems)
        load_avg = None
        try:
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
        except:
            pass

        # Network I/O
        net_io = psutil.net_io_counters()
        network_io = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }

        # Process count
        process_count = len(list(psutil.process_iter()))

        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            load_average=load_avg,
            network_io=network_io,
            process_count=process_count
        )

        # Store in history
        self.system_history.append(metrics)
        if len(self.system_history) > self.max_history:
            self.system_history.pop(0)

        return metrics

    async def collect_process_metrics(self, process_name: str, pid: int) -> Optional[ProcessMetrics]:
        """Collect metrics for a specific process"""
        try:
            proc = psutil.Process(pid)

            # Get process metrics
            cpu_percent = proc.cpu_percent()
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            memory_percent = proc.memory_percent()
            status = proc.status()
            num_threads = proc.num_threads()
            connections = len(proc.connections())

            metrics = ProcessMetrics(
                name=process_name,
                pid=pid,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                status=status,
                num_threads=num_threads,
                connections=connections,
                created_at=datetime.fromtimestamp(proc.create_time())
            )

            # Store in history
            if process_name not in self.process_history:
                self.process_history[process_name] = []
            self.process_history[process_name].append(metrics)
            if len(self.process_history[process_name]) > self.max_history:
                self.process_history[process_name].pop(0)

            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Could not collect metrics for process {process_name} (PID {pid}): {e}")
            return None

    def check_system_health(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """Check if system metrics are within thresholds"""
        violations = []
        thresholds = self.config['system_thresholds']

        if metrics.cpu_percent > thresholds['cpu_percent']:
            violations.append({
                'metric': 'cpu_percent',
                'value': metrics.cpu_percent,
                'threshold': thresholds['cpu_percent'],
                'severity': 'warning'
            })

        if metrics.memory_percent > thresholds['memory_percent']:
            violations.append({
                'metric': 'memory_percent',
                'value': metrics.memory_percent,
                'threshold': thresholds['memory_percent'],
                'severity': 'warning'
            })

        if metrics.disk_percent > thresholds['disk_percent']:
            violations.append({
                'metric': 'disk_percent',
                'value': metrics.disk_percent,
                'threshold': thresholds['disk_percent'],
                'severity': 'warning'
            })

        if metrics.process_count > thresholds['process_count']:
            violations.append({
                'metric': 'process_count',
                'value': metrics.process_count,
                'threshold': thresholds['process_count'],
                'severity': 'warning'
            })

        return {
            'healthy': len(violations) == 0,
            'violations': violations,
            'metrics': {
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'disk_percent': metrics.disk_percent,
                'process_count': metrics.process_count
            }
        }

    def check_process_health(self, metrics: ProcessMetrics) -> Dict[str, Any]:
        """Check if process metrics are within thresholds"""
        violations = []
        thresholds = self.config['process_thresholds']

        if metrics.cpu_percent > thresholds['cpu_percent']:
            violations.append({
                'metric': 'cpu_percent',
                'value': metrics.cpu_percent,
                'threshold': thresholds['cpu_percent'],
                'severity': 'warning'
            })

        if metrics.memory_mb > thresholds['memory_mb']:
            violations.append({
                'metric': 'memory_mb',
                'value': metrics.memory_mb,
                'threshold': thresholds['memory_mb'],
                'severity': 'warning'
            })

        if metrics.num_threads > thresholds['num_threads']:
            violations.append({
                'metric': 'num_threads',
                'value': metrics.num_threads,
                'threshold': thresholds['num_threads'],
                'severity': 'warning'
            })

        return {
            'healthy': len(violations) == 0,
            'violations': violations,
            'metrics': {
                'cpu_percent': metrics.cpu_percent,
                'memory_mb': metrics.memory_mb,
                'num_threads': metrics.num_threads,
                'status': metrics.status
            }
        }

    def get_system_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive system health report"""
        if not self.system_history:
            return {'error': 'No system metrics collected yet'}

        latest = self.system_history[-1]
        return {
            'timestamp': latest.timestamp.isoformat(),
            'system_health': self.check_system_health(latest),
            'trend_analysis': self._analyze_trends(),
            'resource_usage': {
                'cpu_percent': latest.cpu_percent,
                'memory_percent': latest.memory_percent,
                'disk_percent': latest.disk_percent,
                'process_count': latest.process_count
            }
        }

    def get_process_health_report(self, process_name: str) -> Dict[str, Any]:
        """Generate a health report for a specific process"""
        if process_name not in self.process_history or not self.process_history[process_name]:
            return {'error': f'No metrics collected for process {process_name}'}

        latest = self.process_history[process_name][-1]
        return {
            'process_name': process_name,
            'timestamp': latest.created_at.isoformat(),
            'process_health': self.check_process_health(latest),
            'metrics': {
                'cpu_percent': latest.cpu_percent,
                'memory_mb': latest.memory_mb,
                'num_threads': latest.num_threads,
                'status': latest.status,
                'pid': latest.pid
            }
        }

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze trends in system metrics"""
        if len(self.system_history) < 2:
            return {'error': 'Insufficient data for trend analysis'}

        # Calculate trends for key metrics
        cpu_values = [m.cpu_percent for m in self.system_history[-10:]]  # Last 10 readings
        memory_values = [m.memory_percent for m in self.system_history[-10:]]

        def calculate_trend(values):
            if len(values) < 2:
                return 'stable'
            recent_avg = sum(values[-3:]) / 3  # Average of last 3
            earlier_avg = sum(values[:-3][-3:]) / 3  # Average of 3 before that
            if recent_avg > earlier_avg * 1.1:
                return 'increasing'
            elif recent_avg < earlier_avg * 0.9:
                return 'decreasing'
            else:
                return 'stable'

        return {
            'cpu_trend': calculate_trend(cpu_values),
            'memory_trend': calculate_trend(memory_values),
            'data_points': len(self.system_history)
        }

    async def run_monitoring_loop(self, target_processes: List[Dict[str, Any]], output_file: Optional[str] = None):
        """Run continuous monitoring loop"""
        logger.info("Starting health monitoring loop...")

        interval = self.config.get('collection_interval', 30)

        while True:
            try:
                # Collect system metrics
                system_metrics = await self.collect_system_metrics()
                system_health = self.check_system_health(system_metrics)

                # Check for violations and alert if needed
                if system_health['violations'] and self.config.get('alert_on_violation'):
                    for violation in system_health['violations']:
                        logger.warning(f"System health violation: {violation}")

                # Collect process metrics
                for proc_info in target_processes:
                    process_name = proc_info['name']
                    pid = proc_info['pid']
                    process_metrics = await self.collect_process_metrics(process_name, pid)
                    if process_metrics:
                        process_health = self.check_process_health(process_metrics)

                        # Check for violations and alert if needed
                        if process_health['violations'] and self.config.get('alert_on_violation'):
                            for violation in process_health['violations']:
                                logger.warning(f"Process {process_name} health violation: {violation}")

                # Output to file if specified
                if output_file:
                    await self._write_health_report(output_file)

                await asyncio.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Health monitoring interrupted")
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(interval)

    async def _write_health_report(self, output_file: str):
        """Write health report to file"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'system_health': self.get_system_health_report(),
            'processes': {}
        }

        # Add process health reports
        for process_name in self.process_history.keys():
            report['processes'][process_name] = self.get_process_health_report(process_name)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)


def main():
    """Main entry point for health monitor"""
    import argparse

    parser = argparse.ArgumentParser(description="Health Monitor for Watchdog Process Manager")
    parser.add_argument("action", choices=["collect", "report", "monitor"],
                       help="Action to perform")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--process", action="append", nargs=2, metavar=("NAME", "PID"),
                       help="Process to monitor (can be used multiple times)")
    parser.add_argument("--output", help="Output file for health reports")
    parser.add_argument("--log-file", help="Path to log file")

    args = parser.parse_args()

    # Set up logging
    if args.log_file:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(args.log_file)]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    monitor = HealthMonitor(args.config)

    if args.action == "collect":
        # Just collect metrics once
        import asyncio
        metrics = asyncio.run(monitor.collect_system_metrics())
        print(json.dumps({
            'timestamp': metrics.timestamp.isoformat(),
            'cpu_percent': metrics.cpu_percent,
            'memory_percent': metrics.memory_percent,
            'disk_percent': metrics.disk_percent,
            'process_count': metrics.process_count
        }, indent=2))

    elif args.action == "report":
        # Generate health report
        report = monitor.get_system_health_report()
        print(json.dumps(report, indent=2))

        # Add process reports if processes specified
        if args.process:
            for name, pid in args.process:
                proc_report = monitor.get_process_health_report(name)
                print(f"\n{name} Report:")
                print(json.dumps(proc_report, indent=2))

    elif args.action == "monitor":
        # Continuous monitoring
        target_processes = []
        if args.process:
            for name, pid_str in args.process:
                target_processes.append({'name': name, 'pid': int(pid_str)})

        import asyncio
        asyncio.run(monitor.run_monitoring_loop(target_processes, args.output))


if __name__ == "__main__":
    main()