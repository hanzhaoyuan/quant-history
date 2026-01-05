"""Debug script to find data inconsistency between providers"""
from providers import history_n

symbol = '000001.SH'
end_time = '2024-01-15 14:30:00'

print("Comparing data generation across providers...")
print("=" * 60)

# Get data from each provider
cpp_data = history_n(symbol, '1m', 30000, end_time=end_time, provider='cpp_pybind', df=True)
python_data = history_n(symbol, '1m', 30000, end_time=end_time, provider='python', df=True)
numpy_data = history_n(symbol, '1m', 30000, end_time=end_time, provider='numpy', df=True)
pandas_data = history_n(symbol, '1m', 30000, end_time=end_time, provider='pandas', df=True)

print(f"cpp_pybind: {len(cpp_data)} rows")
print(f"python:     {len(python_data)} rows")
print(f"numpy:      {len(numpy_data)} rows")
print(f"pandas:     {len(pandas_data)} rows")
print()

# Check first and last dates
print("First eob:")
print(f"  cpp_pybind: {cpp_data.iloc[0]['eob']}")
print(f"  python:     {python_data.iloc[0]['eob']}")
print()

print("Last eob:")
print(f"  cpp_pybind: {cpp_data.iloc[-1]['eob']}")
print(f"  python:     {python_data.iloc[-1]['eob']}")
print()

# Find where they diverge
if len(cpp_data) != len(python_data):
    min_len = min(len(cpp_data), len(python_data))
    print(f"Checking first {min_len} rows for divergence...")

    for i in range(min_len):
        if cpp_data.iloc[i]['eob'] != python_data.iloc[i]['eob']:
            print(f"\nFirst divergence at index {i}:")
            print(f"  cpp_pybind: {cpp_data.iloc[i]['eob']}")
            print(f"  python:     {python_data.iloc[i]['eob']}")

            # Show context
            if i > 0:
                print(f"  Previous (i-1):")
                print(f"    cpp: {cpp_data.iloc[i-1]['eob']}")
                print(f"    py:  {python_data.iloc[i-1]['eob']}")
            break
    else:
        print(f"First {min_len} rows match, difference is at the end")
        if len(cpp_data) > len(python_data):
            print(f"\ncpp_pybind has extra rows starting from index {min_len}:")
            print(f"  {cpp_data.iloc[min_len]['eob']}")
        else:
            print(f"\npython has extra rows starting from index {min_len}:")
            print(f"  {python_data.iloc[min_len]['eob']}")
