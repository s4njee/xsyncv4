cmake_minimum_required(VERSION 3.20)
project(xsync CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)

# zstd (static if available, so the binary is self-contained) and header-only xxhash.
find_path(ZSTD_INCLUDE_DIR zstd.h HINTS /opt/homebrew/include /usr/local/include)
find_library(ZSTD_LIBRARY NAMES libzstd.a zstd HINTS /opt/homebrew/lib /usr/local/lib)
find_path(XXHASH_INCLUDE_DIR xxhash.h HINTS /opt/homebrew/include /usr/local/include)
if(NOT ZSTD_INCLUDE_DIR OR NOT ZSTD_LIBRARY OR NOT XXHASH_INCLUDE_DIR)
  message(FATAL_ERROR "xsync needs zstd and xxhash (brew install zstd xxhash / apt install libzstd-dev libxxhash-dev)")
endif()
find_package(Threads REQUIRED)
if(APPLE AND NOT ICU_ROOT)
  if(EXISTS /opt/homebrew/opt/icu4c)
    set(ICU_ROOT /opt/homebrew/opt/icu4c)
  elseif(EXISTS /usr/local/opt/icu4c)
    set(ICU_ROOT /usr/local/opt/icu4c)
  endif()
endif()
find_package(ICU REQUIRED COMPONENTS uc)

add_executable(xsync
  src/main.cpp src/util.cpp src/progress.cpp src/fs.cpp src/filter.cpp
  src/local.cpp src/remote.cpp src/names.cpp src/destination.cpp src/fallback.cpp)
target_include_directories(xsync PRIVATE src ${ZSTD_INCLUDE_DIR} ${XXHASH_INCLUDE_DIR})
target_link_libraries(xsync PRIVATE ${ZSTD_LIBRARY} Threads::Threads ICU::uc)
target_compile_options(xsync PRIVATE -Wall -Wextra -Wno-unused-parameter)

add_executable(filter_test EXCLUDE_FROM_ALL tests/filter_test.cpp src/filter.cpp)
target_include_directories(filter_test PRIVATE src)
