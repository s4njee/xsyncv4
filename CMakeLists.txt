cmake_minimum_required(VERSION 3.24)
project(xsync LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE ON)

# Linux release builds must use a musl compiler (the release Dockerfile does).
option(XSYNC_RELEASE_STATIC "Vendor and statically link every third-party dependency" OFF)
option(XSYNC_BUILD_RELEASE_SET "Build Linux amd64/arm64 and macOS universal artifacts" OFF)
set(XSYNC_GIT_HASH "" CACHE STRING "Source revision (for exported trees without .git)")
if(NOT XSYNC_GIT_HASH)
  execute_process(COMMAND git rev-parse --short=12 HEAD WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    OUTPUT_VARIABLE XSYNC_GIT_HASH OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
  if(NOT XSYNC_GIT_HASH)
    set(XSYNC_GIT_HASH "unknown")
  endif()
endif()
find_package(Threads REQUIRED)
if(XSYNC_RELEASE_STATIC)
  include(cmake/Vendored.cmake)
else()
# zstd (static if available) and header-only xxhash for development builds.
find_path(ZSTD_INCLUDE_DIR zstd.h HINTS /opt/homebrew/include /usr/local/include)
find_library(ZSTD_LIBRARY NAMES libzstd.a zstd HINTS /opt/homebrew/lib /usr/local/lib)
find_path(XXHASH_INCLUDE_DIR xxhash.h HINTS /opt/homebrew/include /usr/local/include)
if(NOT ZSTD_INCLUDE_DIR OR NOT ZSTD_LIBRARY OR NOT XXHASH_INCLUDE_DIR)
  message(FATAL_ERROR "xsync needs zstd and xxhash (brew install zstd xxhash / apt install libzstd-dev libxxhash-dev)")
endif()
if(APPLE AND NOT ICU_ROOT)
  if(EXISTS /opt/homebrew/opt/icu4c)
    set(ICU_ROOT /opt/homebrew/opt/icu4c)
  elseif(EXISTS /usr/local/opt/icu4c)
    set(ICU_ROOT /usr/local/opt/icu4c)
  endif()
endif()
find_package(ICU REQUIRED COMPONENTS uc)
set(XSYNC_ICU_LIBRARIES ICU::uc)
endif()

add_executable(xsync
  src/main.cpp src/util.cpp src/progress.cpp src/fs.cpp src/filter.cpp
  src/local.cpp src/remote.cpp src/names.cpp src/destination.cpp src/fallback.cpp src/transport.cpp src/install.cpp)
target_include_directories(xsync PRIVATE src ${ZSTD_INCLUDE_DIR} ${XXHASH_INCLUDE_DIR} ${XSYNC_ICU_INCLUDE_DIR})
target_link_libraries(xsync PRIVATE ${ZSTD_LIBRARY} Threads::Threads ${XSYNC_ICU_LIBRARIES})
target_compile_definitions(xsync PRIVATE XSYNC_GIT_HASH="${XSYNC_GIT_HASH}")
if(XSYNC_RELEASE_STATIC)
  target_compile_definitions(xsync PRIVATE U_STATIC_IMPLEMENTATION)
  if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_options(xsync PRIVATE -static)
  endif()
endif()
target_compile_options(xsync PRIVATE -Wall -Wextra -Wno-unused-parameter)

if(XSYNC_BUILD_RELEASE_SET)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_custom_target(release-set ALL
    COMMAND ${Python3_EXECUTABLE} "${CMAKE_SOURCE_DIR}/tools/release.py"
      --native "$<TARGET_FILE:xsync>" --revision "${XSYNC_GIT_HASH}"
    DEPENDS xsync USES_TERMINAL)
endif()

add_executable(filter_test EXCLUDE_FROM_ALL tests/filter_test.cpp src/filter.cpp)
target_include_directories(filter_test PRIVATE src)
