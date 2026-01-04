"""NumPy-based columnar baseline provider"""
from typing import Union, Optional, List, Dict
from datetime import datetime, timedelta
import hashlib
import numpy as np
import pandas as pd

from .utils import parse_end_time, timestamp_to_datetime, validate_frequency, parse_fields, TZ_UTC8


class NumpyHistoryProvider:
    """NumPy columnar implementation of history_n"""

    def __init__(self):
        self.cache = {}  # {symbol: dict of arrays}

    def _get_seed_from_symbol(self, symbol: str) -> int:
        """Get deterministic seed from symbol using MD5"""
        hash_bytes = hashlib.md5(symbol.encode()).digest()
        return int.from_bytes(hash_bytes[:4], 'little')

    def _lcg_random_array(self, seed: int, size: int, min_val: float, max_val: float) -> np.ndarray:
        """Generate array of random numbers using LCG"""
        result = np.empty(size, dtype=np.float64)
        seed_state = seed

        for i in range(size):
            seed_state = (seed_state * 1103515245 + 12345) & 0xFFFFFFFF
            random_val = ((seed_state // 65536) % 32768)
            normalized = random_val / 32768.0
            result[i] = min_val + normalized * (max_val - min_val)

        return result

    def _is_trading_day(self, date: datetime) -> bool:
        """Check if date is a trading day (Mon-Fri)"""
        return date.weekday() < 5  # 0=Mon, ..., 4=Fri

    def _generate_data(self, symbol: str) -> Dict[str, np.ndarray]:
        """Generate 100 trading days of minute bars (columnar)"""
        seed = self._get_seed_from_symbol(symbol)

        # Collect all eob timestamps first
        eob_timestamps = []
        current_date = datetime(2024, 1, 2, tzinfo=TZ_UTC8)
        trading_days = 0

        while trading_days < 100:
            if self._is_trading_day(current_date):
                # Morning session: 09:30 - 11:30
                morning_start = current_date.replace(hour=9, minute=30, second=0, microsecond=0)
                for i in range(120):
                    eob = morning_start + timedelta(minutes=i+1)
                    eob_timestamps.append(int(eob.timestamp()))

                # Afternoon session: 13:00 - 15:00
                afternoon_start = current_date.replace(hour=13, minute=0, second=0, microsecond=0)
                for i in range(120):
                    eob = afternoon_start + timedelta(minutes=i+1)
                    eob_timestamps.append(int(eob.timestamp()))

                trading_days += 1

            current_date += timedelta(days=1)

        total_bars = len(eob_timestamps)

        # Generate OHLC data using LCG (matching C++/Python logic)
        # We need to generate sequentially to match the seed progression

        symbols = np.array([symbol] * total_bars, dtype=object)
        opens = np.empty(total_bars, dtype=np.float64)
        closes = np.empty(total_bars, dtype=np.float64)
        highs = np.empty(total_bars, dtype=np.float64)
        lows = np.empty(total_bars, dtype=np.float64)

        base_price = 100.0
        seed_state = seed

        for i in range(total_bars):
            # Generate open
            seed_state = (seed_state * 1103515245 + 12345) & 0xFFFFFFFF
            random_val = ((seed_state // 65536) % 32768)
            normalized = random_val / 32768.0
            open_price = base_price + (-10.0 + normalized * 20.0)
            opens[i] = open_price

            # Generate close
            seed_state = (seed_state * 1103515245 + 12345) & 0xFFFFFFFF
            random_val = ((seed_state // 65536) % 32768)
            normalized = random_val / 32768.0
            close_price = base_price + (-10.0 + normalized * 20.0)
            closes[i] = close_price

            min_oc = min(open_price, close_price)
            max_oc = max(open_price, close_price)

            # Generate low
            seed_state = (seed_state * 1103515245 + 12345) & 0xFFFFFFFF
            random_val = ((seed_state // 65536) % 32768)
            normalized = random_val / 32768.0
            low = min_oc - (normalized * 2.0)
            lows[i] = low

            # Generate high
            seed_state = (seed_state * 1103515245 + 12345) & 0xFFFFFFFF
            random_val = ((seed_state // 65536) % 32768)
            normalized = random_val / 32768.0
            high = max_oc + (normalized * 2.0)
            highs[i] = high

        eob_ts_array = np.array(eob_timestamps, dtype=np.int64)

        return {
            'symbol': symbols,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'eob_ts': eob_ts_array
        }

    def query(self, symbol: str, count: int, end_time_ts: int, fields: list) -> Dict[str, np.ndarray]:
        """Query data (internal method, returns columnar arrays)"""
        # Initialize cache if needed
        if symbol not in self.cache:
            self.cache[symbol] = self._generate_data(symbol)

        data = self.cache[symbol]

        if len(data['eob_ts']) == 0:
            return {k: np.array([], dtype=v.dtype) for k, v in data.items()}

        # Use NumPy searchsorted for binary search
        idx = np.searchsorted(data['eob_ts'], end_time_ts, side='right')

        if idx == 0:
            # end_time is before all data
            return {k: np.array([], dtype=v.dtype) for k, v in data.items()}

        # Calculate start position
        start_idx = max(0, idx - count)

        # Slice arrays
        result = {k: v[start_idx:idx] for k, v in data.items()}

        # Apply field filtering if specified (handled in wrapper)
        return result


# Singleton instance
_provider_instance = None


def get_provider():
    """Get or create singleton provider instance"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = NumpyHistoryProvider()
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
    Query history_n data using NumPy columnar implementation

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

    # Call provider
    provider = get_provider()
    result = provider.query(symbol, count, end_time_ts, field_list)

    # Check if empty
    if len(result['eob_ts']) == 0:
        return pd.DataFrame() if df else []

    # Convert eob_ts to datetime
    eob_datetimes = [timestamp_to_datetime(ts) for ts in result['eob_ts']]

    # Build output based on df flag
    if df:
        # Return DataFrame (Path B: arrays -> DataFrame)
        data = {
            'symbol': result['symbol'],
            'open': result['open'],
            'high': result['high'],
            'low': result['low'],
            'close': result['close'],
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
        size = len(result['eob_ts'])
        for i in range(size):
            bar = {
                'symbol': result['symbol'][i],
                'open': result['open'][i],
                'high': result['high'][i],
                'low': result['low'][i],
                'close': result['close'][i],
                'eob': eob_datetimes[i]
            }

            # Apply field filtering if specified
            if field_list:
                # Ensure symbol and eob are always included
                if 'symbol' not in field_list:
                    field_list = ['symbol'] + field_list
                if 'eob' not in field_list:
                    field_list = field_list + ['eob']

                bar = {k: v for k, v in bar.items() if k in field_list}

            bars.append(bar)

        return bars
