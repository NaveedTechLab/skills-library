#!/usr/bin/env python3
"""
Watchdog Process Supervisor - Monitor and manage long-running processes

This script implements a robust process supervision system that monitors,
manages, and auto-restarts failed processes with comprehensive logging
and alerting capabilities.
"""

import asyncio
import json
import logging
import os
import psutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import yaml

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RestartPolicy(Enum):
    """Process restart policies"""
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    NEVER = "never"
    EXPONENTIAL_BACKOFF = "exponential-backoff"


@dataclass
class ProcessConfig:
    """Configuration for a supervised process"""
    name: str
    command: str
    restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    max_restarts: int = 5
    restart_window: int = 60  # seconds
    environment: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    autostart: bool = True
    stdout_file: Optional[str] = None
    stderr_file: Optional[str] = None


@dataclass
class ProcessState:
    """Current state of a supervised process"""
    process: Optional[psutil.Process] = None
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    exit_code: Optional[int] = None
    is_running: bool = False
    health_status: str = "unknown"  # healthy, unhealthy, unknown


class HealthChecker:
    """Health checker for processes"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.check_type = config.get('type', 'heartbeat')
        self.interval = config.get('interval', 30)
        self.timeout = config.get('timeout', 10)

    async def check_health(self, process_state: ProcessState) -> bool:
        """Check health of a process based on configuration"""
        if not process_state.is_running or not process_state.process:
            return False

        try:
            if self.check_type == 'heartbeat':
                return await self._check_heartbeat(process_state)
            elif self.check_type == 'resource':
                return await self._check_resource_usage(process_state)
            elif self.check_type == 'external':
                return await self._check_external(process_state)
            else:
                # Default: check if process is still alive
                return self._check_process_alive(process_state)
        except Exception as e:
            logger.error(f"Health check failed for {process_state.process.name() if process_state.process else 'unknown'}: {e}")
            return False

    def _check_process_alive(self, process_state: ProcessState) -> bool:
        """Basic check if process is still alive"""
        if not process_state.process:
            return False
        try:
            process_state.process.status()
            return process_state.process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    async def _check_heartbeat(self, process_state: ProcessState) -> bool:
        """Check heartbeat file or network endpoint"""
        # This would typically check for a heartbeat file or ping an endpoint
        # Implementation depends on how the process signals health
        return self._check_process_alive(process_state)

    async def _check_resource_usage(self, process_state: ProcessState) -> bool:
        """Check if process is within resource limits"""
        if not process_state.process:
            return False

        try:
            # Check CPU usage
            cpu_percent = process_state.process.cpu_percent()
            mem_info = process_state.process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024  # Convert to MB

            cpu_limit = self.config.get('cpu_percent', 90)
            mem_limit = self.config.get('memory_mb', 1024)

            if cpu_percent > cpu_limit:
                logger.warning(f"Process {process_state.process.name()} CPU usage {cpu_percent}% exceeds limit {cpu_limit}%")
                return False

            if mem_mb > mem_limit:
                logger.warning(f"Process {process_state.process.name()} memory usage {mem_mb:.2f}MB exceeds limit {mem_limit}MB")
                return False

            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            logger.error(f"Resource check failed: {e}")
            return False

    async def _check_external(self, process_state: ProcessState) -> bool:
        """Check external health endpoint"""
        # Implementation for checking external health endpoint
        return self._check_process_alive(process_state)


class AlertManager:
    """Manages alerting and notifications"""

    def __init__(self):
        self.alert_handlers: List[Callable] = []

    def add_alert_handler(self, handler: Callable):
        """Add an alert handler function"""
        self.alert_handlers.append(handler)

    def alert_process_failure(self, process_name: str, exit_code: Optional[int] = None):
        """Send alert when process fails"""
        message = f"Process {process_name} failed"
        if exit_code is not None:
            message += f" with exit code {exit_code}"

        logger.error(message)
        self._notify_handlers("process_failure", message, process_name=process_name, exit_code=exit_code)

    def alert_restart_limit_exceeded(self, process_name: str):
        """Send alert when restart limit is exceeded"""
        message = f"Restart limit exceeded for process {process_name}"
        logger.error(message)
        self._notify_handlers("restart_limit_exceeded", message, process_name=process_name)

    def alert_resource_violation(self, process_name: str, resource: str, value: Any, limit: Any):
        """Send alert when resource limit is violated"""
        message = f"Resource violation for {process_name}: {resource}={value}, limit={limit}"
        logger.warning(message)
        self._notify_handlers("resource_violation", message, process_name=process_name, resource=resource, value=value, limit=limit)

    def _notify_handlers(self, alert_type: str, message: str, **kwargs):
        """Notify all registered alert handlers"""
        for handler in self.alert_handlers:
            try:
                handler(alert_type, message, **kwargs)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")


class ProcessSupervisor:
    """Main process supervisor that manages all supervised processes"""

    def __init__(self):
        self.process_configs: Dict[str, ProcessConfig] = {}
        self.process_states: Dict[str, ProcessState] = {}
        self.health_checkers: Dict[str, HealthChecker] = {}
        self.alert_manager = AlertManager()
        self.running = False
        self.processes: Dict[str, subprocess.Popen] = {}

    def add_process(self, config: ProcessConfig):
        """Add a process to be supervised"""
        self.process_configs[config.name] = config
        self.process_states[config.name] = ProcessState()
        if config.health_check:
            self.health_checkers[config.name] = HealthChecker(config.health_check)
        logger.info(f"Added process {config.name} for supervision")

    def load_config(self, config_path: str):
        """Load process configurations from file"""
        path = Path(config_path)
        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        processes = data.get('processes', [])
        for proc_data in processes:
            config = ProcessConfig(
                name=proc_data['name'],
                command=proc_data['command'],
                restart_policy=RestartPolicy(proc_data.get('restart_policy', 'always')),
                max_restarts=proc_data.get('max_restarts', 5),
                restart_window=proc_data.get('restart_window', 60),
                environment=proc_data.get('environment', {}),
                working_dir=proc_data.get('working_dir'),
                resource_limits=proc_data.get('resource_limits', {}),
                health_check=proc_data.get('health_check', {}),
                autostart=proc_data.get('autostart', True),
                stdout_file=proc_data.get('stdout_file'),
                stderr_file=proc_data.get('stderr_file')
            )
            self.add_process(config)

    def start_process(self, name: str) -> bool:
        """Start a supervised process"""
        if name not in self.process_configs:
            logger.error(f"Process {name} not configured")
            return False

        config = self.process_configs[name]
        state = self.process_states[name]

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(config.environment)

            # Prepare working directory
            cwd = config.working_dir or os.getcwd()

            # Prepare output files
            stdout_fd = None
            stderr_fd = None
            if config.stdout_file:
                stdout_fd = open(config.stdout_file, 'a')
            if config.stderr_file:
                stderr_fd = open(config.stderr_file, 'a')

            # Start the process
            process = subprocess.Popen(
                config.command.split(),
                env=env,
                cwd=cwd,
                stdout=stdout_fd or subprocess.PIPE,
                stderr=stderr_fd or subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            # Update state
            state.process = psutil.Process(process.pid)
            state.pid = process.pid
            state.start_time = datetime.now()
            state.is_running = True
            state.exit_code = None

            self.processes[name] = process

            logger.info(f"Started process {name} with PID {process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start process {name}: {e}")
            return False

    def stop_process(self, name: str, timeout: int = 10) -> bool:
        """Stop a supervised process gracefully"""
        if name not in self.processes:
            logger.warning(f"Process {name} not running")
            return True

        process = self.processes[name]
        state = self.process_states[name]

        try:
            # Try graceful shutdown first
            process.terminate()

            try:
                process.wait(timeout=timeout)
                logger.info(f"Process {name} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                logger.warning(f"Process {name} did not stop gracefully, killing...")
                process.kill()
                process.wait()
                logger.info(f"Process {name} killed")

            # Update state
            state.is_running = False
            if hasattr(process, 'returncode'):
                state.exit_code = process.returncode

            del self.processes[name]
            return True

        except Exception as e:
            logger.error(f"Failed to stop process {name}: {e}")
            return False

    async def monitor_processes(self):
        """Monitor all processes for failures and health"""
        while self.running:
            for name in list(self.process_configs.keys()):
                if name not in self.processes:
                    # Process is not running, check if it should be restarted
                    await self._handle_process_not_running(name)
                else:
                    # Process is running, check health
                    await self._check_process_health(name)

            # Sleep before next check
            await asyncio.sleep(1)

    async def _handle_process_not_running(self, name: str):
        """Handle case where a process is not running"""
        config = self.process_configs[name]
        state = self.process_states[name]

        # If process was running before, it means it crashed
        if state.is_running:
            logger.warning(f"Process {name} has stopped unexpectedly")

            # Alert about the failure
            self.alert_manager.alert_process_failure(name, state.exit_code)

            # Check restart policy
            should_restart = self._should_restart(name)

            if should_restart:
                logger.info(f"Restarting process {name}...")
                await self._restart_process(name)
            else:
                logger.warning(f"Not restarting process {name} due to restart policy")

        elif config.autostart and not state.is_running:
            # Process should be running but isn't, start it
            logger.info(f"Starting process {name}...")
            self.start_process(name)

    def _should_restart(self, name: str) -> bool:
        """Determine if a process should be restarted based on policy and limits"""
        config = self.process_configs[name]
        state = self.process_states[name]

        # Check restart policy
        if config.restart_policy == RestartPolicy.NEVER:
            return False
        elif config.restart_policy == RestartPolicy.ON_FAILURE:
            # Only restart if process exited with non-zero code
            if state.exit_code == 0:
                return False
        elif config.restart_policy == RestartPolicy.EXPONENTIAL_BACKOFF:
            # Implement exponential backoff logic
            if state.last_restart:
                # Calculate delay based on restart count
                delay = min(2 ** state.restart_count, 300)  # Max 5 minutes
                time_since_last = datetime.now() - state.last_restart
                if time_since_last < timedelta(seconds=delay):
                    return False

        # Check restart limits
        if state.last_restart:
            time_since_window_start = datetime.now() - state.last_restart
            if time_since_window_start < timedelta(seconds=config.restart_window):
                if state.restart_count >= config.max_restarts:
                    logger.error(f"Restart limit exceeded for {name}")
                    self.alert_manager.alert_restart_limit_exceeded(name)
                    return False

        return True

    async def _restart_process(self, name: str):
        """Restart a process with appropriate delay"""
        config = self.process_configs[name]
        state = self.process_states[name]

        # Update restart tracking
        state.restart_count += 1
        state.last_restart = datetime.now()

        # Apply restart delay if needed
        if config.restart_policy == RestartPolicy.EXPONENTIAL_BACKOFF:
            delay = min(2 ** (state.restart_count - 1), 300)  # Max 5 minutes
            logger.info(f"Waiting {delay}s before restarting {name} (attempt {state.restart_count})")
            await asyncio.sleep(delay)

        # Start the process
        success = self.start_process(name)
        if success:
            logger.info(f"Successfully restarted {name} (attempt {state.restart_count})")
        else:
            logger.error(f"Failed to restart {name}")

    async def _check_process_health(self, name: str):
        """Check health of a running process"""
        if name not in self.health_checkers:
            return  # No health checker configured

        state = self.process_states[name]
        health_checker = self.health_checkers[name]

        is_healthy = await health_checker.check_health(state)
        state.health_status = "healthy" if is_healthy else "unhealthy"

        if not is_healthy:
            logger.warning(f"Process {name} is unhealthy, stopping...")
            await self._handle_unhealthy_process(name)

    async def _handle_unhealthy_process(self, name: str):
        """Handle an unhealthy process"""
        # Stop the unhealthy process
        await self._stop_and_restart_process(name)

    async def _stop_and_restart_process(self, name: str):
        """Stop and restart a process"""
        # Stop the process
        self.stop_process(name)

        # Mark as not running
        state = self.process_states[name]
        state.is_running = False

        # Handle as if it crashed (will apply restart policy)
        await self._handle_process_not_running(name)

    async def start(self):
        """Start the supervisor and all configured processes"""
        logger.info("Starting process supervisor...")
        self.running = True

        # Start all processes that should auto-start
        for name, config in self.process_configs.items():
            if config.autostart:
                self.start_process(name)

        # Start monitoring
        await self.monitor_processes()

    async def stop(self):
        """Stop the supervisor and all managed processes"""
        logger.info("Stopping process supervisor...")
        self.running = False

        # Stop all managed processes
        for name in list(self.processes.keys()):
            self.stop_process(name)

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all processes"""
        status = {}
        for name, state in self.process_states.items():
            status[name] = {
                'name': name,
                'is_running': state.is_running,
                'pid': state.pid,
                'start_time': state.start_time.isoformat() if state.start_time else None,
                'restart_count': state.restart_count,
                'last_restart': state.last_restart.isoformat() if state.last_restart else None,
                'exit_code': state.exit_code,
                'health_status': state.health_status
            }
        return status


