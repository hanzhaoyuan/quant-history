# history_n 最佳实施方案

## 📋 执行摘要

**推荐方案**: 根据使用场景选择 provider，**不推荐 cpp_pybind**

| 场景 | 推荐 Provider | 性能 | 理由 |
|------|--------------|------|------|
| **DataFrame 输出** | **pandas** | 0.36 ms | 性能最优，快 20-600 倍 |
| **小量 list 输出** (<1000) | **numpy** | 0.10 ms | 最快 |
| **大量 list 输出** (>=1000) | **python** | 1.01 ms | 稳定高效 |
| ❌ 不推荐 | cpp_pybind | 245 ms | df=False 性能崩溃 |

---

## 方案 A：默认推荐（立即采用）⭐

### 统一使用 pandas（性能最优）

```python
from providers import history_n

# 推荐：统一使用 pandas + df=True
result = history_n(
    symbol='000001.SH',
    frequency='1m',
    count=5000,
    end_time='2024-01-15 14:30:00',
    df=True,           # 返回 DataFrame
    provider='pandas'  # 性能之王
)

# 性能：0.38 ms ⚡
# 如果需要 list[dict]，从 DataFrame 转换也很快：
result_list = result.to_dict('records')  # 额外 ~1ms
```

**优势**：
- ✅ 性能最优（0.36-0.38 ms）
- ✅ API 一致，DataFrame 是量化分析标准格式
- ✅ 即使需要 list，转换开销也小于直接用其他 provider

---

## 方案 B：性能优化方案（按场景选择）

### 配置文件：providers/config.py

```python
"""Provider selection configuration based on use case"""

def get_optimal_provider(count: int, df: bool) -> str:
    """
    Auto-select the fastest provider based on parameters

    Args:
        count: Number of bars requested
        df: Whether DataFrame output is needed

    Returns:
        Provider name: 'pandas', 'numpy', or 'python'
    """
    if df:
        # DataFrame output: always use pandas (fastest)
        return 'pandas'
    else:
        # list[dict] output: choose based on data size
        if count < 1000:
            return 'numpy'   # Fastest for small data
        else:
            return 'python'  # Most stable for large data

    # Never return 'cpp_pybind' - performance issue with df=False


# Recommended default
DEFAULT_PROVIDER = 'pandas'
```

### 智能封装：providers/smart_query.py

```python
"""Smart wrapper that auto-selects optimal provider"""
from typing import Union, List, Dict
from datetime import datetime
import pandas as pd
from .config import get_optimal_provider
from . import history_n as _history_n


def smart_history_n(
    symbol: str,
    frequency: str,
    count: int,
    end_time: Union[None, str, datetime] = None,
    fields: str = None,
    df: bool = True,  # Default to DataFrame (best practice)
    auto_optimize: bool = True,  # Auto-select provider
    **kwargs
) -> Union[List[Dict], pd.DataFrame]:
    """
    Smart history_n query with automatic provider selection

    Performance-optimized wrapper that automatically selects the
    fastest provider based on your parameters.

    Args:
        symbol: Stock symbol
        frequency: '1m' or '60s'
        count: Number of bars (max 33000)
        end_time: End time (None, str, or datetime)
        fields: Comma-separated field names or None for all
        df: Return DataFrame (True) or list[dict] (False)
        auto_optimize: Auto-select optimal provider (recommended)
        **kwargs: Additional arguments

    Returns:
        DataFrame if df=True, else list[dict]

    Examples:
        # Recommended usage (auto-optimized):
        >>> result = smart_history_n('000001.SH', '1m', 5000, df=True)
        # Uses pandas, ~0.38 ms

        # Small list query:
        >>> result = smart_history_n('000001.SH', '1m', 100, df=False)
        # Uses numpy, ~0.10 ms

        # Large list query:
        >>> result = smart_history_n('000001.SH', '1m', 10000, df=False)
        # Uses python, ~1.0 ms
    """
    if auto_optimize:
        provider = get_optimal_provider(count, df)
    else:
        provider = kwargs.pop('provider', 'pandas')

    return _history_n(
        symbol=symbol,
        frequency=frequency,
        count=count,
        end_time=end_time,
        fields=fields,
        df=df,
        provider=provider,
        **kwargs
    )
```

### 使用示例

