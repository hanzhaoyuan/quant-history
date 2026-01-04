pybind11_add_module(_cpp_history_core binding.cpp)

target_link_libraries(_cpp_history_core PRIVATE history_core)

# Set output directory to project root for easier import
set_target_properties(_cpp_history_core PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}
)
