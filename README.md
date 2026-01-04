# history_n 分钟K线接口性能评估工程

本项目是一个可重复、可对比、可自动化的 benchmark 工程，用于评估典型行情查询接口 `history_n` 在不同实现路径下的性能差异。

## 项目概述

本项目对比以下 5 种实现方式：

1. **C++ Core + pybind11 绑定**（目标组，推荐）
2. **C++ Core + Cython 绑定**（目标组）
3. **纯 Python 实现**（对照组）
4. **NumPy 列式实现**（对照组）
5. **pandas DataFrame 实现**（对照组）

### 重要声明

- ⚠️ 这是 benchmark 工程，**不是**生产行情系统
- 数据为 mock 分钟K，但保证确定性、可复现、行为完全一致
- 测试聚焦：查询逻辑、跨语言绑定开销、输出包装性能
- 不测试数据生成成本（数据预先生成并缓存）

## 技术栈

- **语言**: C++17, Python 3.10
- **构建系统**: CMake 3.18+
- **编译器**: MSVC (Visual Studio 2019/2022)
- **依赖**: NumPy, pandas, pybind11, Cython, pytest
- **环境**: Windows + conda

## 快速开始

### 1. 创建 conda 环境

```bash
conda env create -f environment.yml
conda activate quant-history
```

### 2. 构建项目

```bash
# Windows
scripts\build.bat
```

该脚本会：
- 创建/更新 conda 环境
- 使用 CMake 构建 C++ Core 和 pybind11 绑定
- 使用 setup.py 构建 Cython 扩展

### 3. 运行测试

```bash
pytest tests/ -v
```

### 4. 运行 benchmark

```bash
python benchmark/benchmark.py

# 或使用一体化脚本（含测试+benchmark）
scripts\run_benchmark.bat
```

## API 规范

### 接口签名

```python
from providers import history_n

history_n(
    symbol: str,                 # 股票代码（仅支持单标的）
    frequency: str,              # '60s' 或 '1m'（仅支持分钟线）
    count: int,                  # 返回条数（最大33000）
    end_time=None,              # None | str | datetime
    fields=None,                # None 或逗号分隔字段名
    skip_suspended=True,        # V1保留参数（忽略）
    fill_missing=None,          # V1保留参数（忽略）
    adjust='none',              # V1保留参数（忽略）
    adjust_end_time='',         # V1保留参数（忽略）
    df=False,                   # False: list[dict], True: DataFrame
    provider='cpp_pybind'       # 实现版本
) -> Union[List[Dict], pd.DataFrame]
```

### Provider 选项

- `cpp_pybind`: C++ + pybind11（默认，推荐）
- `cpp_cython`: C++ + Cython
- `python`: 纯 Python baseline
- `numpy`: NumPy 列式 baseline
- `pandas`: pandas DataFrame baseline

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | str | 股票代码 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| eob | datetime | Bar 结束时间（UTC+8） |

### OHLC 约束

```
low <= min(open, close) <= max(open, close) <= high
```

### 时间轴规则（A股简化模型）

- **交易日**: 周一~周五（不考虑法定节假日）
- **交易时段**:
  - 上午：09:30-11:30（120根K线，eob: 09:31-11:30）
  - 下午：13:00-15:00（120根K线，eob: 13:01-15:00）
- **数据覆盖**: 100个交易日（约24,000根K线/标的）

### end_time 行为

| 输入 | 行为 |
|------|------|
| `None` | 使用当前真实时间（非回测时间） |
| `str` | 格式：`%Y-%m-%d %H:%M:%S`<br>允许个位数：`2017-7-30 20:0:20` |
| `datetime` | 直接使用（naive时区视为UTC+8） |
| 非法日期 | 抛出 `ValueError` |

**错误示例**:
```python
# 非法日期
history_n(..., end_time='2020-10-40 15:30:00')
# 抛出: ValueError: Can't parse string as time: 2020-10-40 15:30:00
```

### count 行为

