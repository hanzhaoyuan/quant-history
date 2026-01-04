"""Edge case and boundary tests"""
import pytest
import pandas as pd
from providers import history_n

# Test all available providers
PROVIDERS = ['python', 'numpy', 'pandas']

try:
    from _cpp_history_core import HistoryProvider
    PROVIDERS.insert(0, 'cpp_pybind')
except ImportError:
    pass

try:
    from providers._cpp_cython import CythonHistoryProvider
    PROVIDERS.append('cpp_cython')
except ImportError:
    pass


class TestInvalidInputs:
    """Test handling of invalid inputs"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_invalid_frequency(self, provider):
        """Test that invalid frequency raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported frequency"):
            history_n('000001.SH', '5m', 100, provider=provider)

        with pytest.raises(ValueError, match="Unsupported frequency"):
            history_n('000001.SH', '1d', 100, provider=provider)

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_invalid_end_time_format(self, provider):
        """Test that invalid end_time format raises ValueError"""
        with pytest.raises(ValueError, match="Can't parse string as time"):
            history_n('000001.SH', '1m', 100,
                     end_time='2020-13-01 10:00:00',  # Invalid month
                     provider=provider)

        with pytest.raises(ValueError, match="Can't parse string as time"):
            history_n('000001.SH', '1m', 100,
                     end_time='2020-10-40 15:30:00',  # Invalid day
                     provider=provider)

        with pytest.raises(ValueError, match="Can't parse string as time"):
            history_n('000001.SH', '1m', 100,
                     end_time='invalid-date',
                     provider=provider)

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_invalid_symbol_returns_empty(self, provider):
        """Test that invalid symbol returns empty result"""
        result_list = history_n('INVALID_SYMBOL', '1m', 100,
                                provider=provider, df=False)
        assert len(result_list) == 0

        result_df = history_n('INVALID_SYMBOL', '1m', 100,
                             provider=provider, df=True)
        assert len(result_df) == 0
        assert isinstance(result_df, pd.DataFrame)


class TestBoundaryValues:
    """Test boundary values and edge cases"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_count_exceeds_33000(self, provider):
        """Test that count > 33000 is capped at 33000"""
        result = history_n('000001.SH', '1m', 50000, provider=provider, df=True)

        # Should be capped at 33000 or available data, whichever is smaller
        assert len(result) <= 33000

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_count_zero(self, provider):
        """Test that count=0 returns empty"""
        result = history_n('000001.SH', '1m', 0, provider=provider, df=False)
        assert len(result) == 0

        result_df = history_n('000001.SH', '1m', 0, provider=provider, df=True)
        assert len(result_df) == 0

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_count_negative(self, provider):
        """Test that negative count returns empty"""
        result = history_n('000001.SH', '1m', -10, provider=provider, df=False)
        assert len(result) == 0

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_end_time_before_data(self, provider):
        """Test that end_time before all data returns empty"""
        result = history_n('000001.SH', '1m', 100,
                          end_time='2020-01-01 10:00:00',
                          provider=provider, df=False)
        assert len(result) == 0

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_count_exceeds_available(self, provider):
        """Test that count exceeding available data returns all available"""
        # Total data: 100 days * 240 bars = 24000 bars
        # Request more than total
        result = history_n('000001.SH', '1m', 30000,
                          end_time='2024-06-30 15:00:00',
                          provider=provider, df=True)

        # Should return all available data (approx 24000)
        assert len(result) <= 24000


class TestFrequencyAliases:
    """Test frequency parameter aliases"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_60s_and_1m_equivalent(self, provider):
        """Test that '60s' and '1m' produce same results"""
        result_60s = history_n('000001.SH', '60s', 100,
                               end_time='2024-01-15 10:00:00',
                               provider=provider, df=True)

        result_1m = history_n('000001.SH', '1m', 100,
                              end_time='2024-01-15 10:00:00',
                              provider=provider, df=True)

        pd.testing.assert_frame_equal(result_60s, result_1m)


class TestFieldParsing:
    """Test field parameter parsing"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_fields_with_whitespace(self, provider):
        """Test that fields with whitespace are handled correctly"""
        result = history_n('000001.SH', '1m', 10,
                          fields=' open , close , high ',
                          provider=provider, df=True)

        assert 'open' in result.columns
        assert 'close' in result.columns
        assert 'high' in result.columns

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_invalid_fields_ignored(self, provider):
        """Test that invalid field names are ignored"""
        result = history_n('000001.SH', '1m', 10,
                          fields='open,invalid_field,close',
                          provider=provider, df=True)

        # Should have valid fields
        assert 'open' in result.columns
        assert 'close' in result.columns

        # Should not have invalid field
        assert 'invalid_field' not in result.columns

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_empty_fields_returns_all(self, provider):
        """Test that fields=None returns all fields"""
        result = history_n('000001.SH', '1m', 10,
                          fields=None,
                          provider=provider, df=True)

        expected_columns = {'symbol', 'open', 'high', 'low', 'close', 'eob'}
        assert set(result.columns) == expected_columns


class TestEndTimeFormats:
    """Test different end_time formats"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_single_digit_datetime(self, provider):
        """Test that single-digit datetime components work"""
        # Test format: 2017-7-30 20:0:20 (from requirements)
        result = history_n('000001.SH', '1m', 10,
                          end_time='2024-1-5 9:35:0',
                          provider=provider, df=True)

        # Should not raise exception
        assert len(result) > 0


class TestReservedParameters:
    """Test that reserved parameters are accepted but ignored"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_reserved_params_accepted(self, provider):
        """Test that reserved parameters don't cause errors"""
        result = history_n('000001.SH', '1m', 10,
                          skip_suspended=False,
                          fill_missing='ffill',
                          adjust='hfq',
                          adjust_end_time='2024-01-01',
                          provider=provider, df=False)

        # Should work without error (parameters are ignored)
        assert len(result) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
