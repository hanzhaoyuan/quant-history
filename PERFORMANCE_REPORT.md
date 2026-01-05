# history_n 性能测试报告

## 执行摘要

**测试日期**: 2026-01-05
**测试环境**: Windows 11, Python 3.10.19, MSVC 19.50, NumPy 1.26.4, pandas 2.2.3
**测试方法**: 每个测试点 warmup 10次，执行 30次取平均值

---

## 📖 关键概念：df 参数说明

### 什么是 df 参数？

`df` 参数控制 `history_n()` 函数的**返回数据格式**：

```python
# df=True: 返回 pandas DataFrame（推荐）
df_result = history_n('000001.SH', '1m', 5000, df=True)
# 类型: <class 'pandas.core.frame.DataFrame'>
# 格式:
#        symbol   open    high     low   close                 eob
# 0  000001.SH  95.23  100.45   94.12   98.76 2024-01-02 09:31:00+08:00
# 1  000001.SH  98.80  102.15   97.23  100.45 2024-01-02 09:32:00+08:00
# ...

# df=False: 返回 list[dict]（字典列表）
list_result = history_n('000001.SH', '1m', 5000, df=False)
# 类型: <class 'list'>
# 格式:
# [
#     {'symbol': '000001.SH', 'open': 95.23, 'high': 100.45, 'low': 94.12,
#      'close': 98.76, 'eob': datetime(2024, 1, 2, 9, 31, 0, tzinfo=UTC+8)},
#     {'symbol': '000001.SH', 'open': 98.80, 'high': 102.15, 'low': 97.23,
#      'close': 100.45, 'eob': datetime(2024, 1, 2, 9, 32, 0, tzinfo=UTC+8)},
#     ...
# ]
```

### 两种格式的区别

| 特性 | df=True (DataFrame) | df=False (list[dict]) |
|------|---------------------|----------------------|
| **数据结构** | 列式存储（columnar） | 行式存储（row-based） |
| **访问方式** | `df['open']`, `df.iloc[0]` | `list[0]['open']` |
| **性能** | ⚡ 极快（向量化运算） | 慢（逐行处理） |
| **内存效率** | 高（连续内存） | 低（分散对象） |
| **典型用途** | 数据分析、计算指标、可视化 | 逐条处理、JSON 序列化 |
| **pandas 操作** | ✅ 原生支持 | ❌ 需要转换 |

### 为什么 df=True 通常更快？

**列式存储的优势**（DataFrame）:
```python
# DataFrame: 列式存储，连续内存
{
    'symbol': ['000001.SH', '000001.SH', ...],  # 5000 个元素的数组
    'open':   [95.23, 98.80, ...],              # 5000 个 float64 的连续内存
    'close':  [98.76, 100.45, ...],             # 直接从 C++ vector 零拷贝
}
# 优势：
# ✅ 零拷贝：C++ std::vector → NumPy array → DataFrame 列（极快）
# ✅ 向量化：操作整列数据时使用 SIMD 指令
# ✅ 缓存友好：连续内存，CPU 缓存命中率高
```

**行式存储的劣势**（list[dict]）:
```python
# list[dict]: 行式存储，分散对象
[
    {'symbol': '000001.SH', 'open': 95.23, ...},  # Python dict 对象
    {'symbol': '000001.SH', 'open': 98.80, ...},  # 又一个 dict 对象
    ...  # 5000 个独立的 dict 对象！
]
# 劣势：
# ❌ 需要构造：循环 5000 次，每次创建一个 dict（慢）
# ❌ 内存分散：5000 个 dict 对象散落在堆上
# ❌ GC 压力：大量小对象增加垃圾回收负担
# ❌ 跨语言开销：C++ → Python 逐个字段转换（cpp_pybind 的致命问题）
```

### 各 provider 的实现差异

| Provider | 内部存储 | df=True 转换 | df=False 转换 |
|----------|----------|-------------|--------------|
| **pandas** | DataFrame | ✅ 零拷贝返回 | ❌ 调用 `.to_dict('records')` |
| **numpy** | 列式 arrays | ⚠️ 构造 DataFrame | ⚠️ 循环构造 5000 个 dict |
| **python** | list[dict] | ❌ 调用 `pd.DataFrame(list)` | ✅ 零拷贝返回 |
| **cpp_pybind** | C++ vectors | ⚠️ pybind11 转 arrays → DataFrame | ❌❌ 30,000 次跨语言调用！|

