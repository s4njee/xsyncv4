---
title: "xsync-setup(1)"
description: "Build the binary, install it locally, and make your first transfer."
manual: "xsync-setup(1)"
manualName: "Getting started"
sectionNumber: "1"
---

# xsync-setup(1)

<div class="manual-deck"><strong>Getting started</strong><p>Build the binary, install it locally, and make your first transfer.</p></div>

## NAME {#name}

<p><strong>xsync-setup</strong> — build and install xsync from a source checkout.</p>



## REQUIREMENTS {#requirements}

<p>Python 3, a C++20 compiler, CMake, zstd, xxHash, and ICU are required. Ninja is used by the build examples. Run the commands below from the xsync source directory.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Platform</th><th scope="col">Dependencies</th></tr></thead><tbody><tr><td>macOS</td><td>Apple command-line developer tools; Homebrew libraries</td></tr><tr><td>Linux</td><td>C++20 compiler; development packages for zstd, xxHash, and ICU</td></tr></tbody></table></div>

## BUILD {#build}



<div class="example-caption">macOS dependencies</div>

```sh
brew install cmake ninja zstd xxhash icu4c
```



<div class="example-caption">Debian / Ubuntu dependencies</div>

```sh
sudo apt install build-essential cmake ninja-build python3 libzstd-dev libxxhash-dev libicu-dev
```



<div class="example-caption">Build and inspect the binary</div>

```sh
cmake -S . -B build -G Ninja
cmake --build build
build/xsync --version
```



## INSTALL {#install}



<div class="example-caption">Local installation</div>

```sh
cmake --install build --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
```

<p>This installs the executable, the generated manpage, and zsh completion. Add the PATH setting to your shell configuration if you want it to persist.</p>



<div class="example-caption">zsh completion — put before your existing compinit setup</div>

```sh
fpath=("$HOME/.local/share/zsh/site-functions" $fpath)
autoload -Uz compinit
compinit
```



## FIRST TRANSFER {#first-transfer}



<div class="example-caption">Copy source contents into the destination</div>

```sh
xsync -aP src/ dst/
```

<p>Replace both paths with your own. Progress is automatic when stderr is a terminal; <code>-P</code> also preserves partial transfer data for a later retry.</p>



## RELEASE BUILDS {#releases}



<div class="example-caption">Build release artifacts</div>

```sh
cmake --preset release-static
cmake --build --preset release-static
```

<p>The release flow produces Linux amd64/arm64 binaries and a macOS universal binary. A macOS host is needed for the macOS output; the documented macOS build also requires Docker, GNU make, and the toolchain. A Linux host can build Linux outputs.</p>



