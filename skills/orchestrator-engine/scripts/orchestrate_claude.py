#!/usr/bin/env python3
"""
Orchestrator Engine - Coordinate Claude Code runs and file processing

This script implements the core orchestration logic for triggering Claude Code runs,
routing files to appropriate watchers, and coordinating outputs.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProcessType(Enum):
    """Types of Claude Code processes that can be orchestrated"""
    FILE_PROCESSOR = "file_processor"
    WATCHER_COORDINATOR = "watcher_coordinator"
    WORKFLOW_EXECUTOR = "workflow_executor"
    ANALYSIS_RUNNER = "analysis_runner"


@dataclass
class ProcessConfig:
    """Configuration for a Claude Code process"""
    process_type: ProcessType
    input_path: str
    output_path: str
    config_file: Optional[str] = None
    additional_params: Dict[str, Any] = None


@dataclass
class RoutingRule:
    """Defines how files should be routed to different watchers"""
    pattern: str  # File pattern to match (glob or regex)
    watcher: str  # Target watcher name
    priority: int = 1  # Higher priority rules are checked first


class FileRouter:
    """Routes files to appropriate watchers based on rules and content analysis"""

    def __init__(self, routing_rules: List[RoutingRule]):
        self.routing_rules = sorted(routing_rules, key=lambda r: r.priority, reverse=True)

    def route_file(self, file_path: Path) -> str:
        """Determine which watcher should handle a file"""
        file_str = str(file_path)

        # Apply routing rules in priority order
        for rule in self.routing_rules:
            if self._matches_pattern(file_str, rule.pattern):
                logger.info(f"Routing {file_path} to {rule.watcher} based on pattern: {rule.pattern}")
                return rule.watcher

        # Default routing based on file extension
        extension = file_path.suffix.lower()
        if extension in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
            return 'code-analyzer'
        elif extension in ['.md', '.txt', '.rst']:
            return 'documentation-processor'
        elif extension in ['.json', '.yaml', '.yml', '.toml', '.ini']:
            return 'config-processor'
        elif extension in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
            return 'media-processor'
        else:
            return 'general-processor'

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches the given pattern"""
        # Simple glob matching (could be extended with regex support)
        from fnmatch import fnmatch
        return fnmatch(os.path.basename(file_path), pattern)


