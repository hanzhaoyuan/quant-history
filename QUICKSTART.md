# 快速启动指南

## 第一次使用

### 步骤 1: 构建项目
```bash
# 在项目根目录下运行
scripts\build.bat
```

这会：
1. 创建 conda 环境 `quant-history`
2. 安装所有依赖（NumPy, pandas, pybind11, Cython等）
3. 编译 C++ Core
4. 构建 pybind11 和 Cython 扩展

### 步骤 2: 运行测试
```bash
# 激活环境
conda activate quant-history

# 运行所有测试
pytest tests/ -v
```

### 步骤 3: 运行 benchmark
```bash
# 方式 1: 直接运行
python benchmark/benchmark.py

# 方式 2: 使用脚本（会先运行测试）
scripts\run_benchmark.bat
```

## 日常使用

### 交互式使用

```python
# 启动 Python
conda activate quant-history
python

# 导入并使用
from providers import history_n

# 使用 C++ + pybind11（最快）
data = history_n('000001.SH', '1m', 100, provider='cpp_pybind')

# 使用纯 Python（对照）
data = history_n('000001.SH', '1m', 100, provider='python')

# 使用 NumPy（对照）
data = history_n('000001.SH', '1m', 100, provider='numpy')

# 使用 pandas（对照）
data = history_n('000001.SH', '1m', 100, provider='pandas')

# 使用 C++ + Cython
data = history_n('000001.SH', '1m', 100, provider='cpp_cython')

# 返回 DataFrame
df = history_n('000001.SH', '1m', 500, df=True, provider='cpp_pybind')
print(df.head())
```

### 仅测试某个 provider

```bash
pytest tests/test_correctness.py::TestBasicQuery::test_basic_query_list[cpp_pybind] -v
```

### benchmark 特定场景

编辑 `benchmark/benchmark.py` 中的 `TEST_MATRIX` 来自定义测试维度。

## 验收检查清单

运行以下命令确保一切正常：

```bash
# 1. 测试 Python baseline（总是可用）
python -c "from providers import history_n; print(len(history_n('000001.SH', '1m', 100, provider='python')))"
# 期望输出: 100

# 2. 测试 NumPy baseline（总是可用）
python -c "from providers import history_n; print(len(history_n('000001.SH', '1m', 100, provider='numpy')))"
# 期望输出: 100

# 3. 测试 pandas baseline（总是可用）
python -c "from providers import history_n; print(len(history_n('000001.SH', '1m', 100, provider='pandas')))"
# 期望输出: 100

# 4. 测试 C++ + pybind11（需要构建）
python -c "from providers import history_n; print(len(history_n('000001.SH', '1m', 100, provider='cpp_pybind')))"
# 期望输出: 100

# 5. 测试 C++ + Cython（需要构建）
python -c "from providers import history_n; print(len(history_n('000001.SH', '1m', 100, provider='cpp_cython')))"
# 期望输出: 100

# 6. 运行完整测试
pytest tests/ -v
# 期望: 所有测试通过

# 7. 运行 benchmark
python benchmark/benchmark.py
# 期望: 生成 benchmark_results.json
```

## 故障排查

### 问题: conda 命令未找到
**解决**: 安装 Anaconda 或 Miniconda，并确保添加到 PATH

### 问题: Visual Studio 未找到
**解决**: 安装 Visual Studio 2019 或 2022，并勾选 "Desktop development with C++"

### 问题: C++ 编译失败
**解决**:
1. 检查是否安装了 Visual Studio C++ 工具
2. 尝试手动运行 CMake：
   ```bash
   mkdir build
   cd build
   cmake .. -G "Visual Studio 17 2022" -A x64
   cmake --build . --config Release
   ```

### 问题: pybind11 导入失败
**解决**:
1. 确保 C++ Core 已构建
2. 检查是否有 `_cpp_history_core.*.pyd` 文件
3. 重新运行 `scripts\build.bat`

### 问题: 测试失败 - provider 结果不一致
**解决**: 这可能是 bug！请检查数据生成的种子逻辑是否一致。

## 下一步

- 查看 `benchmark_results.json` 了解性能数据
- 修改 `benchmark/benchmark.py` 自定义测试场景
- 阅读 `README.md` 了解完整 API 文档
