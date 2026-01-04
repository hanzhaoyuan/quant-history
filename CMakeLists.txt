cmake_minimum_required(VERSION 3.18)
project(quant_history CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# C++ Core library
add_subdirectory(cpp_core)

# Find Python
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Find pybind11 using Python module
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE pybind11_RESULT
)

if(NOT pybind11_RESULT EQUAL 0)
    message(FATAL_ERROR "pybind11 not found. Please install: pip install pybind11")
endif()

# Now find pybind11 with the correct path
find_package(pybind11 CONFIG REQUIRED PATHS ${pybind11_DIR} NO_DEFAULT_PATH)

# pybind11 binding
add_subdirectory(bindings/pybind11)
