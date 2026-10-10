---
title: "xs-install(1)"
description: "Install locally, build static release binaries, and put the helper on the machines you sync with."
manual: "xs-install(1)"
manualName: "Install & releases"
sectionNumber: "1"
---

# xs-install(1)

<div class="manual-deck"><strong>Install &amp; releases</strong><p>Install locally, build static release binaries, and put the helper on the machines you sync with.</p></div>

## LOCAL INSTALL {#local}

<div class="example-caption">From a built checkout (see <a href="getting-started.html#build">getting started</a>)</div>

```sh
cmake --install build --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
```

<p>This installs <code>xs</code>, a manpage generated from its own <code>--help</code>, and zsh completion. The completion builds on zsh’s rsync completion. For zsh, add <code>fpath=("$HOME/.local/share/zsh/site-functions" $fpath)</code> before <code>compinit</code> in <code>.zshrc</code>. Release binaries already in <code>dist/</code> are installed too, under <code>share/xs/releases/</code>, for <a href="#remote">remote install</a>.</p>


## HOMEBREW (LOCAL TAP) {#homebrew}

<div class="example-caption">A formula for this checkout, in a tap on your machine</div>

```sh
python3 tools/package.py
brew tap-new xs/local
cp dist/homebrew/Formula/xs.rb "$(brew --repository xs/local)/Formula/"
brew install --build-from-source xs/local/xs
brew test xs/local/xs
```

<p>The formula points at a source archive of this checkout and builds the vendored, hash-checked dependencies. No public tap is published. If the tap already exists, skip <code>tap-new</code>, and use <code>brew reinstall</code> to replace an installed copy.</p>


## RELEASE BINARIES {#releases}

<div class="example-caption">Static binaries for every supported target</div>

```sh
cmake --preset release-static
cmake --build --preset release-static
```

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Output</th><th scope="col">Target</th><th scope="col">Links against</th></tr></thead><tbody>
<tr><td><code>dist/xs-linux-amd64</code></td><td>Linux x86-64</td><td>nothing: fully static, built with musl</td></tr>
<tr><td><code>dist/xs-linux-arm64</code></td><td>Linux ARM64, such as a Raspberry Pi 4 or 5 on a 64-bit OS</td><td>nothing: fully static, built with musl</td></tr>
<tr><td><code>dist/xs-darwin-universal</code></td><td>macOS on Apple silicon and Intel</td><td>Apple system libraries only</td></tr>
<tr><td><code>dist/manifest.json</code></td><td colspan="2">SHA-256 of each binary</td></tr>
</tbody></table></div>

<p>The preset needs CMake 3.24+, Ninja, a C/C++ compiler, GNU make and Docker with Linux amd64/arm64 emulation. A Linux host can build the two Linux binaries; the macOS binary needs a macOS host. zstd, xxHash and ICU are vendored as hash-checked source archives. <code>xs --version</code> includes the source revision, with <code>-dirty</code> for modified sources. No binaries are published for download yet.</p>

<div class="example-caption">Check a binary against the manifest</div>

```sh
python3 -c "import json; print(json.load(open('dist/manifest.json'))['xs-linux-arm64']['sha256'])"
shasum -a 256 dist/xs-linux-arm64
```


## REMOTE INSTALL {#remote}

<p>Native transfers need <code>xs</code> on both machines. <code>--install</code> is the only way xs ever puts an executable on another host: transfers never upload one. It runs <code>uname</code> on the host over ssh, picks the matching release binary, and installs it atomically at <code>~/.local/bin/xs</code>.</p>



<div class="example-caption">Install xs on a host that does not have it, then push natively</div>

```sh
export XSYNC_RELEASE_DIR=releases
xs --install user@pi
xs -azi --no-fallback src/ user@pi:backup/ | tail -n 3
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>Installed xs-linux-amd64 on user@pi at ~/.local/bin/xs&#10;xs  version 0.1.0  protocol version 4  git 1fff2a09ae2c&#10;&lt;f+++++++++ notes.txt&#10;cd+++++++++ scripts/&#10;&lt;f+++++++++ scripts/build.sh</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<ul>
<li>It refuses to replace a newer or unrecognized <code>xs</code> unless <code>--force</code> is given. An interrupted or invalid upload leaves the previous executable in place.</li>
<li>Release binaries are looked for beside the local <code>xs</code>, then in a sibling <code>dist/</code>, then in <code>../share/xs/releases/</code>. <code>XSYNC_RELEASE_DIR</code> names another directory.</li>
<li>After installing, transfers find the helper in <code>~/.local/bin</code> even though it is not on the remote <code>PATH</code>, as the push above shows.</li>
</ul>


## HOW TRANSFERS FIND THE HELPER {#lookup}

<figure class="diagram">
<svg viewBox="0 0 760 200" role="img" aria-labelledby="lookup-title lookup-desc">
<title id="lookup-title">Remote helper lookup</title>
<desc id="lookup-desc">With --rsync-path the named command is used. Otherwise the remote shell tries xs on PATH, then ~/.local/bin/xs, then XSYNC_REMOTE_PATH; if none exists, the transfer falls back to rsync or exits 127.</desc>
<defs><marker id="arrow-lookup" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="diagram-arrowhead"/></marker></defs>
<rect x="10" y="20" width="150" height="56" rx="3" class="diagram-strong"/><text x="85" y="44" text-anchor="middle" class="diagram-title">--rsync-path?</text><text x="85" y="62" text-anchor="middle" class="diagram-note">yes: run that command</text>
<rect x="200" y="20" width="120" height="56" rx="3"/><text x="260" y="44" text-anchor="middle">xs on PATH</text><text x="260" y="62" text-anchor="middle" class="diagram-note">remote PATH</text>
<rect x="360" y="20" width="140" height="56" rx="3"/><text x="430" y="44" text-anchor="middle">~/.local/bin/xs</text><text x="430" y="62" text-anchor="middle" class="diagram-note">where --install puts it</text>
<rect x="540" y="20" width="210" height="56" rx="3"/><text x="645" y="44" text-anchor="middle">XSYNC_REMOTE_PATH</text><text x="645" y="62" text-anchor="middle" class="diagram-note">local value first, then remote</text>
<rect x="430" y="130" width="320" height="56" rx="3" class="diagram-strong"/><text x="590" y="154" text-anchor="middle" class="diagram-title">None found: shell exits 127</text><text x="590" y="172" text-anchor="middle" class="diagram-note">fall back to rsync, or exit 127 with --no-fallback</text>
<path d="M160 48 L198 48" marker-end="url(#arrow-lookup)"/><text x="179" y="40" text-anchor="middle" class="diagram-note">no</text>
<path d="M320 48 L358 48" marker-end="url(#arrow-lookup)"/><path d="M500 48 L538 48" marker-end="url(#arrow-lookup)"/>
<path d="M645 76 L645 128" marker-end="url(#arrow-lookup)"/>
</svg>
<figcaption>The first match runs as <code>xs --server</code>. Each step is tried only if the previous one is not found.</figcaption>
</figure>

<p><code>XSYNC_REMOTE_PATH</code> may contain spaces or start with <code>~/</code>. An explicit <code>--rsync-path</code> is also used if the transfer falls back, so it must then accept rsync’s server arguments too; prefer the lookup when fallback matters.</p>


