---
title: "xs-setup(1)"
description: "Clone the repository, build xs, install it, and make your first transfer."
manual: "xs-setup(1)"
manualName: "Getting started"
sectionNumber: "1"
---

# xs-setup(1)

<div class="manual-deck"><strong>Getting started</strong><p>Clone the repository, build xs, install it, and make your first transfer.</p></div>

## NAME {#name}

<p><strong>xs-setup</strong> — get the xsync source from GitHub, build the <code>xs</code> executable, and install it.</p>

<p>The project is <a href="https://github.com/s4njee/xsyncv4">github.com/s4njee/xsyncv4</a>. Building takes a few minutes, mostly compiling the C++ sources. Every command on this page was run on a fresh clone.</p>



## REQUIREMENTS {#requirements}

<p>Git, Python 3, a C++20 compiler (clang or gcc 12 or later), CMake 3.24 or later, Ninja, and the development files for zstd, xxHash and ICU. ICU supplies Unicode filename comparison.</p>

<aside class="manual-note"><span>CMAKE VERSION</span><p>Check with <code>cmake --version</code>. Debian 12 and Ubuntu 24.04 ship a new enough CMake; Ubuntu 22.04 ships 3.22, which is too old. There, install a current one with <code>python3 -m pip install --user cmake</code>, or from Kitware’s apt repository.</p></aside><div class="manual-table-wrap"><table><thead><tr><th scope="col">Platform</th><th scope="col">Dependencies</th></tr></thead><tbody><tr><td>macOS</td><td>Apple command-line developer tools, plus Homebrew packages</td></tr><tr><td>Debian / Ubuntu</td><td><code>build-essential</code> plus the packages below</td></tr><tr><td>Other Linux</td><td>The same tools and libraries from your distribution: a C++20 compiler, CMake, Ninja, and zstd, xxHash and ICU headers</td></tr></tbody></table></div>

## 1 · INSTALL DEPENDENCIES {#dependencies}



<div class="example-caption">macOS</div>

```sh
xcode-select --install          # Apple command-line developer tools, if not installed
brew install git cmake ninja zstd xxhash icu4c
```



<div class="example-caption">Debian / Ubuntu</div>

```sh
sudo apt update
sudo apt install git build-essential cmake ninja-build python3 libzstd-dev libxxhash-dev libicu-dev
```



## 2 · CLONE THE REPOSITORY {#clone}



<div class="example-caption">Get the source</div>

```sh
git clone https://github.com/s4njee/xsyncv4.git
cd xsyncv4
```

<p>Run the remaining commands from inside this <code>xsyncv4</code> directory. The repository is named <code>xsyncv4</code>; the program it builds is called <code>xs</code>.</p>



## 3 · BUILD {#build}



<div class="example-caption">Configure, compile, and check the result</div>

```sh
cmake -S . -B build -G Ninja
cmake --build build
build/xs --version
```

<p>The executable is <code>build/xs</code>. Its version line includes the Git revision it was built from, with <code>-dirty</code> if the sources were modified.</p>



<div class="example-caption">Optional: a quick self-test (prints “N checks, 0 failures”)</div>

```sh
cmake --build build --target filter_test
build/filter_test
```



## 4 · INSTALL {#install}



<div class="example-caption">Install into ~/.local</div>

```sh
cmake --install build --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
xs --version
```

<p>This installs <code>bin/xs</code>, the manpage (<code>man xs</code>) generated from its own help, and zsh completion. Add the <code>PATH</code> line to your shell configuration to keep it. To install for all users, use <code>sudo cmake --install build</code>, which installs under <code>/usr/local</code>.</p>



<div class="example-caption">zsh completion — put before your existing compinit setup</div>

```sh
fpath=("$HOME/.local/share/zsh/site-functions" $fpath)
autoload -Uz compinit
compinit
```



## 5 · FIRST TRANSFER {#first-transfer}



<div class="example-caption">Copy source contents into the destination</div>

```sh
xs -aP src/ dst/
```

<p>Replace both paths with your own. Progress is automatic when stderr is a terminal; <code>-P</code> also keeps partial data for a later retry. For remote transfers, the other machine needs <code>xs</code> too. See <a href="install.html#remote">remote install</a>, or let it <a href="compatibility.html#fallback">fall back to rsync</a>.</p>



## UPDATING {#updating}



<div class="example-caption">Pull the latest source and reinstall</div>

```sh
cd xsyncv4
git pull
cmake --build build
cmake --install build --prefix "$HOME/.local"
```

<p><code>cmake --build</code> recompiles only what changed. If a build fails after a large update, start fresh with <code>rm -rf build</code> and repeat step 3.</p>



## RELEASE BUILDS {#releases}



<div class="example-caption">Build static release binaries from the same checkout</div>

```sh
cmake --preset release-static
cmake --build --preset release-static
```

<p>The release flow produces Linux amd64/arm64 binaries and a macOS universal binary in <code>dist/</code>. It also needs Docker and GNU make. A macOS host is needed for the macOS output; a Linux host can build the Linux outputs. See <a href="install.html#releases">release binaries</a>.</p>



