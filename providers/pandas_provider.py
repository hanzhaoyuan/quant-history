"""pandas-based provider using DataFrame for storage"""
from typing import Union, Optional, List, Dict
from datetime import datetime, timedelta
import hashlib
import pandas as pd
import numpy as np

from .utils import parse_end_time, timestamp_to_datetime, validate_frequency, parse_fields, TZ_UTC8


class PandasHistoryProvider:
    """pandas DataFrame-based implementation of history_n"""

    def __init__(self):
        self.cache = {}  # {symbol: pd.DataFrame}

    def _get_seed_from_symbol(self, symbol: str) -> int:
        """Get deterministic seed from symbol using simple hash (matches C++)"""
        hash_val = 0
        for c in symbol:
            hash_val = (hash_val * 31 + ord(c)) & 0xFFFFFFFF
        return hash_val

    def _lcg_random(self, seed_state: list, min_val: float, max_val: float) -> float:
        """Linear Congruential Generator (same as C++)"""
        seed_state[0] = (seed_state[0] * 1103515245 + 12345) & 0xFFFFFFFF
        random_val = ((seed_state[0] // 65536) % 32768)
        normalized = random_val / 32768.0
        return min_val + normalized * (max_val - min_val)

    def _is_trading_day(self, date: datetime) -> bool:
        """Check if date is a trading day (Mon-Fri)"""
        return date.weekday() < 5  # 0=Mon, ..., 4=Fri

    def _generate_trading_day(self, symbol: str, date: datetime, seed_state: list) -> List[Dict]:
        """Generate 240 bars for a single trading day"""
        bars = []

        # Morning session: 09:30 - 11:30 (120 bars)
        morning_start = date.replace(hour=9, minute=30, second=0, microsecond=0)
        for i in range(120):
            eob = morning_start + timedelta(minutes=i+1)
            bar = self._generate_bar(symbol, eob, seed_state)
            bars.append(bar)

        # Afternoon session: 13:00 - 15:00 (120 bars)
        afternoon_start = date.replace(hour=13, minute=0, second=0, microsecond=0)
        for i in range(120):
            eob = afternoon_start + timedelta(minutes=i+1)
            bar = self._generate_bar(symbol, eob, seed_state)
            bars.append(bar)

        return bars

    def _generate_bar(self, symbol: str, eob: datetime, seed_state: list) -> Dict:
        """Generate a single bar"""
        base_price = 100.0

        open_price = base_price + self._lcg_random(seed_state, -10.0, 10.0)
        close_price = base_price + self._lcg_random(seed_state, -10.0, 10.0)

        min_oc = min(open_price, close_price)
        max_oc = max(open_price, close_price)

        low = min_oc - self._lcg_random(seed_state, 0.0, 2.0)
        high = max_oc + self._lcg_random(seed_state, 0.0, 2.0)

        return {
            'symbol': symbol,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'eob': eob
        }

    def _generate_data(self, symbol: str) -> pd.DataFrame:
        """Generate 100 trading days of minute bars as DataFrame"""
        seed = self._get_seed_from_symbol(symbol)
        seed_state = [seed]

        bars = []

        # Start from 2024-01-02 (Tuesday)
        current_date = datetime(2024, 1, 2, tzinfo=TZ_UTC8)
        trading_days = 0

        while trading_days < 100:
            if self._is_trading_day(current_date):
                day_bars = self._generate_trading_day(symbol, current_date, seed_state)
                bars.extend(day_bars)
                trading_days += 1

            current_date += timedelta(days=1)

        # Create DataFrame directly
        df = pd.DataFrame(bars)

        # Ensure eob is datetime and sorted
        df = df.sort_values('eob').reset_index(drop=True)

        return df

    def query(self, symbol: str, count: int, end_time_dt: datetime, fields: list) -> pd.DataFrame:
        """Query data (internal method, returns DataFrame)"""
        # Initialize cache if needed
        if symbol not in self.cache:
            self.cache[symbol] = self._generate_data(symbol)

        df = self.cache[symbol]

        if df.empty:
            return pd.DataFrame()

        # Filter using pandas boolean indexing
        filtered_df = df[df['eob'] <= end_time_dt]

        if filtered_df.empty:
            return pd.DataFrame()

        # Take last 'count' rows
        result = filtered_df.tail(count).reset_index(drop=True)

        # Apply field filtering if specified
        if fields:
            # Ensure symbol and eob are always included
            if 'symbol' not in fields:
                fields = ['symbol'] + fields
            if 'eob' not in fields:
                fields = fields + ['eob']

            # Filter columns (only keep fields that exist)
            available_fields = [f for f in fields if f in result.columns]
            result = result[available_fields]

        return result


# Singleton instance
_provider_instance = None


def get_provider():
    """Get or create singleton provider instance"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = PandasHistoryProvider()
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
    Query history_n data using pandas DataFrame implementation

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

    # Parse end_time to timestamp then to datetime
    try:
        end_time_ts = parse_end_time(end_time)
        end_time_dt = timestamp_to_datetime(end_time_ts)
    except ValueError as e:
        raise ValueError(str(e))

    # Parse fields
    field_list = parse_fields(fields)

    # Call provider
    provider = get_provider()
    result_df = provider.query(symbol, count, end_time_dt, field_list)

    # Check if empty
    if result_df.empty:
        return pd.DataFrame() if df else []

    # Build output based on df flag
    if df:
        return result_df
    else:
        # Convert DataFrame to list of dicts
        return result_df.to_dict('records')
