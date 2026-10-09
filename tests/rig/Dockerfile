FROM debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build libzstd-dev libxxhash-dev libicu-dev python3 rsync \
    openssh-server openssh-client procps iproute2 ca-certificates sudo zsh mandoc \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
COPY CMakeLists.txt ./
COPY src ./src
COPY tests ./tests
COPY tools ./tools
COPY completions ./completions
RUN cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build && cp build/xsync /usr/local/bin/xsync \
    && c++ -std=c++20 -shared -fPIC tests/fault_io.cpp -ldl -o build/fault_io.so
RUN mkdir -p /run/sshd /root/.ssh && ssh-keygen -A \
    && printf '\nPermitRootLogin prohibit-password\nPasswordAuthentication no\n' >> /etc/ssh/sshd_config
CMD ["sleep", "infinity"]
