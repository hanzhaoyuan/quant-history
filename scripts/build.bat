@echo off
REM Build script for quant-history project on Windows
REM This script builds both C++ core with pybind11 and Cython extensions

echo ========================================
echo Building quant-history benchmark project
echo ========================================
echo.

REM Save current directory and change to project root
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

REM Set Visual Studio environment (custom location)
echo Setting up Visual Studio environment...
if exist "D:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" (
    call "D:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 >nul
    echo Visual Studio 2026 environment loaded
) else (
    echo WARNING: Visual Studio not found at custom location
    echo Trying to find VS in standard locations...
    where cl >nul 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: No C++ compiler found
        echo Please ensure Visual Studio is installed
        exit /b 1
    )
)

echo.
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

REM Use Ninja generator (works with VS command prompt environment)
echo Running CMake configuration with Ninja...
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
if %errorlevel% neq 0 (
    echo ERROR: CMake configuration failed
    echo Make sure Ninja is installed: conda install ninja
    cd ..
    exit /b 1
)

echo Building with Ninja...
cmake --build .
if %errorlevel% neq 0 (
    echo ERROR: C++ build failed
    cd ..
    exit /b 1
)

cd ..

echo.
echo Step 4: Copying pybind11 extension to project root...
if exist build\_cpp_history_core.*.pyd (
    copy build\_cpp_history_core.*.pyd . >nul
    echo pybind11 extension copied
) else (
    echo WARNING: pybind11 extension not found
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