class ClaudeOrchestrator:
    """Main orchestrator for managing Claude Code processes"""

    def __init__(self, routing_rules: List[RoutingRule] = None):
        self.router = FileRouter(routing_rules or self._default_routing_rules())
        self.active_processes = {}
        self.process_queue = asyncio.Queue()

    def _default_routing_rules(self) -> List[RoutingRule]:
        """Default routing rules for common file types"""
        return [
            RoutingRule("**/*.py", "python-analyzer", priority=10),
            RoutingRule("**/*.js", "javascript-analyzer", priority=10),
            RoutingRule("**/*.ts", "typescript-analyzer", priority=10),
            RoutingRule("**/*.md", "markdown-processor", priority=10),
            RoutingRule("**/requirements*.txt", "dependency-analyzer", priority=15),
            RoutingRule("**/package*.json", "dependency-analyzer", priority=15),
            RoutingRule("**/Dockerfile", "container-analyzer", priority=15),
            RoutingRule("**/*.yaml", "config-processor", priority=5),
            RoutingRule("**/*.yml", "config-processor", priority=5),
            RoutingRule("**/CLAUDE.md", "specification-processor", priority=20),
            RoutingRule("**/README*", "documentation-processor", priority=5),
        ]

    async def process_file(self, file_path: Path) -> Optional[str]:
        """Process a single file by routing it to the appropriate Claude Code instance"""
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return None

        # Determine target watcher
        target_watcher = self.router.route_file(file_path)

        # Create process configuration
        config = ProcessConfig(
            process_type=ProcessType.FILE_PROCESSOR,
            input_path=str(file_path),
            output_path=str(file_path.parent / "processed" / file_path.name),
            additional_params={"watcher": target_watcher}
        )

        # Execute the process
        result = await self._execute_claude_process(config)
        return result

    async def process_directory(self, directory_path: Path, recursive: bool = True) -> Dict[str, str]:
        """Process all files in a directory, routing each appropriately"""
        results = {}

        # Collect all files to process
        if recursive:
            files = [f for f in directory_path.rglob("*") if f.is_file()]
        else:
            files = [f for f in directory_path.iterdir() if f.is_file()]

        # Process files concurrently with limited concurrency
        semaphore = asyncio.Semaphore(5)  # Limit concurrent processes

        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self.process_file(file_path)

        tasks = [process_with_semaphore(f) for f in files]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results back to file paths
        for file_path, result in zip(files, results_list):
            if isinstance(result, Exception):
                logger.error(f"Error processing {file_path}: {result}")
                results[str(file_path)] = f"ERROR: {str(result)}"
            else:
                results[str(file_path)] = result or "PROCESSED"

        return results

    async def _execute_claude_process(self, config: ProcessConfig) -> Optional[str]:
        """Execute a Claude Code process with the given configuration"""
        try:
            logger.info(f"Starting Claude process: {config.process_type.value} for {config.input_path}")

            # Create output directory if it doesn't exist
            output_dir = Path(config.output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build command based on process type
            cmd = self._build_command(config)

            # Execute the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully completed process for {config.input_path}")
                return stdout.decode() if stdout else "SUCCESS"
            else:
                logger.error(f"Process failed for {config.input_path}: {stderr.decode()}")
                return f"ERROR: {stderr.decode()}"

        except Exception as e:
            logger.error(f"Exception during process execution for {config.input_path}: {e}")
            return f"EXCEPTION: {str(e)}"

    def _build_command(self, config: ProcessConfig) -> List[str]:
        """Build command line for Claude Code execution"""
        # This is a simplified example - in reality, this would call Claude Code appropriately
        if config.config_file:
            return [
                "python", "-m", "claude_code",
                "--input", config.input_path,
                "--output", config.output_path,
                "--config", config.config_file
            ]
        else:
            # Default command for file processing
            return [
                "python", "-m", "claude_code",
                "--input", config.input_path,
                "--output", config.output_path
            ]

    async def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a multi-step workflow defined in the configuration"""
        results = {}

        steps = workflow_config.get("steps", [])
        for step in steps:
            step_name = step.get("name", "unnamed_step")
            logger.info(f"Executing workflow step: {step_name}")

            try:
                if step["type"] == "file_processing":
                    directory = Path(step["directory"])
                    recursive = step.get("recursive", True)
                    step_result = await self.process_directory(directory, recursive)
                    results[step_name] = step_result

                elif step["type"] == "custom_command":
                    # Execute a custom command as part of the workflow
                    cmd = step["command"]
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    results[step_name] = {
                        "returncode": process.returncode,
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else ""
                    }

                else:
                    logger.warning(f"Unknown step type: {step['type']}")
                    results[step_name] = f"UNKNOWN_STEP_TYPE: {step['type']}"

            except Exception as e:
                logger.error(f"Error in workflow step {step_name}: {e}")
                results[step_name] = f"ERROR: {str(e)}"

        return results


def main():
    """Main entry point for the orchestrator"""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator Engine for Claude Code processes")
    parser.add_argument("action", choices=["process-file", "process-dir", "execute-workflow"],
                       help="Action to perform")
    parser.add_argument("--path", required=True, help="Path to file or directory")
    parser.add_argument("--recursive", action="store_true",
                       help="Process directory recursively (for process-dir action)")
    parser.add_argument("--workflow-config", help="Path to workflow configuration file")

    args = parser.parse_args()

    # Initialize orchestrator with default rules
    orchestrator = ClaudeOrchestrator()

    async def run():
        if args.action == "process-file":
            file_path = Path(args.path)
            result = await orchestrator.process_file(file_path)
            print(f"Result: {result}")

        elif args.action == "process-dir":
            dir_path = Path(args.path)
            results = await orchestrator.process_directory(dir_path, args.recursive)
            print(json.dumps(results, indent=2))

        elif args.action == "execute-workflow":
            if not args.workflow_config:
                print("Error: --workflow-config required for execute-workflow action")
                sys.exit(1)

            config_path = Path(args.workflow_config)
            if not config_path.exists():
                print(f"Error: Workflow config file does not exist: {config_path}")
                sys.exit(1)

            with open(config_path, 'r') as f:
                workflow_config = json.load(f)

            results = await orchestrator.execute_workflow(workflow_config)
            print(json.dumps(results, indent=2))

    # Run the async function
    asyncio.run(run())


if __name__ == "__main__":
    main()