- `count <= 0`: 返回空
- `count > 33000`: 自动截断为 33000
- `count > 可用数据`: 返回全部可用数据

### fields 过滤

- `fields=None`: 返回所有字段
- `fields='a,b,c'`: 仅返回指定字段
- 无效字段自动忽略
- `symbol` 和 `eob` 强制包含

**示例**:
```python
data = history_n('000001.SH', '1m', 100,
                 fields='open,close',  # 实际返回: symbol, open, close, eob
                 df=True)
```

### 返回格式

#### df=False（list[dict]）
```python
[
    {'symbol': '000001.SH', 'open': 100.5, 'high': 101.0,
     'low': 100.2, 'close': 100.8, 'eob': datetime(2024,1,2,9,31,0,tzinfo=UTC+8)},
    ...
]
```

#### df=True（DataFrame）
```python
   symbol    open    high     low   close                 eob
0  000001.SH  100.5   101.0   100.2   100.8  2024-01-02 09:31:00+08:00
1  000001.SH  100.8   101.2   100.5   101.0  2024-01-02 09:32:00+08:00
...
```

## 使用示例

```python
from providers import history_n

# 1. 获取最新100根K线
data = history_n('000001.SH', '1m', 100)

# 2. 指定结束时间
data = history_n('000001.SH', '1m', 1000,
                 end_time='2024-01-15 14:30:00')

# 3. 返回 DataFrame
df = history_n('000001.SH', '1m', 500, df=True)

# 4. 筛选字段
df = history_n('000001.SH', '1m', 500,
               fields='symbol,open,close,eob',
               df=True)

# 5. 使用不同 provider
data_cpp = history_n('000001.SH', '1m', 100, provider='cpp_pybind')
data_py = history_n('000001.SH', '1m', 100, provider='python')
data_np = history_n('000001.SH', '1m', 100, provider='numpy')
data_pd = history_n('000001.SH', '1m', 100, provider='pandas')
data_cy = history_n('000001.SH', '1m', 100, provider='cpp_cython')
```

## V1 限制与保留参数

### 仅支持分钟K

- ✅ 支持: `'60s'`, `'1m'`
- ❌ 不支持: tick, 日K, 周K等
- 非法 frequency → `ValueError`

### 仅支持单标的

- ✅ 支持: `'000001.SH'`
- ❌ 不支持: `['000001.SH', '000002.SH']`

### 保留但忽略的参数

以下参数接受但不实现真实逻辑：
- `skip_suspended`
- `fill_missing`
- `adjust`
- `adjust_end_time`

## Benchmark 设计

### 测试矩阵

测试维度（笛卡尔积）：

| 维度 | 取值 |
|------|------|
| provider | cpp_pybind, cpp_cython, python, numpy, pandas |
| count | 100, 5000, 30000 |
| fields | None, 指定字段 |
| df | False, True |
| end_time | 固定时间（确保可复现） |

### 数据路径分类

| 路径 | df | 说明 |
|------|-------|------|
| A | False | NumPy-only（C++：列式数据） |
| B | True | NumPy → DataFrame |
| C | True | list[dict] → DataFrame |

### 输出指标

- 平均耗时（mean）
- 中位数（P50）
- 95分位（P95）
- 99分位（P99）
- 吞吐量（calls/sec）

### 运行方式

```bash
python benchmark/benchmark.py
```

结果保存至 `benchmark_results.json`

## 项目结构

