---
title: "xs-config(5)"
description: "Set personal defaults and understand which layer wins."
manual: "xs-config(5)"
manualName: "Environment & defaults"
sectionNumber: "5"
---

# xs-config(5)

<div class="manual-deck"><strong>Environment &amp; defaults</strong><p>Set personal defaults and understand which layer wins.</p></div>

## FILES {#files}

<p>The default config is <code>$XDG_CONFIG_HOME/xsync/config</code>, or <code>~/.config/xsync/config</code> when XDG_CONFIG_HOME is unset. A missing default file is ignored. An explicitly selected missing file is an error.</p>



<div class="example-caption">A defaults file</div>

```sh
# ~/.config/xsync/config
--progress
--jobs=4
--exclude 'scratch files'
```

<p>Blank lines and full-line comments are allowed. Quoting splits words; variables, commands, and <code>~</code> are never expanded. Defaults contain flags and values, with transfer paths on the command line. Control actions such as install/server/help/version are not defaults.</p>



## PRECEDENCE {#precedence}

<p>For scalar options and on/off flags: <strong>command-line flags → environment → config</strong>. Within a layer, the last value wins. Repeatable options accumulate from config, then environment, then command-line flags; <code>--filter=!</code> clears earlier filter rules.</p>



<div class="example-caption">An explicit command-line override</div>

```sh
export XSYNC_OPTS='--jobs=8 --no-progress'
xs --progress src/ dst/
```



## ENVIRONMENT {#environment}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Variable</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td><code>XSYNC_CONFIG</code></td><td>Alternate config path; an empty value disables config</td></tr><tr><td><code>XSYNC_OPTS</code></td><td>Shell-quoted default option string</td></tr><tr><td><code>XSYNC_PROGRESS</code></td><td>0 disables; 1 enables; auto retains defaults; explicit flags win</td></tr><tr><td><code>XSYNC_FALLBACK</code></td><td>0 disables fallback; --fallback overrides it</td></tr><tr><td><code>XSYNC_RSH</code></td><td>Remote shell, ahead of RSYNC_RSH and defaults</td></tr><tr><td><code>RSYNC_RSH</code></td><td>Remote shell when higher-priority settings are absent</td></tr><tr><td><code>XSYNC_REMOTE_PATH</code></td><td>Extra remote helper lookup path</td></tr><tr><td><code>XSYNC_RELEASE_DIR</code></td><td>Release artifacts for explicit remote install</td></tr><tr><td><code>NO_COLOR</code></td><td>Disable color escapes in progress</td></tr></tbody></table></div>

## REMOTE SHELL PRECEDENCE {#remote-shell}

<p><code>--rsh</code>/<code>-e</code>, then <code>XSYNC_RSH</code>, then <code>RSYNC_RSH</code>, then a shell in XSYNC_OPTS, then config, then <code>ssh</code>. Empty shell values are rejected.</p>



<div class="example-caption">Set the remote shell through the environment</div>

```sh
export XSYNC_RSH='ssh -p 2222'
xs -azP src/ user@host:/backup/
```



## CONTROL DEFAULTS EXPLICITLY {#deterministic}



<div class="example-caption">Disable personal defaults and require native execution</div>

```sh
XSYNC_CONFIG='' XSYNC_OPTS='' xs --no-fallback --no-progress -a src/ dst/
```

<p>Check inherited <code>XSYNC_*</code> and <code>RSYNC_RSH</code> variables when making a fully controlled script. Explicit flags override progress and fallback defaults; supply <code>-e</code> if the remote shell must also be fixed.</p>



