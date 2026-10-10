---
slug: protocol
title: xs-protocol(7)
name: Protocol & compatibility
summary: How xs talks to its remote helper, which features each option needs, and what happens with older helpers.
group: REFERENCE
after: compatibility
---

## OVERVIEW {#overview}

<p>xs is not wire-compatible with rsync. A remote transfer runs <code>xs --server</code> on the other machine over a remote shell, normally ssh, and the two processes speak xs’s own pipelined protocol over the shell’s stdin and stdout. Paths travel as protocol data, never as shell text.</p>

<p>Every constant on this page is read from <code>src/common.h</code> and <code>src/remote.cpp</code> when the documentation is built, and <code>npm run check</code> fails if the copy here is out of date.</p>

<!--generated:protocol-constants-->

## VERSIONS {#versions}

<p>Each release speaks its own protocol, N, and the one before it, N−1. When a protocol-4 client meets a protocol-3 helper, it reconnects once at protocol 3 before opening the destination. A protocol-3 client can also use a protocol-4 helper. If the versions are further apart, the transfer falls back to rsync, or exits 2 with <code>--no-fallback</code>.</p>

<p>A protocol-3 peer is assumed to support only the core transfer, compression, name mapping and safe links. Any request beyond that (<code>-H</code>, <code>-X</code>, <code>-A</code>, <code>--bwlimit</code>, extended filters, structured output and so on) delegates to rsync before anything is written.</p>

## NEGOTIATION {#negotiation}

<ol>
<li>The client starts the helper: <code>ssh [-l user] host &lt;helper&gt; --server</code>. The helper is <code>--rsync-path</code> if given; otherwise a small shell snippet tries <code>xs</code> on <code>PATH</code>, then <code>~/.local/bin/xs</code>, then <code>XSYNC_REMOTE_PATH</code>. If none is found, the shell exits 127 and the transfer falls back to rsync.</li>
<li>The client sends <code>F_HELLO</code>: magic, version, role (the helper receives on a push and sends on a pull), its feature mask, and the frozen options.</li>
<li>The helper answers with its own <code>F_HELLO</code>. The negotiated features are the intersection of both masks. Unknown bits are ignored.</li>
<li>Each side checks that every feature the requested options need is in the intersection. If one is missing, the transfer falls back to rsync before any write, or exits 4 with <code>--no-fallback</code>. Optional features, such as resume or compression, are simply not used.</li>
<li>Options outside the frozen layout follow as separate configuration frames, each sent only when its feature was negotiated: I/O limits, xattrs, ACLs, <code>--chown</code>, sparse, <code>--link-dest</code>, relative paths, file lists, filters, deletion, pruning and output.</li>
</ol>

## FEATURES {#features}

<!--generated:protocol-features-->

<p>Features that are never advertised on a platform are features its native filesystem layer cannot provide. Requesting one there fails before transfer, for example <code>-N</code> on Linux. <a href="options.html#source">The option reference</a> shows which features each option needs.</p>

## FRAMES {#frames}

<p>Every frame is a 4-byte payload length, a 1-byte type and the payload, capped at 1 GiB. Each type has its own length and negotiation checks: a frame for a feature that was not negotiated is a protocol error, never ignored.</p>

<!--generated:protocol-frames-->

## A PUSH {#push}

<ol>
<li>Handshake and configuration, as above.</li>
<li>The receiving helper sends <code>F_DEST</code>: its destination’s identity. The sender refuses to continue if the destination lies inside the source.</li>
<li>The sender walks the source in parallel and streams one <code>F_DIR</code> per directory, with <code>F_IDMAP</code> names and streamed extended attributes, then <code>F_LIST_END</code>.</li>
<li>For each directory, the receiver compares it with the destination and answers <code>F_NEED</code>: the files it wants, with any verified resume prefix and whether a delta is possible.</li>
<li>The sender reads the needed files on its worker threads. Small files are packed many to a <code>F_DATA</code> block; large files are split into chunks; changed large files can use a delta (<code>F_DELTA_REQUEST</code>, <code>F_DELTA_SIGNATURE</code>, then copy and literal records).</li>
<li>While writing, the receiver reports progress (<code>F_PROGRESS</code>), file events (<code>F_OUTPUT</code>), phases (<code>F_PHASE</code>) and errors (<code>F_MSG</code>).</li>
<li>The sender finishes with <code>F_DATA_END</code>; the receiver finalizes directory attributes and deletions and replies <code>F_DONE</code>.</li>
</ol>

<p>A pull is the same exchange with the roles reversed: the helper sends, and the client receives and renders output locally. See <a href="architecture.html#remote">how it works</a> for a diagram.</p>

## FROZEN PROTOCOL-3 LAYOUT {#v3-layout}

<p>The options inside <code>F_HELLO</code> keep the exact layout of protocol 3, so older peers can still parse them.</p>

<!--generated:protocol-v3-options-->

## ADDING A FEATURE {#adding}

<ul>
<li>A new optional frame, field or option gets its own feature bit. It must not change the protocol-3 layout or add unnegotiated fields to the Hello.</li>
<li>A receiver rejects frames for features that were not negotiated.</li>
<li>A requested semantic is never dropped silently. If the peer lacks a feature the user asked for, the transfer falls back or fails before any write.</li>
<li>When the supported window moves forward, a frozen N−1 peer is checked in as a fixture, like <code>tests/fixtures/protocol3.tar.gz</code>. Transfers are then tested in both directions, old client to new helper and new client to old helper, with fallback disabled (<code>tests/protocol_test.py</code>).</li>
</ul>
