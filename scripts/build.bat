@echo off
REM Build script for quant-history project on Windows
REM This script builds both C++ core with pybind11 and Cython extensions

echo ========================================
echo Building quant-history benchmark project
echo ========================================
echo.

REM Check if conda environment is activated
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: conda not found in PATH
    echo Please install Anaconda/Miniconda or ensure it's in your PATH
    exit /b 1
)

echo Step 1: Creating/updating conda environment...
call conda env create -f environment.yml 2>nul
if %errorlevel% neq 0 (
    echo Environment already exists, updating...
    call conda env update -f environment.yml --prune
)

echo.
echo Step 2: Activating conda environment...
call conda activate quant-history
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate quant-history environment
    exit /b 1
)

echo.
echo Step 3: Building C++ Core with pybind11...
if not exist build mkdir build
cd build

REM Detect Visual Studio version
cmake .. -G "Visual Studio 17 2022" -A x64 >nul 2>nul
if %errorlevel% neq 0 (
    echo Visual Studio 2022 not found, trying 2019...
    cmake .. -G "Visual Studio 16 2019" -A x64
    if %errorlevel% neq 0 (
        echo ERROR: No compatible Visual Studio found
        echo Please install Visual Studio 2019 or 2022 with C++ tools
        cd ..
        exit /b 1
    )
)

echo Building Release configuration...
cmake --build . --config Release
if %errorlevel% neq 0 (
    echo ERROR: C++ build failed
    cd ..
    exit /b 1
)

cd ..

echo.
echo Step 4: Copying pybind11 extension to project root...
if exist build\Release\_cpp_history_core.*.pyd (
    copy build\Release\_cpp_history_core.*.pyd . >nul
) else if exist build\_cpp_history_core.*.pyd (
    copy build\_cpp_history_core.*.pyd . >nul
) else (
    echo WARNING: pybind11 extension not found in expected location
)

echo.
echo Step 5: Building Cython extension...
python setup.py build_ext --inplace
if %errorlevel% neq 0 (
    echo WARNING: Cython build failed (optional)
    echo You can still use cpp_pybind, python, and numpy providers
) else (
    echo Cython extension built successfully
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Available providers:
echo   - cpp_pybind  : C++ + pybind11 (recommended)
echo   - cpp_cython  : C++ + Cython
echo   - python      : Pure Python baseline
echo   - numpy       : NumPy columnar baseline
echo.
echo Next steps:
echo   1. Run tests:       pytest tests/ -v
echo   2. Run benchmark:   python benchmark/benchmark.py
echo   3. Or use script:   scripts\run_benchmark.bat
echo.
pause
