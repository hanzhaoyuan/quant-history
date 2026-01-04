"""Utility functions for quant-history benchmark"""
from datetime import datetime, timezone, timedelta
from typing import Union, Optional

# UTC+8 timezone
TZ_UTC8 = timezone(timedelta(hours=8))

def parse_end_time(end_time: Union[None, str, datetime]) -> int:
    """
    Parse end_time to Unix timestamp (seconds)

    Args:
        end_time: None (current time), str (format: %Y-%m-%d %H:%M:%S), or datetime

    Returns:
        Unix timestamp in seconds (UTC+8)

    Raises:
        ValueError: If string cannot be parsed
    """
    if end_time is None:
        # Use current time in UTC+8
        return int(datetime.now(TZ_UTC8).timestamp())

    if isinstance(end_time, str):
        # Parse string format: %Y-%m-%d %H:%M:%S
        # Allow single-digit month/day/hour/minute/second
        try:
            # Try parsing with datetime
            dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Try more flexible parsing for single-digit values
            try:
                parts = end_time.split()
                if len(parts) != 2:
                    raise ValueError()

                date_parts = parts[0].split('-')
                time_parts = parts[1].split(':')

                if len(date_parts) != 3 or len(time_parts) != 3:
                    raise ValueError()

                year = int(date_parts[0])
                month = int(date_parts[1])
                day = int(date_parts[2])
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                second = int(time_parts[2])

                dt = datetime(year, month, day, hour, minute, second)
            except (ValueError, IndexError):
                raise ValueError(f"Can't parse string as time: {end_time}")

        # Assume the datetime is in UTC+8
        dt = dt.replace(tzinfo=TZ_UTC8)
        return int(dt.timestamp())

    if isinstance(end_time, datetime):
        # If datetime is naive, assume UTC+8
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=TZ_UTC8)
        return int(end_time.timestamp())

    raise ValueError(f"end_time must be None, str, or datetime, got {type(end_time)}")


def timestamp_to_datetime(ts: int) -> datetime:
    """
    Convert Unix timestamp to datetime (UTC+8)

    Args:
        ts: Unix timestamp in seconds

    Returns:
        datetime object in UTC+8
    """
    return datetime.fromtimestamp(ts, tz=TZ_UTC8)


def validate_frequency(frequency: str) -> None:
    """
    Validate frequency parameter

    Args:
        frequency: Frequency string

    Raises:
        ValueError: If frequency is not supported
    """
    valid_frequencies = ['60s', '1m']
    if frequency not in valid_frequencies:
        raise ValueError(
            f"Unsupported frequency: {frequency}. "
            f"Only {valid_frequencies} are supported in V1."
        )


def parse_fields(fields: Optional[str]) -> list:
    """
    Parse fields parameter

    Args:
        fields: Comma-separated field names, or None

    Returns:
        List of field names (empty if None)
    """
    if fields is None:
        return []

    # Split by comma and strip whitespace
    field_list = [f.strip() for f in fields.split(',')]
    return [f for f in field_list if f]  # Remove empty strings
