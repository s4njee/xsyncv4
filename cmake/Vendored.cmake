# Offline, hash-checked source archives. Keep full ICU filename semantics.
include(FetchContent)
include(ExternalProject)
if(XSYNC_VENDOR_BUILD_DIR)
  # The release Docker image caches dependencies separately from application code.
  set(vendor_build "${XSYNC_VENDOR_BUILD_DIR}")
  set(ZSTD_INCLUDE_DIR "${vendor_build}/_deps/zstd-src/lib")
  set(ZSTD_LIBRARY "${vendor_build}/_deps/zstd-build/lib/libzstd.a")
  set(XXHASH_INCLUDE_DIR "${vendor_build}/_deps/xxhash-src")
  set(XSYNC_ICU_INCLUDE_DIR "${vendor_build}/_deps/icu-src/source/common")
  set(XSYNC_ICU_LIBRARIES "${vendor_build}/icu-static/lib/libicuuc.a"
    "${vendor_build}/icu-static/lib/libicudata.a" ${CMAKE_DL_LIBS})
  return()
endif()
file(READ "${CMAKE_SOURCE_DIR}/third_party/manifest.json" vendor_manifest)
function(xsync_archive name filename)
  string(JSON digest GET "${vendor_manifest}" "${filename}" sha256)
  FetchContent_Declare(${name}
    URL "${CMAKE_SOURCE_DIR}/third_party/${filename}"
    URL_HASH "SHA256=${digest}"
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE ${ARGN})
  FetchContent_MakeAvailable(${name})
  set(${name}_SOURCE_DIR "${${name}_SOURCE_DIR}" PARENT_SCOPE)
endfunction()

set(ZSTD_BUILD_STATIC ON CACHE BOOL "" FORCE)
set(ZSTD_BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(ZSTD_BUILD_PROGRAMS OFF CACHE BOOL "" FORCE)
set(ZSTD_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(ZSTD_LEGACY_SUPPORT OFF CACHE BOOL "" FORCE)
set(ZSTD_DISABLE_ASM ON CACHE BOOL "" FORCE)
xsync_archive(zstd zstd-1.5.7.tar.gz SOURCE_SUBDIR build/cmake)
xsync_archive(xxhash xxhash-0.8.3.tar.gz SOURCE_SUBDIR unused)
xsync_archive(icu icu4c-77_1-src.tgz SOURCE_SUBDIR unused)

find_program(ICU_MAKE NAMES gmake make REQUIRED)
set(icu_flags "-O2")
if(APPLE)
  foreach(arch IN LISTS CMAKE_OSX_ARCHITECTURES)
    string(APPEND icu_flags " -arch ${arch}")
  endforeach()
  if(CMAKE_OSX_DEPLOYMENT_TARGET)
    string(APPEND icu_flags " -mmacosx-version-min=${CMAKE_OSX_DEPLOYMENT_TARGET}")
  endif()
endif()
set(icu_prefix "${CMAKE_BINARY_DIR}/icu-static")
ExternalProject_Add(xsync_icu
  SOURCE_DIR "${icu_SOURCE_DIR}/source"
  PREFIX "${CMAKE_BINARY_DIR}/icu-project"
  INSTALL_DIR "${icu_prefix}"
  CONFIGURE_COMMAND ${CMAKE_COMMAND} -E env
    "CC=${CMAKE_C_COMPILER}" "CXX=${CMAKE_CXX_COMPILER}"
    "CFLAGS=${icu_flags}" "CXXFLAGS=${icu_flags} -std=c++17"
    <SOURCE_DIR>/configure --prefix=<INSTALL_DIR>
    --enable-static --disable-shared --with-data-packaging=static
    --disable-tests --disable-samples --disable-extras --disable-icuio --disable-tools
  BUILD_COMMAND ${ICU_MAKE} -j8
  INSTALL_COMMAND ${ICU_MAKE} install
  BUILD_BYPRODUCTS "${icu_prefix}/lib/libicuuc.a" "${icu_prefix}/lib/libicudata.a"
  LOG_CONFIGURE ON LOG_BUILD ON LOG_INSTALL ON LOG_OUTPUT_ON_FAILURE ON)
add_library(xsync_icu_uc STATIC IMPORTED)
set_target_properties(xsync_icu_uc PROPERTIES IMPORTED_LOCATION "${icu_prefix}/lib/libicuuc.a")
add_dependencies(xsync_icu_uc xsync_icu)
add_library(xsync_icu_data STATIC IMPORTED)
set_target_properties(xsync_icu_data PROPERTIES IMPORTED_LOCATION "${icu_prefix}/lib/libicudata.a")
add_dependencies(xsync_icu_data xsync_icu)
set(ZSTD_INCLUDE_DIR "${zstd_SOURCE_DIR}/lib")
set(ZSTD_LIBRARY libzstd_static)
set(XXHASH_INCLUDE_DIR "${xxhash_SOURCE_DIR}")
set(XSYNC_ICU_LIBRARIES xsync_icu_uc xsync_icu_data ${CMAKE_DL_LIBS})
set(XSYNC_ICU_INCLUDE_DIR "${icu_SOURCE_DIR}/source/common")