**关键洞察**：
- **pandas + df=True**：存储格式与输出格式完全一致 → 最快（0.36 ms）
- **python + df=False**：存储格式与输出格式完全一致 → 快（1.0 ms）
- **cpp_pybind + df=False**：需要将 C++ 列式数据逐个转换为 Python dict → 崩溃（245 ms）

### 实际性能对比（count=5000）

```
场景 1: df=True（返回 DataFrame）
------------------------------------
pandas:      0.38 ms  ⚡⚡⚡ 极快（内部就是 DataFrame）
numpy:       7.62 ms  ⚡   快（arrays → DataFrame）
cpp_pybind:  8.68 ms  ⚡   快（C++ vectors → DataFrame）
python:      8.61 ms  ⚡   慢（list[dict] → DataFrame）

场景 2: df=False（返回 list[dict]）
------------------------------------
python:      1.01 ms  ⚡⚡  快（内部就是 list[dict]）
numpy:       2.03 ms  ⚡   中等（arrays → 5000 个 dict）
pandas:      5.00 ms       慢（DataFrame → list[dict]）
cpp_pybind:  245 ms   ❌❌❌ 崩溃（30,000 次跨语言调用）
```

### 如何选择？

**决策树**：
```
需要 DataFrame 做数据分析？
├─ 是 → df=True + provider='pandas'  (0.36 ms)  ✅ 最优
│
└─ 否 → 需要 list[dict]
    ├─ 数据量 < 1000？
    │  └─ 是 → df=False + provider='numpy'   (0.10 ms)  ✅ 最快
    │
    └─ 数据量 >= 1000？
       └─ 是 → df=False + provider='python'  (1.0 ms)   ✅ 稳定
```

**通用建议**：
1. **默认使用 df=True**：除非有明确理由需要 list[dict]
2. **量化分析必用 DataFrame**：计算指标、画图、统计都需要 DataFrame
3. **需要 JSON 序列化？**先用 df=True 获取，再 `.to_dict('records')`，总耗时仍然很快
4. **永远不要**：`df=False + provider='cpp_pybind'`（慢 200-600 倍）

---

## 🏆 性能排名总结

| 排名 | Provider | 平均耗时 | 最快场景 | 最慢场景 |
|------|----------|----------|----------|----------|
| 🥇 1 | **pandas** | **2.21 ms** | 0.36 ms | 5.66 ms |
| 🥈 2 | **numpy** | **3.74 ms** | 0.10 ms | 7.99 ms |
| 🥉 3 | **python** | **4.12 ms** | 0.91 ms | 10.13 ms |
| ❌ 4 | **cpp_pybind** | **85.55 ms** | 0.57 ms | 249.30 ms |

---

## 关键发现

### ⚠️ 惊人发现：C++ 实现反而最慢！

**cpp_pybind 存在严重性能缺陷：**
- ✅ df=True 时性能正常（8-9 ms）
- ❌ **df=False 时性能崩溃（245 ms）**

**问题根源**: pybind11 在将 C++ 列式数据（`std::vector<double>`）转换为 Python `list[dict]` 时，存在严重的性能瓶颈。

```
场景对比（count=5000）:
- cpp_pybind df=False: 245.12 ms  ← 性能崩溃！
- cpp_pybind df=True:    8.68 ms  ← 正常
- pandas df=False:       5.00 ms  ← 快 49 倍！
- pandas df=True:        0.38 ms  ← 快 646 倍！
```

---

## 详细性能分析

### 1. 小数据量场景 (count=100)

**最优选择**: 🏆 **numpy (df=False)** - 仅需 0.10 ms

