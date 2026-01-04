@echo off
REM Run benchmark with correctness checks
echo ========================================
echo Running quant-history benchmark
echo ========================================
echo.

REM Save current directory and change to project root
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

REM Activate conda environment
call conda.bat activate quant-history
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate quant-history environment
    echo Please run scripts\build.bat first
    exit /b 1
)

echo Step 1: Running correctness tests...
echo.
pytest tests/ -v --tb=short
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo ERROR: Correctness tests failed!
    echo ========================================
    echo.
    echo Benchmark will not run until all tests pass.
    echo Please fix the issues above and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo All correctness tests passed!
echo ========================================
echo.
echo Step 2: Running performance benchmark...
echo.

python benchmark/benchmark.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Benchmark failed
    exit /b 1
)

echo.
echo ========================================
echo Benchmark complete!
echo ========================================
echo.
echo Results saved to: benchmark_results.json
echo.
pause
