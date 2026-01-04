"""Setup script for quant-history project"""
from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import numpy as np
import os
import sys

# Determine build directory for lib location
build_dir = "build"
if sys.platform == "win32":
    lib_dir = os.path.join(build_dir, "cpp_core", "Release")
    lib_dir_debug = os.path.join(build_dir, "cpp_core", "Debug")
    library_name = "history_core"
else:
    lib_dir = os.path.join(build_dir, "cpp_core")
    library_name = "history_core"

# Cython extension for cpp_cython_provider
# Note: This is optional and only built if Cython extension is needed
extensions = []

# Check if C++ library exists
cpp_lib_exists = os.path.exists(lib_dir) or (
    sys.platform == "win32" and os.path.exists(lib_dir_debug)
)

if cpp_lib_exists:
    cython_ext = Extension(
        "providers._cpp_cython",
        sources=["bindings/cython/cpp_cython_provider.pyx"],
        include_dirs=[
            "cpp_core/include",
            np.get_include()
        ],
        libraries=[library_name],
        library_dirs=[lib_dir, lib_dir_debug] if sys.platform == "win32" else [lib_dir],
        language="c++",
        extra_compile_args=["/std:c++17"] if sys.platform == "win32" else ["-std=c++17"],
    )
    extensions.append(cython_ext)
else:
    print("WARNING: C++ library not found. Skipping Cython extension build.")
    print(f"Please run CMake build first to generate the library in {lib_dir}")

setup(
    name="quant-history",
    version="0.1.0",
    description="Benchmark project for history_n minute bar query interface",
    author="Claude",
    packages=find_packages(include=["providers", "benchmark", "tests"]),
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}) if extensions else [],
    install_requires=[
        "numpy>=1.23",
        "pandas>=1.5",
        "pytest>=7.0",
    ],
    python_requires=">=3.10",
)