| Provider | df=False | df=True | 推荐用途 |
|----------|----------|---------|----------|
| numpy | **0.10 ms** | 0.55 ms | df=False 时绝对最快 ✅ |
| pandas | 0.87 ms | **0.37 ms** | df=True 时最快 ✅ |
| cpp_pybind | 0.61 ms | 0.57 ms | 性能中等 |
| python | 0.91 ms | 1.67 ms | 最慢 |

**性能差距**: numpy df=False 比 python df=True 快 **16.7 倍**！

---

### 2. 中等数据量场景 (count=5000)

**最优选择**: 🏆 **pandas (df=True)** - 仅需 0.38 ms

| Provider | df=False | df=True | 性能评级 |
|----------|----------|---------|----------|
| pandas | 5.00 ms | **0.38 ms** ⚡ | 🥇 df=True 王者 |
| python | **1.01 ms** | 8.61 ms | 🥈 df=False 意外快 |
| numpy | 2.03 ms | 7.62 ms | 🥉 均衡性能 |
| cpp_pybind | **245.12 ms** ❌ | 8.68 ms | ❌ df=False 崩溃 |

**关键洞察**:
- pandas df=True 快到不可思议（0.38ms vs 5.00ms），**快 13 倍**
- **python df=False 竟然比 cpp_pybind 快 242 倍！**
- cpp_pybind 在 df=False 时完全不可用

---

### 3. 大数据量场景 (count=30000)

**最优选择**: 🏆 **pandas (df=True)** - 仅需 0.36 ms

| Provider | df=False | df=True | 扩展性 |
|----------|----------|---------|--------|
| pandas | 5.21 ms | **0.36 ms** ⚡ | 优秀：数据量增大性能不变 ✅ |
| python | **0.94 ms** | 8.44 ms | 好：df=False 性能稳定 ✅ |
| numpy | 2.03 ms | 7.56 ms | 好：性能稳定 ✅ |
| cpp_pybind | **244.81 ms** ❌ | 8.63 ms | 差：df=False 不可用 ❌ |

**扩展性分析**:
- pandas df=True: 从 100 到 30000 条，耗时几乎不变（0.37ms → 0.36ms）
- python df=False: 扩展性极佳（0.91ms → 0.94ms，仅增加 3%）
- cpp_pybind df=False: 性能与数据量无关（都是 ~245ms），说明瓶颈在数据转换

---

## 🎯 使用建议

### 场景 1: 需要 DataFrame 输出 (df=True)

```python
# 推荐：pandas（快 10-20 倍）
result = history_n('000001.SH', '1m', 5000, df=True, provider='pandas')
# 性能：0.38 ms ⚡
```

**为什么 pandas 这么快？**
- pandas 内部就是 DataFrame 存储，直接切片返回，零拷贝
- 其他 provider 需要先构造 list/arrays，再转 DataFrame

---

### 场景 2: 需要 list[dict] 输出 (df=False)

#### 小数据量 (count < 1000)
```python
# 推荐：numpy（最快）
result = history_n('000001.SH', '1m', 100, df=False, provider='numpy')
# 性能：0.10 ms ⚡
```

#### 大数据量 (count >= 1000)
```python
# 推荐：python（最稳定）
result = history_n('000001.SH', '1m', 5000, df=False, provider='python')
# 性能：1.01 ms
```

**为什么 python 在 df=False 时这么快？**
- python provider 内部就是 list[dict] 存储，直接切片返回
- numpy/cpp_pybind 需要把列式数据转成行式，有巨大开销

---

### ❌ 不推荐的用法

```python
# 千万不要这样用！性能崩溃！
result = history_n('000001.SH', '1m', 5000,
                   df=False,  # ← 关键：df=False
                   provider='cpp_pybind')  # ← 会慢 245ms！
```

---

## 技术解析

### 为什么 cpp_pybind 在 df=False 时这么慢？

**数据转换路径对比**:

```
pandas df=True（最快 0.38ms）:
  DataFrame 存储 → 直接切片 → 返回 ✅

python df=False（快 1.01ms）:
  list[dict] 存储 → 直接切片 → 返回 ✅

numpy df=False（中等 2.03ms）:
  列式 arrays → 循环构造 5000 个 dict → 返回 ⚠️

cpp_pybind df=False（崩溃 245ms）:
  C++ vectors → pybind11 转换 → 5000 次跨语言调用 → Python dict → 返回 ❌
```

