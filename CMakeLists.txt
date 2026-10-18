cmake_minimum_required(VERSION 3.18)
project(RouteWise LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(routewise_cpp
    cpp/bindings.cpp
    cpp/router_engine.cpp
)
target_include_directories(routewise_cpp PRIVATE cpp)

# Put the extension beside this file so `import routewise_cpp` works from the repository root.
set_target_properties(routewise_cpp PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}"
)
foreach(CONFIG_NAME Debug Release RelWithDebInfo MinSizeRel)
    string(TOUPPER "${CONFIG_NAME}" CONFIG_UPPER)
    set_target_properties(routewise_cpp PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY_${CONFIG_UPPER} "${CMAKE_SOURCE_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_${CONFIG_UPPER} "${CMAKE_SOURCE_DIR}"
    )
endforeach()
