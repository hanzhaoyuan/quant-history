#!/usr/bin/env python
"""
Quick Start Example for history_n API
Demonstrates best practices based on performance benchmarks
"""

from providers import history_n
import time


def demo_recommended_usage():
    """Recommended usage: pandas with DataFrame output"""
    print("=" * 70)
    print("1. RECOMMENDED: pandas provider with DataFrame output")
    print("=" * 70)

    start = time.perf_counter()
    df = history_n('000001.SH', '1m', 5000)  # Uses defaults: df=True, provider='pandas'
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Result: {len(df)} bars")
    print(f"Performance: {elapsed:.2f} ms")
    print(f"Data type: {type(df)}")
    print(f"\nFirst 3 bars:\n{df.head(3)}\n")


def demo_list_output_small():
    """For small data: numpy is fastest"""
    print("=" * 70)
    print("2. Small list output (<1000 bars): Use numpy")
    print("=" * 70)

    start = time.perf_counter()
    bars = history_n('000001.SH', '1m', 100, df=False, provider='numpy')
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Result: {len(bars)} bars")
    print(f"Performance: {elapsed:.2f} ms")
    print(f"Data type: {type(bars)}")
    print(f"\nFirst bar:\n{bars[0]}\n")


def demo_list_output_large():
    """For large data: python is most stable"""
    print("=" * 70)
    print("3. Large list output (>=1000 bars): Use python")
    print("=" * 70)

    start = time.perf_counter()
    bars = history_n('000001.SH', '1m', 5000, df=False, provider='python')
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Result: {len(bars)} bars")
    print(f"Performance: {elapsed:.2f} ms")
    print(f"Data type: {type(bars)}")
    print(f"\nFirst bar:\n{bars[0]}\n")


def demo_field_filtering():
    """Field filtering example"""
    print("=" * 70)
    print("4. Field filtering: Only get specific columns")
    print("=" * 70)

    start = time.perf_counter()
    df = history_n('000001.SH', '1m', 1000,
                   fields='symbol,open,close,eob',
                   df=True,
                   provider='pandas')
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Result: {len(df)} bars with {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")
    print(f"Performance: {elapsed:.2f} ms")
    print(f"\nFirst 3 bars:\n{df.head(3)}\n")


def demo_time_range():
    """Query specific time range"""
    print("=" * 70)
    print("5. Time range query: Get data up to specific time")
    print("=" * 70)

    start = time.perf_counter()
    df = history_n('000001.SH', '1m', 1000,
                   end_time='2024-01-15 14:30:00',
                   provider='pandas')
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Result: {len(df)} bars")
    print(f"Performance: {elapsed:.2f} ms")
    print(f"Last bar time: {df['eob'].iloc[-1]}")
    print(f"\nLast 3 bars:\n{df.tail(3)}\n")


def demo_bad_practice():
    """WARNING: This is slow! Demonstrates what NOT to do"""
    print("=" * 70)
    print("⚠️  WARNING: Bad practice (extremely slow!)")
    print("=" * 70)

    import warnings

    # This will trigger a PerformanceWarning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        start = time.perf_counter()
        bars = history_n('000001.SH', '1m', 5000,
                        df=False,              # ← Problem 1: list output
                        provider='cpp_pybind') # ← Problem 2: cpp_pybind
        elapsed = (time.perf_counter() - start) * 1000

        if w:
            print(f"⚠️  {w[0].category.__name__}: {w[0].message}\n")

        print(f"Result: {len(bars)} bars")
        print(f"Performance: {elapsed:.2f} ms ❌ (VERY SLOW!)")
        print(f"\nThis is 200-600x slower than recommended alternatives!")
        print(f"Use pandas or python provider instead.\n")


def demo_performance_comparison():
    """Compare all providers for the same query"""
    print("=" * 70)
    print("6. Performance Comparison: All providers")
    print("=" * 70)

    providers = ['pandas', 'numpy', 'python', 'cpp_pybind']
    results = {}

    for provider in providers:
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)

        start = time.perf_counter()
        result = history_n('000001.SH', '1m', 5000,
                          df=True,  # Fair comparison
                          provider=provider)
        elapsed = (time.perf_counter() - start) * 1000

        results[provider] = elapsed

    # Sort by performance
    sorted_results = sorted(results.items(), key=lambda x: x[1])

    print(f"Query: 5000 bars, df=True\n")
    print(f"{'Provider':<15} {'Time (ms)':<12} {'Relative':<12} {'Rating'}")
    print("-" * 60)

    fastest = sorted_results[0][1]
    for provider, elapsed in sorted_results:
        relative = elapsed / fastest
        if relative <= 1.5:
            rating = "⭐⭐⭐⭐⭐ Excellent"
        elif relative <= 3:
            rating = "⭐⭐⭐⭐ Good"
        elif relative <= 10:
            rating = "⭐⭐⭐ OK"
        else:
            rating = "⭐⭐ Slow"

        print(f"{provider:<15} {elapsed:>8.2f}     {relative:>6.1f}x      {rating}")

    print(f"\n🏆 Winner: {sorted_results[0][0]} ({sorted_results[0][1]:.2f} ms)\n")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "history_n Performance Quick Start" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Run demos
    demo_recommended_usage()
    demo_list_output_small()
    demo_list_output_large()
    demo_field_filtering()
    demo_time_range()
    demo_performance_comparison()
    demo_bad_practice()  # This should be last (shows warning)

    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    print("✅ Best practice: history_n(..., df=True, provider='pandas')")
    print("✅ Small list: history_n(..., df=False, provider='numpy')")
    print("✅ Large list: history_n(..., df=False, provider='python')")
    print("❌ Avoid: cpp_pybind with df=False (200-600x slower!)")
    print()
