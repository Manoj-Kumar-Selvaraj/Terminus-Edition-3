cmake_minimum_required(VERSION 3.20)
project(sovereign_lb_dataplane LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_executable(lb-dataplane
  src/main.cpp src/json.cpp src/protocol.cpp src/snapshot.cpp src/eligibility.cpp
  src/selector.cpp src/connection.cpp src/proxy.cpp src/health.cpp src/prober.cpp
  src/drain.cpp src/checkpoint.cpp src/sha256.cpp src/status.cpp src/control.cpp)
target_include_directories(lb-dataplane PRIVATE include)
target_compile_options(lb-dataplane PRIVATE -Wall -Wextra -Wpedantic -Wconversion)
target_link_libraries(lb-dataplane PRIVATE pthread)
install(TARGETS lb-dataplane RUNTIME DESTINATION bin)