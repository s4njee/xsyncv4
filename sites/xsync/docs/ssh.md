---
title: "xsync-ssh(1)"
description: "Choose a shell, prepare the remote helper, and bound idle connections."
manual: "xsync-ssh(1)"
manualName: "SSH & remote helpers"
sectionNumber: "1"
---

# xsync-ssh(1)

<div class="manual-deck"><strong>SSH &amp; remote helpers</strong><p>Choose a shell, prepare the remote helper, and bound idle connections.</p></div>

## DESCRIPTION {#description}

<p>xsync transports its native protocol over a remote shell, normally OpenSSH. Paths are carried as protocol data. The helper must support the client’s protocol and requested capabilities.</p>



## EXAMPLES {#examples}



<div class="example-caption">Use a specific SSH identity</div>

```sh
xsync -azP -e "ssh -i ~/.ssh/backup_key" src/ user@host:/backup/
```



<div class="example-caption">Use a different SSH port</div>

```sh
xsync -azP -e "ssh -p 2222" src/ user@host:/backup/
```



<div class="example-caption">Bracketed IPv6 host</div>

```sh
xsync -aP src/ "user@[::1]:backup/"
```

<p>An empty remote path, <code>host:</code>, refers to the remote current directory. Leading <code>~</code> and <code>~user</code> expand on the server; quote remote wildcards to prevent your local shell from expanding them.</p>



## HELPER LOOKUP {#helper}

<p>Transfers try <code>xsync</code> on remote PATH, then <code>~/.local/bin/xsync</code>, then <code>XSYNC_REMOTE_PATH</code>. The local environment value takes precedence over the remote value.</p>



<div class="example-caption">Choose an explicit helper</div>

```sh
xsync -azP --rsync-path=/opt/bin/xsync src/ user@host:/backup/
```

<aside class="manual-note"><span>NOTE</span><p>An explicit <code>--rsync-path</code> bypasses automatic lookup. If fallback is needed, that same command must support rsync. An explicit xsync-only executable may therefore prevent fallback.</p></aside>

## EXPLICIT REMOTE INSTALL {#install}



<div class="example-caption">Install the matching release at ~/.local/bin/xsync</div>

```sh
xsync --install user@host
```

<p>The install command probes the remote OS and architecture and chooses the matching release artifact. Existing newer or unrecognized versions are refused unless <code>--force</code> is given. This requires matching release binaries to be available locally.</p>

<aside class="manual-note"><span>NOTE</span><p>Starting a transfer never uploads or silently installs a helper.</p></aside>

## BANDWIDTH AND TIMEOUTS {#limits}



<div class="example-caption">Limit bandwidth and remote idle time</div>

```sh
xsync -azP --bwlimit=10M --timeout=60 src/ user@host:/backup/
```

<p>Bare bandwidth numbers are KiB/s. Suffixed rates accept binary and decimal units; <code>0</code> disables the limit. Compression limits serialized wire bytes remotely; local workers share a limit on bytes written.</p>

<p><code>--timeout</code> bounds remote idle I/O, including shell/hello waits, partial frames, blocked writes, and a helper that remains alive after protocol EOF. <code>0</code> disables it. Local copies have no remote I/O deadline. A timeout exits with code <code>30</code>.</p>



## PROTOCOL AND FALLBACK {#protocol}

<p>Protocol 4 supports protocols 4 and 3. Optional features are negotiated before use. Missing helper support, incompatible protocols, and unsupported flags can delegate to rsync before transfer. <code>--no-fallback</code> fails instead.</p>

<p>See <a href="compatibility.html">compatibility</a> for fallback boundaries and <a href="environment.html">environment</a> for remote-shell precedence.</p>



