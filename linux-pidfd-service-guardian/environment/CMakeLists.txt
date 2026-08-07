cmake_minimum_required(VERSION 3.25)
project(guardian LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra -Wpedantic -Werror -O2)

add_library(guardian_core
    src/common.cpp
    src/config.cpp
    src/journal.cpp
    src/process.cpp
    src/control.cpp
    src/supervisor.cpp
)
target_include_directories(guardian_core PUBLIC include)

add_executable(guardian src/main.cpp)
target_link_libraries(guardian PRIVATE guardian_core)

add_executable(guardianctl src/guardianctl.cpp)
target_link_libraries(guardianctl PRIVATE guardian_core)

add_executable(guardian-worker src/worker.cpp)

install(TARGETS guardian guardianctl guardian-worker RUNTIME DESTINATION bin)