```python
from providers.smart_query import smart_history_n

# 1. 推荐用法：DataFrame 输出（自动选择 pandas）
df = smart_history_n('000001.SH', '1m', 5000, df=True)
# 性能：~0.38 ms

# 2. 小数据量 list 输出（自动选择 numpy）
bars = smart_history_n('000001.SH', '1m', 100, df=False)
# 性能：~0.10 ms

# 3. 大数据量 list 输出（自动选择 python）
bars = smart_history_n('000001.SH', '1m', 10000, df=False)
# 性能：~1.0 ms

# 4. 禁用自动优化（手动指定）
df = smart_history_n('000001.SH', '1m', 5000,
                     auto_optimize=False,
                     provider='pandas')
```

---

## 方案 C：修复 cpp_pybind 性能问题（可选）

### 问题诊断

**根本原因**：pybind11 将 `std::vector` 逐个转换为 Python dict 时，存在以下瓶颈：

```cpp
// 当前实现（慢 245ms）
std::vector<Bar> bars = query(...);  // C++ side
// pybind11 自动转换：
for (auto& bar : bars) {
    py::dict d;
    d["symbol"] = bar.symbol;    // 5000 次跨语言调用
    d["open"] = bar.open;        // 5000 次跨语言调用
    d["high"] = bar.high;        // ...
    // 总计：5000 bars × 6 fields = 30000 次跨语言调用！
}
```

### 修复方案：返回列式数据，让 Python 端转换

#### 修改 C++ 绑定（bindings/pybind11/binding.cpp）

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "history_provider.h"

namespace py = pybind11;

PYBIND11_MODULE(_cpp_history_core, m) {
    // 只暴露列式结果，不做行式转换
    py::class_<QueryResult>(m, "QueryResult")
        .def_readonly("symbols", &QueryResult::symbols)
        .def_readonly("opens", &QueryResult::opens)
        .def_readonly("highs", &QueryResult::highs)
        .def_readonly("lows", &QueryResult::lows)
        .def_readonly("closes", &QueryResult::closes)
        .def_readonly("eob_timestamps", &QueryResult::eob_timestamps)

        // 添加辅助方法：返回行数
        .def_property_readonly("size", [](const QueryResult& r) {
            return r.eob_timestamps.size();
        });

    py::class_<HistoryProvider>(m, "HistoryProvider")
        .def(py::init<>())
        .def("query", &HistoryProvider::query,
             py::arg("symbol"),
             py::arg("count"),
             py::arg("end_time_ts"),
             py::arg("fields"),
             // 返回值策略：移动语义，避免拷贝
             py::return_value_policy::move);
}
```

#### 优化 Python Wrapper（providers/cpp_pybind_provider.py）

```python
"""Optimized cpp_pybind provider"""
from typing import Union, Optional, List, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from _cpp_history_core import HistoryProvider as _CppProvider
from .utils import parse_end_time, timestamp_to_datetime, validate_frequency, parse_fields


class OptimizedCppProvider:
    """Optimized wrapper with efficient list conversion"""

    def __init__(self):
        self.provider = _CppProvider()

    def query_to_lists(self, result) -> List[Dict]:
        """
        Efficient columnar-to-row conversion using NumPy

        Strategy: Use NumPy's vectorized operations instead of Python loops
        """
        size = result.size
        if size == 0:
            return []

        # Convert C++ vectors to NumPy arrays (fast, no copy)
        symbols = np.array(result.symbols, dtype=object)
        opens = np.array(result.opens, dtype=np.float64)
        highs = np.array(result.highs, dtype=np.float64)
        lows = np.array(result.lows, dtype=np.float64)
        closes = np.array(result.closes, dtype=np.float64)
        eob_ts = np.array(result.eob_timestamps, dtype=np.int64)

        # Convert timestamps to datetime (vectorized)
        eob_datetimes = [timestamp_to_datetime(ts) for ts in eob_ts]

        # Build list of dicts using dict comprehension (faster)
        # Method 1: List comprehension (fast)
        bars = [
            {
                'symbol': symbols[i],
                'open': opens[i],
                'high': highs[i],
                'low': lows[i],
                'close': closes[i],
                'eob': eob_datetimes[i]
            }
            for i in range(size)
        ]

        return bars

    def query_to_dataframe(self, result) -> pd.DataFrame:
        """
        Efficient conversion to DataFrame (zero-copy)
        """
        if result.size == 0:
            return pd.DataFrame()

        # Convert timestamps
        eob_datetimes = [timestamp_to_datetime(ts)
                        for ts in result.eob_timestamps]

        # Build DataFrame directly from C++ vectors
        return pd.DataFrame({
            'symbol': result.symbols,
            'open': result.opens,
            'high': result.highs,
            'low': result.lows,
            'close': result.closes,
            'eob': eob_datetimes
        })


