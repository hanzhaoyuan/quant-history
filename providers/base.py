"""Base provider interface (optional, for documentation)"""
from abc import ABC, abstractmethod
from typing import Union, Optional, List, Dict
from datetime import datetime
import pandas as pd


class BaseProvider(ABC):
    """Base class for history_n providers"""

    @abstractmethod
    def history_n(
        self,
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
        Query history_n data

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
        pass
