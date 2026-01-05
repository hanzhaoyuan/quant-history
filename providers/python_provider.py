"""Pure Python baseline provider (reference implementation)"""
from typing import Union, Optional, List, Dict
from datetime import datetime, timedelta
import hashlib
import pandas as pd

from .utils import parse_end_time, timestamp_to_datetime, validate_frequency, parse_fields, TZ_UTC8


class PythonHistoryProvider:
    """Pure Python implementation of history_n"""

    def __init__(self):
        self.cache = {}  # {symbol: list[dict]}

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

    def _generate_data(self, symbol: str) -> List[Dict]:
        """Generate 100 trading days of minute bars"""
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

        return bars

    def query(self, symbol: str, count: int, end_time_ts: int, fields: list) -> List[Dict]:
        """Query data (internal method)"""
        # Initialize cache if needed
        if symbol not in self.cache:
            self.cache[symbol] = self._generate_data(symbol)

        bars = self.cache[symbol]

        if not bars:
            return []

        # Convert end_time_ts to datetime for comparison
        end_time_dt = timestamp_to_datetime(end_time_ts)

        # Linear search for bars with eob <= end_time_dt
        filtered_bars = [bar for bar in bars if bar['eob'] <= end_time_dt]

        if not filtered_bars:
            return []

        # Take last 'count' bars
        result = filtered_bars[-count:]

        # Apply field filtering if specified
        if fields:
            # Ensure symbol and eob are always included
            if 'symbol' not in fields:
                fields = ['symbol'] + fields
            if 'eob' not in fields:
                fields = fields + ['eob']

            result = [{k: bar[k] for k in fields if k in bar} for bar in result]

        return result


# Singleton instance
_provider_instance = None


def get_provider():
    """Get or create singleton provider instance"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = PythonHistoryProvider()
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
    Query history_n data using pure Python implementation

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
    if not result:
        return pd.DataFrame() if df else []

    # Build output based on df flag
    if df:
        return pd.DataFrame(result)
    else:
        return result
