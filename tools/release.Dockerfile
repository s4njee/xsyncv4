FROM alpine:3.22 AS build
RUN apk add --no-cache build-base cmake ninja git python3 linux-headers
WORKDIR /deps
COPY tools/dependencies.CMakeLists.txt ./CMakeLists.txt
COPY cmake ./cmake
COPY third_party ./third_party
RUN cmake -S . -B /deps/build -G Ninja \
    && cmake --build /deps/build --target xsync_icu libzstd_static -j8
WORKDIR /work
COPY CMakeLists.txt CMakePresets.json ./
COPY src ./src
COPY cmake ./cmake
COPY tests/filter_test.cpp tests/xattr_value_test.cpp ./tests/
COPY tools ./tools
COPY completions ./completions
ARG XSYNC_GIT_HASH
RUN cmake -S . -B /tmp/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DXSYNC_RELEASE_STATIC=ON -DXSYNC_BUILD_RELEASE_SET=OFF -DXSYNC_GIT_HASH=$XSYNC_GIT_HASH \
    -DXSYNC_VENDOR_BUILD_DIR=/deps/build \
    && cmake --build /tmp/build -j8 \
    && cmake --build /tmp/build --target xattr_value_test -j8 && /tmp/build/xattr_value_test \
    && mkdir /release && cp /tmp/build/xsync /release/xsync && /release/xsync --version
FROM scratch
COPY --from=build /release/xsync /xsync