**瓶颈**: pybind11 在构造 5000 个 Python dict 时，每次字段访问都是跨语言调用，性能损失巨大。

---

## 性能矩阵（完整对比）

### count=100

|  | cpp_pybind | python | numpy | pandas | 最优 |
|---|---|---|---|---|---|
| **df=False, all fields** | 0.61 ms | 0.91 ms | **0.10 ms** ⚡ | 0.87 ms | numpy |
| **df=True, all fields** | 0.57 ms | 1.67 ms | 0.55 ms | **0.37 ms** ⚡ | pandas |
| **df=False, subset** | 0.74 ms | 1.11 ms | **0.19 ms** ⚡ | 1.24 ms | numpy |
| **df=True, subset** | 0.89 ms | 1.74 ms | 0.82 ms | **0.71 ms** ⚡ | pandas |

### count=5000

|  | cpp_pybind | python | numpy | pandas | 最优 |
|---|---|---|---|---|---|
| **df=False, all fields** | 245.12 ms ❌ | **1.01 ms** ⚡ | 2.03 ms | 5.00 ms | python |
| **df=True, all fields** | 8.68 ms | 8.61 ms | 7.62 ms | **0.38 ms** ⚡ | pandas |
| **df=False, subset** | 249.14 ms ❌ | **2.45 ms** ⚡ | 4.09 ms | 5.66 ms | python |
| **df=True, subset** | 9.06 ms | 9.95 ms | 7.91 ms | **0.70 ms** ⚡ | pandas |

### count=30000

|  | cpp_pybind | python | numpy | pandas | 最优 |
|---|---|---|---|---|---|
| **df=False, all fields** | 244.81 ms ❌ | **0.94 ms** ⚡ | 2.03 ms | 5.21 ms | python |
| **df=True, all fields** | 8.63 ms | 8.44 ms | 7.56 ms | **0.36 ms** ⚡ | pandas |
| **df=False, subset** | 249.30 ms ❌ | **2.46 ms** ⚡ | 3.97 ms | 5.33 ms | python |
| **df=True, subset** | 9.10 ms | 10.13 ms | 7.99 ms | **0.71 ms** ⚡ | pandas |

---

## 吞吐量对比（calls/sec）

### 最高吞吐量场景

| Provider | 场景 | 吞吐量 | 适用场景 |
|----------|------|--------|----------|
| **numpy** | count=100, df=False, all | **9560 calls/s** | 高频小查询 |
| **pandas** | count=30000, df=True, all | **2752 calls/s** | 大数据 DataFrame |
| **python** | count=5000, df=False, all | **990 calls/s** | 中等数据 list |
| cpp_pybind | count=30000, df=False, all | **4 calls/s** ❌ | 不推荐 |

---

## 最终推荐

### 🎯 生产环境推荐配置

```python
# 默认使用 pandas（最通用最快）
history_n(..., df=True, provider='pandas')

# 如果确实需要 list[dict] 且追求极致性能：
if count < 1000:
    history_n(..., df=False, provider='numpy')  # 最快
else:
    history_n(..., df=False, provider='python')  # 稳定
```

### ⚠️ 避免使用

```python
# 永远不要这样用！
history_n(..., df=False, provider='cpp_pybind')  # 慢 200+ 倍
```

---

## 结论

1. **pandas 是性能之王**：df=True 时性能碾压所有对手，比 cpp_pybind 快 20-600 倍
2. **C++ 并非万能**：pybind11 的跨语言开销在某些场景下（list 转换）会抵消所有优势
3. **选择正确的数据结构**：
   - 需要 DataFrame → pandas
   - 需要 list 且数据量小 → numpy
   - 需要 list 且数据量大 → python
4. **cpp_pybind 仅在特定场景有用**：df=True 时性能尚可，但仍不如 pandas

---

## 附录：原始数据

完整的 benchmark 数据已保存至: `benchmark_results.json`

测试通过率: **86/86 tests passed** ✅
数据一致性: **4 个 provider 输出完全一致** ✅
