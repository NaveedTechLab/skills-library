#!/usr/bin/env python3
"""
Advanced Cron Expression Parser for Scheduler Cron Integration

Implements comprehensive cron expression parsing with support for various formats
and extensions including seconds, named months/days, and predefined schedules.
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union
from zoneinfo import ZoneInfo

import structlog
from croniter import croniter

logger = structlog.get_logger()


class CronField:
    """Represents a single field in a cron expression"""

    def __init__(self, field_value: str, min_val: int, max_val: int, names: Optional[dict] = None):
        self.field_value = field_value
        self.min_val = min_val
        self.max_val = max_val
        self.names = names or {}
        self.values = self._parse_field()

    def _parse_field(self) -> List[int]:
        """Parse the cron field and return a list of valid values"""
        if self.field_value == '*':
            return list(range(self.min_val, self.max_val + 1))

        values = []
        for part in self.field_value.split(','):
            part = part.strip()

            # Handle step values (e.g., */2, 2-10/2)
            if '/' in part:
                range_part, step = part.split('/')
                step = int(step)

                if range_part == '*':
                    # Handle */n format
                    values.extend(list(range(self.min_val, self.max_val + 1, step)))
                else:
                    # Handle range with step (e.g., 2-10/2)
                    if '-' in range_part:
                        start, end = map(int, range_part.split('-'))
                        values.extend(list(range(start, end + 1, step)))
                    else:
                        # Single value with step doesn't make sense, treat as just the value
                        val = self._convert_name(part)
                        if self.min_val <= val <= self.max_val:
                            values.append(val)
            elif '-' in part:
                # Handle range (e.g., 1-5)
                start, end = part.split('-')
                start = self._convert_name(start)
                end = self._convert_name(end)
                if self.min_val <= start <= self.max_val and self.min_val <= end <= self.max_val:
                    values.extend(list(range(start, end + 1)))
            else:
                # Handle single value
                val = self._convert_name(part)
                if self.min_val <= val <= self.max_val:
                    values.append(val)

        return sorted(set(values))  # Remove duplicates and sort

    def _convert_name(self, value: str) -> int:
        """Convert named values (like JAN, MON) to numbers"""
        value = value.upper()
        if value in self.names:
            return self.names[value]
        return int(value)

    def matches(self, value: int) -> bool:
        """Check if the given value matches this field"""
        return value in self.values

    def next_match(self, current_value: int) -> int:
        """Get the next matching value greater than current_value"""
        for val in self.values:
            if val > current_value:
                return val
        return self.values[0] if self.values else current_value


class CronExpression:
    """Parsed representation of a cron expression"""

    # Month names mapping
    MONTH_NAMES = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    # Day names mapping
    DAY_NAMES = {
        'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6
    }

    def __init__(self, expression: str):
        self.original_expression = expression
        self.has_seconds = False
        self.fields = self._parse_expression(expression)

    def _parse_expression(self, expr: str) -> dict:
        """Parse the cron expression into fields"""
        # Normalize the expression
        expr = expr.strip().upper()

        # Predefined aliases
        aliases = {
            '@YEARLY': '0 0 1 1 *',
            '@ANNUALLY': '0 0 1 1 *',
            '@MONTHLY': '0 0 1 * *',
            '@WEEKLY': '0 0 * * 0',
            '@DAILY': '0 0 * * *',
            '@MIDNIGHT': '0 0 * * *',
            '@HOURLY': '0 * * * *',
            '@MINUTELY': '* * * * *'
        }

        # Check for aliases
        if expr in aliases:
            expr = aliases[expr]
        elif expr.startswith('@EVERY_'):  # Custom extension for intervals like @EVERY_5MIN
            # Parse custom intervals
            match = re.match(r'@EVERY_(\d+)([SMHDW])', expr)
            if match:
                num, unit = match.groups()
                num = int(num)
                if unit == 'S':  # Seconds
                    expr = f'*/{num} * * * * *'  # With seconds
                    self.has_seconds = True
                elif unit == 'M':  # Minutes
                    expr = f'0 */{num} * * * *'  # With seconds
                    self.has_seconds = True
                elif unit == 'H':  # Hours
                    expr = f'0 0 */{num} * * *'  # With seconds
                    self.has_seconds = True
                elif unit == 'D':  # Days
                    expr = f'0 0 0 */{num} * *'  # With seconds
                    self.has_seconds = True
                elif unit == 'W':  # Weeks
                    expr = f'0 0 0 */{num * 7} * *'  # With seconds
                    self.has_seconds = True

        # Split the expression
        parts = expr.split()

        # Determine if we have seconds (6 parts) or not (5 parts)
        if len(parts) == 6:
            self.has_seconds = True
            second, minute, hour, day, month, dow = parts
            fields = {
                'second': CronField(second, 0, 59),
                'minute': CronField(minute, 0, 59),
                'hour': CronField(hour, 0, 23),
                'day': CronField(day, 1, 31),
                'month': CronField(month, 1, 12, self.MONTH_NAMES),
                'dow': CronField(dow, 0, 7, self.DAY_NAMES)  # 0 and 7 are both Sunday
            }
        elif len(parts) == 5:
            minute, hour, day, month, dow = parts
            fields = {
                'minute': CronField(minute, 0, 59),
                'hour': CronField(hour, 0, 23),
                'day': CronField(day, 1, 31),
                'month': CronField(month, 1, 12, self.MONTH_NAMES),
                'dow': CronField(dow, 0, 7, self.DAY_NAMES)  # 0 and 7 are both Sunday
            }
        else:
            raise ValueError(f"Invalid cron expression: {expr}. Expected 5 or 6 fields.")

        return fields

    def matches_datetime(self, dt: datetime) -> bool:
        """Check if the expression matches the given datetime"""
        # Adjust for dow field - both 0 and 7 represent Sunday
        dow = dt.weekday()  # Monday is 0, Sunday is 6
        adjusted_dow = 0 if dow == 6 else dow + 1  # Convert to cron format (Sunday=0)

        if self.has_seconds:
            return (self.fields['second'].matches(dt.second) and
                    self.fields['minute'].matches(dt.minute) and
                    self.fields['hour'].matches(dt.hour) and
                    self.fields['day'].matches(dt.day) and
                    self.fields['month'].matches(dt.month) and
                    (self.fields['dow'].matches(dow) or self.fields['dow'].matches(adjusted_dow)))
        else:
            return (self.fields['minute'].matches(dt.minute) and
                    self.fields['hour'].matches(dt.hour) and
                    self.fields['day'].matches(dt.day) and
                    self.fields['month'].matches(dt.month) and
                    (self.fields['dow'].matches(dow) or self.fields['dow'].matches(adjusted_dow)))

    def get_next_datetime(self, from_dt: datetime) -> datetime:
        """Get the next datetime that matches this expression"""
        # Start from the next second
        current = from_dt + timedelta(seconds=1)

        # Try up to a reasonable limit to avoid infinite loops
        max_attempts = 1000000

        for _ in range(max_attempts):
            if self.matches_datetime(current):
                return current

            # Increment by one unit depending on precision needed
            if self.has_seconds:
                current = current + timedelta(seconds=1)
            else:
                # If no seconds field, go to next minute
                current = current.replace(second=0) + timedelta(minutes=1)

        raise ValueError(f"Could not find next match for expression {self.original_expression} within reasonable time")

    def get_next_n_datetimes(self, from_dt: datetime, n: int) -> List[datetime]:
        """Get the next n datetimes that match this expression"""
        results = []
        current = from_dt

        for _ in range(n):
            current = self.get_next_datetime(current)
            results.append(current)

        return results


class AdvancedCronParser:
    """Advanced cron parser with validation and utility functions"""

    def __init__(self):
        self.common_expressions = {
            # Every minute
            '* * * * *': 'Every minute',
            # Every hour
            '0 * * * *': 'Every hour at minute 0',
            # Every day at midnight
            '0 0 * * *': 'Every day at midnight',
            # Every day at noon
            '0 12 * * *': 'Every day at noon',
            # Weekdays at 9 AM
            '0 9 * * 1-5': 'Weekdays at 9 AM',
            # Weekends at 10 AM
            '0 10 * * 0,6': 'Weekends at 10 AM',
            # First day of month
            '0 0 1 * *': 'First day of every month',
            # Last day of month (approximate)
            '0 0 28 * *': 'Around the end of each month',
            # Monthly on the 15th
            '0 0 15 * *': 'Mid-month',
        }

    def parse(self, expression: str) -> CronExpression:
        """Parse a cron expression"""
        try:
            return CronExpression(expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{expression}': {str(e)}")

    def validate(self, expression: str) -> Tuple[bool, str]:
        """Validate a cron expression and return (is_valid, error_message)"""
        try:
            self.parse(expression)
            return True, ""
        except ValueError as e:
            return False, str(e)

    def normalize(self, expression: str) -> str:
        """Normalize a cron expression (expand aliases, standardize format)"""
        expr = expression.strip().upper()

        # Predefined aliases
        aliases = {
            '@YEARLY': '0 0 1 1 *',
            '@ANNUALLY': '0 0 1 1 *',
            '@MONTHLY': '0 0 1 * *',
            '@WEEKLY': '0 0 * * 0',
            '@DAILY': '0 0 * * *',
            '@MIDNIGHT': '0 0 * * *',
            '@HOURLY': '0 * * * *',
            '@MINUTELY': '* * * * *'
        }

        if expr in aliases:
            return aliases[expr]

        # Return the original expression if not an alias
        return expression

    def get_human_readable(self, expression: str) -> str:
        """Convert a cron expression to human-readable format"""
        normalized = self.normalize(expression)

        # Check for common expressions
        if normalized in self.common_expressions:
            return self.common_expressions[normalized]

        # Try to interpret the expression
        try:
            parsed = CronExpression(expression)
            parts = expression.split()

            if len(parts) == 6:  # Has seconds
                sec, min_val, hour, day, month, dow = parts
            else:  # No seconds
                min_val, hour, day, month, dow = parts

            # Build human description
            desc_parts = []

            # Minute part
            if min_val == '*':
                desc_parts.append("every minute")
            elif min_val.startswith('*/'):
                interval = min_val[2:]
                desc_parts.append(f"every {interval} minutes")
            else:
                desc_parts.append(f"at minute(s) {min_val}")

            # Hour part
            if hour == '*':
                desc_parts.append("every hour")
            elif hour.startswith('*/'):
                interval = hour[2:]
                desc_parts.append(f"every {interval} hours")
            else:
                desc_parts.append(f"at hour(s) {hour}")

            # Day part
            if day == '*':
                desc_parts.append("every day")
            else:
                desc_parts.append(f"on day(s) {day}")

            # Month part
            if month == '*':
                desc_parts.append("every month")
            else:
                desc_parts.append(f"in month(s) {month}")

            # Day of week part
            if dow == '*':
                desc_parts.append("every day of the week")
            else:
                desc_parts.append(f"on day(s) of week {dow}")

            return f"At {' and '.join(desc_parts)}"

        except Exception:
            return f"Complex expression: {expression}"

    def get_next_run_time(self, expression: str, from_time: Optional[datetime] = None) -> datetime:
        """Calculate the next run time for a cron expression"""
        if from_time is None:
            from_time = datetime.now()

        parsed = self.parse(expression)
        return parsed.get_next_datetime(from_time)

    def get_next_n_run_times(self, expression: str, n: int, from_time: Optional[datetime] = None) -> List[datetime]:
        """Get the next N run times for a cron expression"""
        if from_time is None:
            from_time = datetime.now()

        parsed = self.parse(expression)
        return parsed.get_next_n_datetimes(from_time, n)


# Backward compatibility wrapper for the original CronExpressionParser class
class CronExpressionParser:
    """Legacy class for backward compatibility"""

    def __init__(self):
        self.advanced_parser = AdvancedCronParser()

    def normalize_expression(self, expression: str) -> str:
        """Normalize a cron expression (handle aliases, etc.)"""
        return self.advanced_parser.normalize(expression)

    def get_next_run_time(self, expression: str, from_time: Optional[datetime] = None) -> datetime:
        """Calculate the next run time for a cron expression"""
        return self.advanced_parser.get_next_run_time(expression, from_time)

    def get_next_n_run_times(self, expression: str, n: int, from_time: Optional[datetime] = None) -> List[datetime]:
        """Get the next N run times for a cron expression"""
        return self.advanced_parser.get_next_n_run_times(expression, n, from_time)


# Utility functions
def is_valid_cron_expression(expression: str) -> bool:
    """Check if a cron expression is valid"""
    parser = AdvancedCronParser()
    is_valid, _ = parser.validate(expression)
    return is_valid


def get_next_run_time(expression: str, from_time: Optional[datetime] = None) -> datetime:
    """Get the next run time for a cron expression"""
    parser = AdvancedCronParser()
    return parser.get_next_run_time(expression, from_time)


def parse_cron_expression(expression: str) -> CronExpression:
    """Parse a cron expression into a CronExpression object"""
    parser = AdvancedCronParser()
    return parser.parse(expression)


def cron_to_human_readable(expression: str) -> str:
    """Convert a cron expression to human-readable format"""
    parser = AdvancedCronParser()
    return parser.get_human_readable(expression)


if __name__ == "__main__":
    # Demo of cron parser functionality
    print("Advanced Cron Parser Demo")
    print("=" * 40)

    parser = AdvancedCronParser()

    # Test various cron expressions
    test_expressions = [
        "0 9 * * *",           # Daily at 9 AM
        "0 2 * * 0",           # Weekly on Sunday at 2 AM
        "0 0 1 * *",           # Monthly on the 1st at midnight
        "*/15 * * * *",        # Every 15 minutes
        "@daily",              # Daily alias
        "@weekly",             # Weekly alias
        "0 12 * * 1-5",        # Weekdays at noon
        "* * * * *"            # Every minute
    ]

    print("Testing cron expressions:")
    for expr in test_expressions:
        is_valid, error = parser.validate(expr)
        if is_valid:
            human_desc = parser.get_human_readable(expr)
            next_run = parser.get_next_run_time(expr)
            print(f"  {expr:<20} -> {human_desc:<35} (next: {next_run.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print(f"  {expr:<20} -> INVALID: {error}")

    # Test getting next N run times
    print(f"\nNext 3 run times for '0 9 * * *' (daily at 9 AM):")
    next_times = parser.get_next_n_run_times("0 9 * * *", 3)
    for i, dt in enumerate(next_times, 1):
        print(f"  {i}. {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # Test invalid expression
    print(f"\nTesting invalid expression:")
    is_valid, error = parser.validate("invalid")
    print(f"  'invalid' -> Valid: {is_valid}, Error: {error}")