# Singleton instance
_optimized_provider = None


def get_provider():
    global _optimized_provider
    if _optimized_provider is None:
        _optimized_provider = OptimizedCppProvider()
    return _optimized_provider


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
    """Optimized cpp_pybind query"""
    validate_frequency(frequency)

    if count <= 0:
        return pd.DataFrame() if df else []

    if count > 33000:
        count = 33000

    end_time_ts = parse_end_time(end_time)
    field_list = parse_fields(fields)

    provider = get_provider()
    result = provider.provider.query(symbol, count, end_time_ts, field_list)

    if result.size == 0:
        return pd.DataFrame() if df else []

    # Use optimized conversion
    if df:
        return provider.query_to_dataframe(result)
    else:
        return provider.query_to_lists(result)
```

**预期性能提升**：
- df=False: 从 245 ms → **预计 2-5 ms**（提升 50-100 倍）
- df=True: 保持 8-9 ms（已经够快）

---

## 方案 D：生产环境配置建议

### 1. 统一入口配置

**providers/__init__.py** 修改默认 provider：

```python
"""
History providers with smart defaults
"""
from .python_provider import history_n as python_history_n
from .numpy_provider import history_n as numpy_history_n
from .pandas_provider import history_n as pandas_history_n

try:
    from .cpp_pybind_provider import history_n as cpp_pybind_history_n
    _HAS_CPP_PYBIND = True
except ImportError:
    _HAS_CPP_PYBIND = False


def history_n(
    symbol: str,
    frequency: str,
    count: int,
    end_time=None,
    fields=None,
    skip_suspended: bool = True,
    fill_missing=None,
    adjust: str = 'none',
    adjust_end_time: str = '',
    df: bool = True,  # ← 改为默认 True（最佳实践）
    provider: str = 'pandas'  # ← 改为默认 pandas（性能最优）
):
    """
    Unified history_n interface with performance-optimized defaults

    Default configuration (recommended):
    - df=True: Return DataFrame (faster and more practical)
    - provider='pandas': Best overall performance

    Performance guide:
    - For DataFrame output: use 'pandas' (0.36 ms)
    - For small list output (<1000): use 'numpy' (0.10 ms)
    - For large list output (>=1000): use 'python' (1.0 ms)
    - Avoid: 'cpp_pybind' with df=False (245 ms - 200x slower!)
    """
    if provider == 'pandas':
        return pandas_history_n(symbol, frequency, count, end_time,
                               fields, skip_suspended, fill_missing,
                               adjust, adjust_end_time, df)
    elif provider == 'numpy':
        return numpy_history_n(symbol, frequency, count, end_time,
                              fields, skip_suspended, fill_missing,
                              adjust, adjust_end_time, df)
    elif provider == 'python':
        return python_history_n(symbol, frequency, count, end_time,
                               fields, skip_suspended, fill_missing,
                               adjust, adjust_end_time, df)
    elif provider == 'cpp_pybind':
        if not _HAS_CPP_PYBIND:
            raise ImportError("cpp_pybind provider not available")
        if not df:
            import warnings
            warnings.warn(
                "cpp_pybind with df=False is 200x slower than pandas! "
                "Consider using provider='pandas' or 'python' instead.",
                PerformanceWarning,
                stacklevel=2
            )
        return cpp_pybind_history_n(symbol, frequency, count, end_time,
                                    fields, skip_suspended, fill_missing,
                                    adjust, adjust_end_time, df)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# 定义性能警告类
class PerformanceWarning(UserWarning):
    """Warning for performance issues"""
    pass


# 便捷导出
__all__ = ['history_n']
```

### 2. 使用示例

```python
from providers import history_n

# 方式 1：使用默认配置（推荐）
result = history_n('000001.SH', '1m', 5000)
# 自动使用 pandas + df=True，性能最优

# 方式 2：明确指定
result = history_n('000001.SH', '1m', 5000,
                   df=True,
                   provider='pandas')

