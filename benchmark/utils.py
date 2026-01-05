"""Utility functions for benchmarking"""
import time
import numpy as np
from typing import Callable, Dict, Any


def timeit(func: Callable, *args, **kwargs) -> float:
    """
    Time a single function call

    Returns:
        Execution time in seconds
    """
    start = time.perf_counter()
    func(*args, **kwargs)
    end = time.perf_counter()
    return end - start


def benchmark_function(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    warmup: int = 10,
    repeat: int = 30
) -> Dict[str, float]:
    """
    Benchmark a function with warmup and multiple runs

    Args:
        func: Function to benchmark
        args: Positional arguments
        kwargs: Keyword arguments
        warmup: Number of warmup runs
        repeat: Number of timed runs

    Returns:
        Dictionary with timing statistics (in milliseconds)
    """
    if kwargs is None:
        kwargs = {}

    # Warmup
    for _ in range(warmup):
        func(*args, **kwargs)

    # Benchmark
    times = []
    for _ in range(repeat):
        elapsed = timeit(func, *args, **kwargs)
        times.append(elapsed * 1000)  # Convert to ms

    times_array = np.array(times)

    return {
        'mean_ms': float(np.mean(times_array)),
        'std_ms': float(np.std(times_array)),
        'min_ms': float(np.min(times_array)),
        'max_ms': float(np.max(times_array)),
        'p50_ms': float(np.percentile(times_array, 50)),
        'p95_ms': float(np.percentile(times_array, 95)),
        'p99_ms': float(np.percentile(times_array, 99)),
        'throughput_per_sec': 1000.0 / np.mean(times_array)
    }


def format_time(ms: float) -> str:
    """Format time in milliseconds to human-readable string"""
    if ms < 1:
        return f"{ms*1000:.2f} us"  # Changed from µs to us for Windows compatibility
    elif ms < 1000:
        return f"{ms:.2f} ms"
    else:
        return f"{ms/1000:.2f} s"


def print_benchmark_table(results: list, title: str = "Benchmark Results"):
    """
    Print benchmark results as a formatted table

    Args:
        results: List of result dictionaries
        title: Table title
    """
    print(f"\n{'=' * 100}")
    print(f"{title:^100}")
    print(f"{'=' * 100}")

    # Header
    header = f"{'Provider':<15} {'Path':<20} {'Count':<8} {'Mean':<12} {'P50':<12} {'P95':<12} {'P99':<12} {'Throughput':<15}"
    print(header)
    print('-' * 100)

    # Rows
    for result in results:
        provider = result.get('provider', 'N/A')
        path = result.get('path', 'N/A')
        count = result.get('count', 'N/A')
        mean = format_time(result.get('mean_ms', 0))
        p50 = format_time(result.get('p50_ms', 0))
        p95 = format_time(result.get('p95_ms', 0))
        p99 = format_time(result.get('p99_ms', 0))
        throughput = f"{result.get('throughput_per_sec', 0):.1f} calls/s"

        row = f"{provider:<15} {path:<20} {count:<8} {mean:<12} {p50:<12} {p95:<12} {p99:<12} {throughput:<15}"
        print(row)

    print('=' * 100)