```
quant-history/
├── environment.yml          # conda 环境配置
├── CMakeLists.txt           # 顶层 CMake
├── setup.py                 # Python 包构建
├── README.md                # 本文档
├── .gitignore
│
├── cpp_core/                # C++ 核心实现
│   ├── include/
│   │   ├── bar.h           # 数据结构
│   │   ├── market_data.h   # 数据生成与缓存
│   │   └── history_provider.h  # 查询接口
│   └── src/
│       ├── bar.cpp
│       ├── market_data.cpp
│       └── history_provider.cpp
│
├── bindings/                # Python 绑定
│   ├── pybind11/
│   │   ├── binding.cpp
│   │   └── CMakeLists.txt
│   └── cython/
│       ├── cpp_cython_provider.pyx
│       └── cpp_cython_provider.pxd
│
├── providers/               # Python 统一接口
│   ├── __init__.py         # 统一入口
│   ├── utils.py            # 时间工具等
│   ├── cpp_pybind_provider.py
│   ├── cpp_cython_provider.py
│   ├── python_provider.py
│   ├── numpy_provider.py
│   └── pandas_provider.py
│
├── benchmark/               # 性能测试
│   ├── benchmark.py
│   └── utils.py
│
├── tests/                   # 单元测试
│   ├── test_correctness.py
│   └── test_edge_cases.py
│
└── scripts/                 # 构建脚本
    ├── build.bat
    └── run_benchmark.bat
```

## 正确性保证

### 确定性数据生成

- 使用 `std::hash<std::string>(symbol)` 作为种子
- 禁止使用 Python `hash()`（随机盐）
- 同一 symbol 的数据在所有 provider 中完全一致

### 跨版本一致性测试

```bash
pytest tests/test_correctness.py -v
```

测试内容：
- 五个版本返回相同行数
- eob 时间戳完全一致
- OHLC 数值一致（允许浮点误差 < 1e-10）
- df=True 和 df=False 内容一致

### 边界测试

```bash
pytest tests/test_edge_cases.py -v
```

测试内容：
- 非法 frequency → ValueError
- 非法 end_time → ValueError with message
- count > 33000 → 截断
- 无效 symbol → 空结果
- end_time 早于数据 → 空结果

## 开发说明

### 添加新 provider

1. 在 `providers/` 创建 `your_provider.py`
2. 实现 `history_n()` 函数（签名与现有一致）
3. 在 `providers/__init__.py` 中注册
4. 在 `tests/` 和 `benchmark/` 中添加到 `PROVIDERS` 列表

### 修改 C++ Core

1. 修改 `cpp_core/` 中的源文件
2. 重新构建：
   ```bash
   cd build
   cmake --build . --config Release
   cd ..
   ```
3. 重新构建 Cython（如需要）：
   ```bash
   python setup.py build_ext --inplace
   ```

### 添加测试用例

在 `tests/test_correctness.py` 或 `tests/test_edge_cases.py` 中添加新的测试函数。

## 常见问题

### Q: pybind11 扩展导入失败

**A**: 确保已运行构建脚本：
```bash
scripts\build.bat
```

检查是否生成了 `_cpp_history_core.*.pyd` 文件。

### Q: Cython 扩展构建失败

**A**: 确保 C++ Core 已先构建：
```bash
cd build
cmake --build . --config Release
cd ..
python setup.py build_ext --inplace
```

### Q: 测试失败：不同 provider 结果不一致

**A**: 检查数据生成逻辑中的种子设置是否一致。所有 provider 必须使用相同的确定性种子。

### Q: end_time=None 时结果不可复现

**A**: 这是预期行为。`end_time=None` 使用当前真实时间，每次运行结果不同。benchmark 中使用固定 end_time。

### Q: Visual Studio 版本问题

**A**: 支持 VS 2019 或 2022。如果两者都未安装，请安装至少一个，并确保包含 C++ 工具。

## 性能优化要点

### C++ Core

- 数据预生成并缓存（避免每次查询重新生成）
- 使用二分查找定位 end_time
- 列式返回（零拷贝友好）

### pybind11/Cython

- 零拷贝转换为 NumPy arrays
- 最小化 Python/C++ 边界跨越

### Python/NumPy

- NumPy 使用 `searchsorted` 二分查找
- 数组切片高效

## 许可证

本项目为 Benchmark 评估工程，仅用于性能测试和教学目的。

## 贡献

本项目为内部 benchmark 工程，不接受外部贡献。

## 联系方式

如有问题，请在项目仓库提交 Issue。
