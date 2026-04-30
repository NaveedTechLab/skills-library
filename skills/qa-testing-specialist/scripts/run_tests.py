#!/usr/bin/env python3
"""
Test runner script with coverage and reporting
"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", coverage=False, verbose=False, markers=None):
    """Run tests with specified options"""

    # Build pytest command
    cmd = ["pytest"]

    # Add test path based on type
    test_paths = {
        "unit": "tests/unit",
        "integration": "tests/integration",
        "e2e": "tests/e2e",
        "social": "-k 'linkedin or twitter or facebook'",
        "webhook": "-k 'whatsapp or webhook'",
        "feedback": "-k 'feedback or learning'",
        "all": "tests/"
    }

    if test_type in test_paths:
        path = test_paths[test_type]
        if path.startswith("-k"):
            cmd.extend(path.split())
        else:
            cmd.append(path)

    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-report=xml"
        ])

    # Add verbose flag
    if verbose:
        cmd.append("-v")

    # Add custom markers
    if markers:
        cmd.extend(["-m", markers])

    # Add asyncio mode
    cmd.append("--asyncio-mode=auto")

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print()

    # Run tests
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✓ Tests passed successfully")
        if coverage:
            print("Coverage report generated in htmlcov/index.html")
    else:
        print("\n✗ Tests failed")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run tests with various options")
    parser.add_argument(
        "-t", "--type",
        choices=["all", "unit", "integration", "e2e", "social", "webhook", "feedback"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-m", "--markers",
        help="Custom pytest markers"
    )

    args = parser.parse_args()

    run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        markers=args.markers
    )

if __name__ == "__main__":
    main()
