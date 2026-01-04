add_library(history_core_static STATIC IMPORTED)
set_target_properties(history_core_static PROPERTIES
    IMPORTED_LOCATION "${CMAKE_BINARY_DIR}/cpp_core/Release/history_core.lib"
)

# Note: Cython extension is built via setup.py, not CMake
# This file is kept for reference but not actively used
