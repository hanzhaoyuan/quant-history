"""
Main benchmark script for history_n performance evaluation

This script benchmarks different provider implementations across various
parameter combinations to measure query performance.
"""

import json
import itertools
from providers import history_n
from .utils import benchmark_function, print_benchmark_table

# Test providers
PROVIDERS = ['python', 'numpy', 'pandas']

try:
    from _cpp_history_core import HistoryProvider
    PROVIDERS.insert(0, 'cpp_pybind')
except ImportError:
    print("WARNING: cpp_pybind provider not available")

try:
    from providers._cpp_cython import CythonHistoryProvider
    PROVIDERS.append('cpp_cython')
except ImportError:
    print("WARNING: cpp_cython provider not available")


# Test dimensions
TEST_MATRIX = {
    'symbol': ['000001.SH'],
    'frequency': ['1m'],
    'count': [100, 5000, 30000],
    'end_time': ['2024-01-15 14:30:00'],  # Fixed time for reproducibility
    'fields': [None, 'symbol,open,close,low,high,eob'],
    'df': [False, True]
}

# Benchmark parameters
WARMUP_RUNS = 10
BENCHMARK_RUNS = 30


def generate_test_cases():
    """Generate all test case combinations"""
    keys = ['symbol', 'frequency', 'count', 'end_time', 'fields', 'df']
    values = [TEST_MATRIX[k] for k in keys]

    for combination in itertools.product(*values):
        case = dict(zip(keys, combination))
        yield case


def classify_path(df: bool, fields: any) -> str:
    """
    Classify the data path taken

    Paths:
    - A_numpy_only: df=False, returns arrays (for C++ providers, this is list conversion)
    - B_numpy_to_df: df=True, from arrays to DataFrame
    - C_list_to_df: df=True, but data comes from list[dict] internally
    """
    if df:
        return "B_numpy_to_df"
    else:
        return "C_list_conversion"


def run_single_benchmark(provider: str, case: dict) -> dict:
    """Run benchmark for a single provider and test case"""
    stats = benchmark_function(
        history_n,
        kwargs={**case, 'provider': provider},
        warmup=WARMUP_RUNS,
        repeat=BENCHMARK_RUNS
    )

    path = classify_path(case['df'], case['fields'])

    result = {
        'provider': provider,
        'path': path,
        'symbol': case['symbol'],
        'count': case['count'],
        'fields': 'all' if case['fields'] is None else 'subset',
        'df': case['df'],
        'end_time': case['end_time'],
        **stats
    }

    return result


def run_all_benchmarks():
    """Run complete benchmark suite"""
    print("\n" + "=" * 100)
    print("HISTORY_N PERFORMANCE BENCHMARK".center(100))
    print("=" * 100)
    print(f"\nProviders: {', '.join(PROVIDERS)}")
    print(f"Warmup runs: {WARMUP_RUNS}")
    print(f"Benchmark runs: {BENCHMARK_RUNS}")
    print()

    all_results = []

    test_cases = list(generate_test_cases())
    total_tests = len(PROVIDERS) * len(test_cases)
    current = 0

    print(f"Total benchmark runs: {total_tests}\n")

    for provider in PROVIDERS:
        print(f"\nBenchmarking provider: {provider}")
        print("-" * 50)

        for case in test_cases:
            current += 1
            print(f"[{current}/{total_tests}] {provider} | count={case['count']} | df={case['df']} | fields={'all' if case['fields'] is None else 'subset'}", end=' ... ')

            try:
                result = run_single_benchmark(provider, case)
                all_results.append(result)
                print(f"{result['mean_ms']:.2f} ms")
            except Exception as e:
                print(f"FAILED: {e}")
                continue

    # Print summary tables
    print_benchmark_table(all_results, "Complete Benchmark Results")

    # Group by count
    for count in TEST_MATRIX['count']:
        count_results = [r for r in all_results if r['count'] == count]
        if count_results:
            print_benchmark_table(count_results, f"Results for count={count}")

    # Save to JSON
    output_file = 'benchmark_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Print summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS".center(100))
    print("=" * 100)

    for provider in PROVIDERS:
        provider_results = [r for r in all_results if r['provider'] == provider]
        if provider_results:
            mean_times = [r['mean_ms'] for r in provider_results]
            print(f"\n{provider}:")
            print(f"  Average time: {sum(mean_times)/len(mean_times):.2f} ms")
            print(f"  Fastest: {min(mean_times):.2f} ms")
            print(f"  Slowest: {max(mean_times):.2f} ms")


if __name__ == '__main__':
    run_all_benchmarks()