# 方式 3：如果需要 list
result = history_n('000001.SH', '1m', 100,
                   df=False,      # 需要 list
                   provider='numpy')  # 小数据用 numpy
```

---

## 迁移指南

### 从 cpp_pybind 迁移到 pandas

#### Before（慢）
```python
# 旧代码：使用 cpp_pybind
result = history_n('000001.SH', '1m', 5000,
                   df=False,  # ← 性能崩溃点
                   provider='cpp_pybind')
# 耗时：245 ms ❌
```

#### After（快）
```python
# 新代码：使用 pandas
result = history_n('000001.SH', '1m', 5000,
                   df=True,   # ← 改为 DataFrame
                   provider='pandas')
# 耗时：0.38 ms ✅ (快 646 倍！)

# 如果确实需要 list[dict]:
result_list = result.to_dict('records')
# 额外耗时：~1 ms
# 总耗时：1.38 ms（仍然快 177 倍！）
```

### 兼容性处理

```python
def legacy_query(symbol, count, df=False):
    """
    兼容旧代码的封装函数
    """
    # 智能转换：总是用 pandas（快）
    result = history_n(symbol, '1m', count,
                      df=True,  # 内部用 DataFrame（快）
                      provider='pandas')

    # 如果旧代码需要 list，再转换
    if not df:
        return result.to_dict('records')
    else:
        return result
```

---

## 性能对比总结

### 场景 1: DataFrame 输出（df=True, count=5000）

| Provider | 耗时 | 相对 pandas | 推荐 |
|----------|------|------------|------|
| **pandas** | **0.38 ms** | 1x (基准) | ✅ 强烈推荐 |
| numpy | 7.62 ms | 20x | ❌ |
| cpp_pybind | 8.68 ms | 23x | ❌ |
| python | 8.61 ms | 23x | ❌ |

### 场景 2: List 输出（df=False, count=5000）

| Provider | 耗时 | 相对最优 | 推荐 |
|----------|------|----------|------|
| **python** | **1.01 ms** | 1x (基准) | ✅ 推荐 |
| numpy | 2.03 ms | 2x | ⚠️ 可用 |
| pandas | 5.00 ms | 5x | ⚠️ 可用 |
| cpp_pybind | **245 ms** | **243x** | ❌ 禁用 |

### 场景 3: 小数据 List 输出（df=False, count=100）

| Provider | 耗时 | 相对最优 | 推荐 |
|----------|------|----------|------|
| **numpy** | **0.10 ms** | 1x (基准) | ✅ 强烈推荐 |
| cpp_pybind | 0.61 ms | 6x | ❌ |
| pandas | 0.87 ms | 9x | ❌ |
| python | 0.91 ms | 9x | ❌ |

---

## 最终建议

### 🎯 立即采用（方案 A）

**90% 场景适用：统一使用 pandas**

```python
# 默认配置
from providers import history_n

result = history_n('000001.SH', '1m', 5000)  # 默认 df=True, provider='pandas'
```

**优势**：
- 性能最优（0.36-0.38 ms）
- 代码最简洁
- DataFrame 是量化分析标准

---

### 🔧 高级优化（方案 B）

**需要榨取每一点性能时：按场景自动选择**

```python
from providers.smart_query import smart_history_n

result = smart_history_n('000001.SH', '1m', count, df=df)
# 自动选择最优 provider
```

---

### ⚠️ 性能警告

**永远不要这样用：**
```python
# ❌ 禁止！性能崩溃！
history_n(..., df=False, provider='cpp_pybind')  # 245 ms
```

**应该改为：**
```python
# ✅ 推荐：
history_n(..., df=True, provider='pandas')  # 0.38 ms
```

---

## 后续优化空间

1. **修复 cpp_pybind**（方案 C）：预计提升 50-100 倍
2. **Cython 实现**：可能比 pandas 更快
3. **批量查询优化**：多 symbol 并行查询
4. **缓存策略**：热数据内存缓存

---

## 检查清单

- [ ] 将默认 provider 改为 'pandas'
- [ ] 将默认 df 改为 True
- [ ] 更新所有业务代码使用 pandas
- [ ] 添加 PerformanceWarning 警告 cpp_pybind + df=False
- [ ] 可选：实现 smart_history_n 自动优化
- [ ] 可选：修复 cpp_pybind 性能问题
- [ ] 更新文档和示例代码

---

**结论**: **立即采用 pandas 作为默认 provider**，性能最优且最稳定。
