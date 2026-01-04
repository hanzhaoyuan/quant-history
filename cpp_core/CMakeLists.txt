add_library(history_core STATIC
    src/bar.cpp
    src/market_data.cpp
    src/history_provider.cpp
)

target_include_directories(history_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Ensure C++17
target_compile_features(history_core PUBLIC cxx_std_17)
