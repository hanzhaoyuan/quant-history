cmake_minimum_required(VERSION 3.18)
project(quant_history CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# C++ Core library
add_subdirectory(cpp_core)

# Find Python and pybind11
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# pybind11 binding
add_subdirectory(bindings/pybind11)