def main():
    """Main entry point for the process supervisor"""
    import argparse

    parser = argparse.ArgumentParser(description="Watchdog Process Supervisor")
    parser.add_argument("action", choices=["start", "stop", "status", "monitor"],
                       help="Action to perform")
    parser.add_argument("--config", required=True,
                       help="Path to configuration file")
    parser.add_argument("--log-file", help="Path to log file")

    args = parser.parse_args()

    # Set up logging to file if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

    supervisor = ProcessSupervisor()

    try:
        # Load configuration
        supervisor.load_config(args.config)

        if args.action == "start":
            logger.info("Starting supervisor with configuration from {}".format(args.config))
            # In a real scenario, we'd run this in the background
            # For now, just start the processes
            for name, config in supervisor.process_configs.items():
                if config.autostart:
                    supervisor.start_process(name)
            print("Processes started. Use 'monitor' action to supervise.")

        elif args.action == "monitor":
            logger.info("Starting process monitoring...")
            asyncio.run(supervisor.start())

        elif args.action == "stop":
            logger.info("Stopping supervisor...")
            asyncio.run(supervisor.stop())
            print("Supervisor stopped.")

        elif args.action == "status":
            status = supervisor.get_status()
            print(json.dumps(status, indent=2))

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping supervisor...")
        asyncio.run(supervisor.stop())
    except Exception as e:
        logger.error(f"Error running supervisor: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()