"""Cython-based provider using C++ backend"""
from typing import Union, Optional, List, Dict
from datetime import datetime
import pandas as pd
import numpy as np

try:
    from providers._cpp_cython import CythonHistoryProvider as _CythonProvider
except ImportError:
    _CythonProvider = None  # Will fail at runtime if not built

from .utils import parse_end_time, timestamp_to_datetime, validate_frequency, parse_fields


# Singleton instance
_provider_instance = None


def get_provider():
    """Get or create singleton provider instance"""
    global _provider_instance
    if _provider_instance is None:
        if _CythonProvider is None:
            raise ImportError(
                "Cython backend not available. "
                "Please build the project first using: python setup.py build_ext --inplace"
            )
        _provider_instance = _CythonProvider()
    return _provider_instance


def history_n(
    symbol: str,
    frequency: str,
    count: int,
    end_time: Union[None, str, datetime] = None,
    fields: Optional[str] = None,
    skip_suspended: bool = True,
    fill_missing: Optional[str] = None,
    adjust: str = 'none',
    adjust_end_time: str = '',
    df: bool = False
) -> Union[List[Dict], pd.DataFrame]:
    """
    Query history_n data using C++ backend (Cython)

    Args:
        symbol: Symbol code (single symbol only)
        frequency: '60s' or '1m' (only)
        count: Number of bars to return (max 33000)
        end_time: End time (None=now, str, or datetime)
        fields: Comma-separated field names (None=all)
        skip_suspended: (V1: ignored)
        fill_missing: (V1: ignored)
        adjust: (V1: ignored)
        adjust_end_time: (V1: ignored)
        df: Return DataFrame (True) or list of dicts (False)

    Returns:
        list[dict] if df=False, else pd.DataFrame

    Raises:
        ValueError: If frequency is not supported or end_time is invalid
    """
    # Validate parameters
    validate_frequency(frequency)

    if count <= 0:
        return pd.DataFrame() if df else []

    # Cap count at 33000
    if count > 33000:
        count = 33000

    # Parse end_time to timestamp
    try:
        end_time_ts = parse_end_time(end_time)
    except ValueError as e:
        raise ValueError(str(e))

    # Parse fields
    field_list = parse_fields(fields)

    # Call Cython backend
    provider = get_provider()
    result = provider.query(symbol, count, end_time_ts, field_list)

    # Check if empty
    if len(result['eob_timestamps']) == 0:
        return pd.DataFrame() if df else []

    # Convert eob_timestamps to datetime
    eob_datetimes = [timestamp_to_datetime(ts) for ts in result['eob_timestamps']]

    # Build output based on df flag
    if df:
        # Return DataFrame (Path B: arrays -> DataFrame)
        data = {
            'symbol': result['symbols'],
            'open': result['opens'],
            'high': result['highs'],
            'low': result['lows'],
            'close': result['closes'],
            'eob': eob_datetimes
        }

        # Apply field filtering if specified
        if field_list:
            # Ensure symbol and eob are always included
            if 'symbol' not in field_list:
                field_list.insert(0, 'symbol')
            if 'eob' not in field_list:
                field_list.append('eob')

            # Filter columns
            data = {k: v for k, v in data.items() if k in field_list}

            # Reorder columns according to field_list
            column_order = [f for f in field_list if f in data]
            return pd.DataFrame(data)[column_order]

        return pd.DataFrame(data)
    else:
        # Return list of dicts (Path C: list[dict])
        bars = []
        size = len(result['eob_timestamps'])
        for i in range(size):
            bar = {
                'symbol': result['symbols'][i],
                'open': result['opens'][i],
                'high': result['highs'][i],
                'low': result['lows'][i],
                'close': result['closes'][i],
                'eob': eob_datetimes[i]
            }

            # Apply field filtering if specified
            if field_list:
                # Ensure symbol and eob are always included
                if 'symbol' not in field_list:
                    field_list.insert(0, 'symbol')
                if 'eob' not in field_list:
                    field_list.append('eob')

                bar = {k: v for k, v in bar.items() if k in field_list}

            bars.append(bar)

        return bars
