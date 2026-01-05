"""Debug random number generation consistency"""
from providers import history_n

symbol = '000001.SH'

# Get first 10 bars from each provider
cpp_data = history_n(symbol, '1m', 10, end_time='2024-01-15 14:30:00', provider='cpp_pybind', df=True)
python_data = history_n(symbol, '1m', 10, end_time='2024-01-15 14:30:00', provider='python', df=True)

print("Comparing first 10 bars:")
print("=" * 80)

for i in range(10):
    print(f"\nBar {i} (eob: {cpp_data.iloc[i]['eob']}):")
    print(f"  cpp_pybind - open: {cpp_data.iloc[i]['open']:.10f}, close: {cpp_data.iloc[i]['close']:.10f}")
    print(f"  python     - open: {python_data.iloc[i]['open']:.10f}, close: {python_data.iloc[i]['close']:.10f}")

    if abs(cpp_data.iloc[i]['open'] - python_data.iloc[i]['open']) > 0.0001:
        print("  ❌ MISMATCH!")
    else:
        print("  ✓ Match")
