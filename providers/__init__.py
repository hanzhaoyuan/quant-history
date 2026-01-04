"""
Unified history_n interface for quant-history benchmark

This module provides a unified entry point for querying minute-bar data
using different implementations:
- cpp_pybind: C++ backend with pybind11 bindings
- cpp_cython: C++ backend with Cython bindings
- python: Pure Python baseline
- numpy: NumPy columnar baseline
- pandas: pandas DataFrame baseline
"""

from typing import Union, Optional, List, Dict
from datetime import datetime
import pandas as pd

# Import individual providers
from . import cpp_pybind_provider
from . import python_provider
from . import numpy_provider
from . import pandas_provider

__all__ = ['history_n']

# Version info
__version__ = '0.1.0'


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
    df: bool = False,
    provider: str = 'cpp_pybind'
) -> Union[List[Dict], pd.DataFrame]:
    """
    Query history_n minute bar data

    This is the unified entry point for all provider implementations.

    Args:
        symbol: Symbol code (single symbol only, e.g., '000001.SH')
        frequency: '60s' or '1m' (only these are supported in V1)
        count: Number of bars to return (max 33000)
        end_time: End time (None=current time, str in format '%Y-%m-%d %H:%M:%S', or datetime)
        fields: Comma-separated field names to include (None=all fields)
                Valid fields: symbol, open, high, low, close, eob
        skip_suspended: (V1: ignored, reserved for future)
        fill_missing: (V1: ignored, reserved for future)
        adjust: (V1: ignored, reserved for future, default 'none')
        adjust_end_time: (V1: ignored, reserved for future)
        df: Return pandas DataFrame (True) or list of dicts (False)
        provider: Which implementation to use:
                  - 'cpp_pybind': C++ + pybind11 (default, recommended)
                  - 'cpp_cython': C++ + Cython
                  - 'python': Pure Python baseline
                  - 'numpy': NumPy columnar baseline
                  - 'pandas': pandas DataFrame baseline

    Returns:
        If df=False: list[dict] where each dict is a bar with keys:
                     symbol, open, high, low, close, eob (datetime in UTC+8)
        If df=True:  pandas.DataFrame with columns as above

    Raises:
        ValueError: If frequency is not supported or end_time format is invalid
        ImportError: If C++ backend is not built (for cpp_pybind/cpp_cython)

    Examples:
        >>> # Get latest 100 bars
        >>> data = history_n('000001.SH', '1m', 100)

        >>> # Get data up to specific time
        >>> data = history_n('000001.SH', '1m', 1000,
        ...                  end_time='2024-01-15 14:30:00')

        >>> # Get only specific fields as DataFrame
        >>> df = history_n('000001.SH', '1m', 500,
        ...                fields='symbol,open,close,eob',
        ...                df=True)

        >>> # Use Python baseline for comparison
        >>> data = history_n('000001.SH', '1m', 100, provider='python')

    Notes:
        - Only '60s' or '1m' frequency is supported in V1
        - count is capped at 33000
        - Invalid symbols return empty result (no exception)
        - Invalid end_time raises ValueError with descriptive message
        - All timestamps are in UTC+8 timezone
        - Data covers 100 trading days (approx 24,000 bars per symbol)
        - Trading days: Mon-Fri, no holidays (simplified for benchmark)
        - Sessions: 09:30-11:30 (morning), 13:00-15:00 (afternoon)
    """
    provider_map = {
        'cpp_pybind': cpp_pybind_provider,
        'python': python_provider,
        'numpy': numpy_provider,
        'pandas': pandas_provider,
    }

    if provider not in provider_map:
        # Check if cpp_cython is requested
        if provider == 'cpp_cython':
            try:
                from . import cpp_cython_provider
                impl = cpp_cython_provider
            except ImportError:
                raise ImportError(
                    "Cython provider not available. "
                    "Please build the Cython extension first."
                )
        else:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Valid providers: cpp_pybind, cpp_cython, python, numpy, pandas"
            )
    else:
        impl = provider_map[provider]

    return impl.history_n(
        symbol=symbol,
        frequency=frequency,
        count=count,
        end_time=end_time,
        fields=fields,
        skip_suspended=skip_suspended,
        fill_missing=fill_missing,
        adjust=adjust,
        adjust_end_time=adjust_end_time,
        df=df
    )
