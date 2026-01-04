"""Quick test to verify pandas provider consistency"""
from providers import history_n
import pandas as pd
import numpy as np

print("Testing pandas provider consistency...")
print("=" * 60)

# Test configuration
symbol = '000001.SH'
count = 100
end_time = '2024-01-15 14:30:00'

# Get data from all baseline providers (always available)
print("\n1. Fetching data from all baseline providers...")
result_python = history_n(symbol, '1m', count, end_time=end_time, provider='python', df=True)
result_numpy = history_n(symbol, '1m', count, end_time=end_time, provider='numpy', df=True)
result_pandas = history_n(symbol, '1m', count, end_time=end_time, provider='pandas', df=True)

print(f"   Python provider: {len(result_python)} rows")
print(f"   NumPy provider:  {len(result_numpy)} rows")
print(f"   pandas provider: {len(result_pandas)} rows")

# Check shape consistency
print("\n2. Checking shape consistency...")
assert result_python.shape == result_numpy.shape == result_pandas.shape, "Shape mismatch!"
print("   ✓ All providers return same shape")

# Check eob consistency
print("\n3. Checking eob timestamps...")
pd.testing.assert_series_equal(
    result_python['eob'].reset_index(drop=True),
    result_pandas['eob'].reset_index(drop=True),
    check_names=False
)
print("   ✓ Python vs pandas: eob timestamps match")

pd.testing.assert_series_equal(
    result_numpy['eob'].reset_index(drop=True),
    result_pandas['eob'].reset_index(drop=True),
    check_names=False
)
print("   ✓ NumPy vs pandas: eob timestamps match")

# Check OHLC consistency
print("\n4. Checking OHLC values...")
for col in ['open', 'high', 'low', 'close']:
    np.testing.assert_allclose(
        result_python[col].values,
        result_pandas[col].values,
        rtol=1e-10,
        err_msg=f"Python vs pandas: {col} mismatch"
    )
    np.testing.assert_allclose(
        result_numpy[col].values,
        result_pandas[col].values,
        rtol=1e-10,
        err_msg=f"NumPy vs pandas: {col} mismatch"
    )
print("   ✓ All OHLC values match across providers")

# Check OHLC constraints
print("\n5. Checking OHLC constraints...")
for idx, row in result_pandas.iterrows():
    min_oc = min(row['open'], row['close'])
    max_oc = max(row['open'], row['close'])
    assert row['low'] <= min_oc, f"Constraint violation at index {idx}: low > min(open,close)"
    assert row['high'] >= max_oc, f"Constraint violation at index {idx}: high < max(open,close)"
print("   ✓ OHLC constraints satisfied")

# Test df=False (list output)
print("\n6. Testing list output (df=False)...")
result_list = history_n(symbol, '1m', 10, end_time=end_time, provider='pandas', df=False)
assert isinstance(result_list, list), "Should return list"
assert len(result_list) == 10, "Should have 10 bars"
assert all('symbol' in bar and 'eob' in bar for bar in result_list), "Missing required fields"
print("   ✓ List output works correctly")

# Test field filtering
print("\n7. Testing field filtering...")
result_filtered = history_n(symbol, '1m', 10,
                            end_time=end_time,
                            fields='open,close',
                            provider='pandas',
                            df=True)
assert 'open' in result_filtered.columns, "open should be in columns"
assert 'close' in result_filtered.columns, "close should be in columns"
assert 'symbol' in result_filtered.columns, "symbol should always be included"
assert 'eob' in result_filtered.columns, "eob should always be included"
print("   ✓ Field filtering works correctly")

print("\n" + "=" * 60)
print("✓ All tests passed! pandas provider is consistent.")
print("=" * 60)
