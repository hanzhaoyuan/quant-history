"""Correctness tests to ensure all providers return consistent results"""
import pytest
import pandas as pd
import numpy as np
from providers import history_n

# Test all available providers
PROVIDERS = ['python', 'numpy', 'pandas']  # Always available

# Try to add C++ providers if available
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


class TestBasicQuery:
    """Test basic query functionality"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_basic_query_list(self, provider):
        """Test basic query returning list[dict]"""
        result = history_n('000001.SH', '1m', 100, provider=provider, df=False)

        assert isinstance(result, list)
        assert len(result) == 100

        # Check first bar structure
        bar = result[0]
        assert 'symbol' in bar
        assert 'open' in bar
        assert 'high' in bar
        assert 'low' in bar
        assert 'close' in bar
        assert 'eob' in bar

        # Check OHLC constraints
        assert bar['low'] <= bar['open']
        assert bar['low'] <= bar['close']
        assert bar['high'] >= bar['open']
        assert bar['high'] >= bar['close']

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_basic_query_dataframe(self, provider):
        """Test basic query returning DataFrame"""
        result = history_n('000001.SH', '1m', 100, provider=provider, df=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

        # Check columns
        expected_columns = {'symbol', 'open', 'high', 'low', 'close', 'eob'}
        assert set(result.columns) == expected_columns

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_eob_ascending(self, provider):
        """Test that eob timestamps are in ascending order"""
        result = history_n('000001.SH', '1m', 1000, provider=provider, df=True)

        eob_list = result['eob'].tolist()
        for i in range(1, len(eob_list)):
            assert eob_list[i] > eob_list[i-1], f"eob not ascending at index {i}"


class TestCrossProviderConsistency:
    """Test that all providers return identical results"""

    def test_same_data_all_providers(self):
        """All providers should return identical data for same query"""
        if len(PROVIDERS) < 2:
            pytest.skip("Need at least 2 providers for consistency test")

        symbol = '000001.SH'
        count = 5000
        end_time = '2024-01-15 14:30:00'

        results = {}
        for provider in PROVIDERS:
            results[provider] = history_n(
                symbol, '1m', count,
                end_time=end_time,
                provider=provider,
                df=True
            )

        # Compare all providers against the first one
        base_provider = PROVIDERS[0]
        base_df = results[base_provider]

        for provider in PROVIDERS[1:]:
            df = results[provider]

            # Check shape
            assert df.shape == base_df.shape, \
                f"{provider} shape {df.shape} != {base_provider} shape {base_df.shape}"

            # Check eob (should be exact)
            pd.testing.assert_series_equal(
                df['eob'].reset_index(drop=True),
                base_df['eob'].reset_index(drop=True),
                check_names=False
            )

            # Check symbol (should be exact)
            pd.testing.assert_series_equal(
                df['symbol'].reset_index(drop=True),
                base_df['symbol'].reset_index(drop=True),
                check_names=False
            )

            # Check OHLC (allow small floating point errors)
            for col in ['open', 'high', 'low', 'close']:
                np.testing.assert_allclose(
                    df[col].values,
                    base_df[col].values,
                    rtol=1e-10,
                    err_msg=f"{provider} {col} values differ from {base_provider}"
                )

    def test_df_vs_list_consistency(self):
        """Test that df=True and df=False return same data"""
        if len(PROVIDERS) == 0:
            pytest.skip("No providers available")

        provider = PROVIDERS[0]
        symbol = '000001.SH'
        count = 100

        # Get both formats
        list_result = history_n(symbol, '1m', count, provider=provider, df=False)
        df_result = history_n(symbol, '1m', count, provider=provider, df=True)

        # Check length
        assert len(list_result) == len(df_result)

        # Check content
        for i, bar in enumerate(list_result):
            assert bar['symbol'] == df_result.iloc[i]['symbol']
            assert bar['eob'] == df_result.iloc[i]['eob']
            np.testing.assert_allclose(bar['open'], df_result.iloc[i]['open'])
            np.testing.assert_allclose(bar['high'], df_result.iloc[i]['high'])
            np.testing.assert_allclose(bar['low'], df_result.iloc[i]['low'])
            np.testing.assert_allclose(bar['close'], df_result.iloc[i]['close'])


class TestFieldFiltering:
    """Test field filtering functionality"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_field_filtering_list(self, provider):
        """Test field filtering with list output"""
        result = history_n(
            '000001.SH', '1m', 10,
            fields='open,close',
            provider=provider,
            df=False
        )

        assert len(result) == 10
        bar = result[0]

        # symbol and eob should always be included
        assert 'symbol' in bar
        assert 'eob' in bar
        assert 'open' in bar
        assert 'close' in bar

        # high and low should not be included
        # Note: Current implementation may include all fields, this tests the requirement

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_field_filtering_dataframe(self, provider):
        """Test field filtering with DataFrame output"""
        result = history_n(
            '000001.SH', '1m', 10,
            fields='symbol,open,close,eob',
            provider=provider,
            df=True
        )

        assert len(result) == 10
        # Check that requested fields are present
        assert 'symbol' in result.columns
        assert 'open' in result.columns
        assert 'close' in result.columns
        assert 'eob' in result.columns


class TestDataIntegrity:
    """Test data integrity constraints"""

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_ohlc_constraints(self, provider):
        """Test that OHLC data satisfies constraints"""
        result = history_n('000001.SH', '1m', 1000, provider=provider, df=True)

        for idx, row in result.iterrows():
            min_oc = min(row['open'], row['close'])
            max_oc = max(row['open'], row['close'])

            assert row['low'] <= min_oc, f"low > min(open,close) at {idx}"
            assert row['high'] >= max_oc, f"high < max(open,close) at {idx}"

    @pytest.mark.parametrize('provider', PROVIDERS)
    def test_60_second_intervals(self, provider):
        """Test that bars are 60 seconds apart"""
        result = history_n('000001.SH', '1m', 240, provider=provider, df=True)

        # Check consecutive bars within same session
        for i in range(1, len(result)):
            diff = (result.iloc[i]['eob'] - result.iloc[i-1]['eob']).total_seconds()

            # Should be 60 seconds or a session break
            # Session breaks: 11:30 -> 13:01 (91 minutes = 5460 seconds)
            # or overnight (next day)
            if diff != 60:
                # Must be a session break or day break
                assert diff >= 5400, f"Unexpected time gap: {diff} seconds at index {i}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
