---
title: "xsync-lessons(7)"
description: "What the first xsync learned from its benchmarks, and what xsync does with it."
manual: "xsync-lessons(7)"
manualName: "Lessons"
sectionNumber: "7"
pageClass: "lessons-page"
---

# xsync-lessons(7)

<div class="manual-deck"><strong>Lessons</strong><p>What the first xsync learned from its benchmarks, and what xsync does with it.</p></div>

## IN SHORT {#summary}

<p>Before this C++ version, xsync was written in Rust. That first version ran a long series of measured experiments across a MacBook, two Ryzen workstations, a Raspberry Pi and Windows. Most of its speed came from <strong>a handful of big ideas</strong>. Most clever-sounding tweaks <strong>did almost nothing</strong>. And the test machine itself caused fake results more than once.</p>

<div class="lesson-points"><div><strong>Do less work per file</strong><p>Bundling, cloning and checking things once beat every low-level trick.</p></div><div><strong>Measure the machine you sync with</strong><p>The best thread count changed from 4 to 24 depending on the disk.</p></div><div><strong>Don’t trust one run</strong><p>The same transfer took 23 s cold and 11 s warm, with no code change.</p></div></div>

## A FEW BIG IDEAS DID MOST OF THE WORK {#big-ideas}

<p>Each bar is one change v1 tried, measured against the version without it. The blue changes stayed. The gray ones were measured and dropped: even at their best they were within a few percent of doing nothing.</p>

<figure class="lesson-figure"><figcaption><span>Measured speed-up of each idea</span><p>The winners cut the work done per file. The losers made the same work slightly cheaper.</p></figcaption><HoloChart set="lessons" chart="wins" :height="470" label="Measured speed-up of each idea" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Change</th><th scope="col">Speed-up</th><th scope="col">Outcome</th></tr></thead><tbody><tr><td>Pack many small files into each network message</td><td>25.5×</td><td>Kept</td></tr><tr><td>Clone a whole new folder in one call (macOS)</td><td>6.27×</td><td>Kept</td></tr><tr><td>Read ahead on the sender, write in parallel on the receiver</td><td>3.11×</td><td>Kept</td></tr><tr><td>Check once whether the disk can clone files</td><td>2.98×</td><td>Kept</td></tr><tr><td>Compress, but only when a sample shows it helps</td><td>1.66×</td><td>Kept</td></tr><tr><td>Confirm progress every 8 chunks instead of every chunk</td><td>1.19×</td><td>Kept</td></tr><tr><td>Use a faster, weaker compression level</td><td>1.056×</td><td>Dropped</td></tr><tr><td>Rewrite file creation with io_uring (best case)</td><td>1.045×</td><td>Dropped</td></tr><tr><td>Pin work to the thread that found it (best case)</td><td>1.021×</td><td>Dropped</td></tr><tr><td>Hint the kernel to flush data early</td><td>1.007×</td><td>Dropped</td></tr><tr><td>Skip checksums entirely</td><td>1.001×</td><td>Dropped</td></tr><tr><td>Open extra SSH connections for a tree of small files</td><td>0.9×</td><td>Dropped</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/benches/results/story-8.1/DECISION.md" target="_blank" rel="noopener noreferrer"><code>benches/results/story-8.1/DECISION.md</code></a> · <a href="https://github.com/s4njee/xsync/blob/main/benches/results/tuning/T1/DECISION.md" target="_blank" rel="noopener noreferrer"><code>benches/results/tuning/T1/DECISION.md</code></a> · <a href="https://github.com/s4njee/xsync/blob/main/legacy/backlogv4.md" target="_blank" rel="noopener noreferrer"><code>legacy/backlogv4.md</code></a> · <a href="https://github.com/s4njee/xsync/blob/main/legacy/BENCHMARKSv3.md" target="_blank" rel="noopener noreferrer"><code>legacy/BENCHMARKSv3.md</code></a></p></details></figure><p>One example: v1 once asked the operating system 3.9 times as often as rsync did, about 25 calls per file instead of 6. Cutting those calls by 44% made it only 13% faster, because creating the files on disk was the real limit. <strong>Fewer steps only helps when those steps are what you’re waiting for.</strong></p>



## MORE THREADS ISN’T ALWAYS FASTER {#threads}

<p>Copying 10,000 small files locally, Linux kept getting faster all the way to 24 threads. macOS peaked at four or five and then got slower, because its file system handles changes to a folder one at a time. v1’s default of one thread per core was 8–15% slower than the best setting on the Mac.</p>

<figure class="lesson-figure"><figcaption><span>How much slower than its best setting each disk is</span><p>Lower is better. The Linux line keeps falling; both Mac lines turn back up after 4–5 threads.</p></figcaption><HoloChart set="lessons" chart="threads" :height="340" label="How much slower than its best setting each disk is" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Disk and data</th><th scope="col">Median time by worker threads</th></tr></thead><tbody><tr><td>Linux ext4 (24 cores)</td><td>1: 0.468 s, 2: 0.317 s, 4: 0.241 s, 6: 0.221 s, 8: 0.209 s, 12: 0.201 s, 16: 0.196 s, 24: 0.193 s</td></tr><tr><td>macOS APFS, government data</td><td>2: 2.856 s, 3: 2.609 s, 4: 2.520 s, 5: 2.500 s, 6: 2.554 s, 10: 2.717 s</td></tr><tr><td>macOS APFS, node_modules</td><td>2: 4.893 s, 4: 3.834 s, 5: 3.872 s, 8: 4.534 s, 10: 4.418 s, 16: 4.474 s</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/benches/results/tuning/T7/DECISION.md" target="_blank" rel="noopener noreferrer"><code>benches/results/tuning/T7/DECISION.md</code></a></p></details></figure><p><strong>What xsync does with this:</strong> choose the thread count from the kind of disk, not the number of cores. See <a href="roadmap.html#item-2-3">roadmap item 2.3</a>.</p>



## CLONE BIG FILES, COPY SMALL ONES {#clone}

<p>A clone makes a new file that shares storage with the original until either one changes. It sounds free, but on macOS each clone carries a fixed cost. For small files a plain copy is quicker. Past about 12 MiB, cloning wins and keeps winning.</p>

<figure class="lesson-figure"><figcaption><span>Clone vs plain copy on macOS, by file size</span><p>Below the dashed line copying is faster; above it cloning is faster.</p></figcaption><HoloChart set="lessons" chart="clone" :height="340" label="Clone vs plain copy on macOS, by file size" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">File size</th><th scope="col">Clone speed vs copy</th></tr></thead><tbody><tr><td>4 MiB</td><td>0.502×</td></tr><tr><td>8 MiB</td><td>0.863×</td></tr><tr><td>12 MiB</td><td>1.13×</td></tr><tr><td>16 MiB</td><td>1.448×</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/benches/results/tuning/T1/DECISION.md" target="_blank" rel="noopener noreferrer"><code>benches/results/tuning/T1/DECISION.md</code></a></p></details></figure><p>The same idea applies to whole folders: cloning a new folder in one call was 6.3 times faster than cloning its files one by one. On Linux, v1 found the biggest local win by <em>checking once</em> whether the disk supports clones, instead of trying and failing for every file (2.98× faster).</p>



## COMPRESSION: SAMPLE FIRST, THEN KEEP IT SIMPLE {#compression}

<p>Compressing data before sending it made a 100,000-file transfer 1.66 times as fast. But data that is already compressed, like photos or archives, only gets slower. v1 compresses a small sample first and sends the rest raw if the sample doesn’t shrink. Going from the default level 3 down to level 1 saved just 5%. Level 9 doubled the time.</p>

<figure class="lesson-figure"><figcaption><span>One 100,000-file transfer at different compression levels</span><p>Level 3 is within 5% of the fastest setting and shrinks data more.</p></figcaption><HoloChart set="lessons" chart="compression" :height="320" label="One 100,000-file transfer at different compression levels" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Setting</th><th scope="col">Seconds</th></tr></thead><tbody><tr><td>Off</td><td>12.52</td></tr><tr><td>Level 1</td><td>7.14</td></tr><tr><td>Level 3 (default)</td><td>7.54</td></tr><tr><td>Level 9</td><td>15.23</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/legacy/backlogv4.md" target="_blank" rel="noopener noreferrer"><code>legacy/backlogv4.md</code></a></p></details></figure><p>Level 3 measured 7.53–7.54 s in the two sessions these numbers come from.</p>



## EXTRA CONNECTIONS ONLY HELP BIG FILES {#connections}

<p>Splitting a file across several SSH connections lets more processor cores encrypt at once. That helped for files of 16 MiB and up. For trees of small files it made things slower, and on Windows extra connections cost 1.4–1.5 times the time. Too many connections also run into SSH server limits.</p>

<figure class="lesson-figure"><figcaption><span>Four SSH connections compared with one</span><p>Big files gain; small files and a 4 MiB file do not.</p></figcaption><HoloChart set="lessons" chart="stripes" :height="320" label="Four SSH connections compared with one" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Data</th><th scope="col">Speed with 4 connections</th></tr></thead><tbody><tr><td>4 MiB file</td><td>0.98×</td></tr><tr><td>16 MiB file</td><td>1.41×</td></tr><tr><td>64 MiB file</td><td>1.94×</td></tr><tr><td>Many small files</td><td>0.9×</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/benches/results/story-4.3/stripe-crossover.md" target="_blank" rel="noopener noreferrer"><code>benches/results/story-4.3/stripe-crossover.md</code></a></p></details></figure>

## THE NETWORK IS USUALLY THE LIMIT, NOT ENCRYPTION {#network}

<p>On a gigabit network, which carries about 125 MB/s at most, every SSH cipher v1 tried was within 4% of the others, and SSH matched a raw unencrypted socket. Encryption speed only matters on faster links. There, the default ChaCha20 cipher is much slower than AES on processors with AES hardware.</p>

<figure class="lesson-figure"><figcaption><span>How fast one SSH connection can encrypt</span><p>Both ciphers are far faster than a gigabit network can carry.</p></figcaption><HoloChart set="lessons" chart="cipher" :height="240" label="How fast one SSH connection can encrypt" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Cipher</th><th scope="col">MB/s</th></tr></thead><tbody><tr><td>ChaCha20 (OpenSSH default)</td><td>845.5</td></tr><tr><td>AES-128-GCM</td><td>2,374.5</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/legacy/exotic.md" target="_blank" rel="noopener noreferrer"><code>legacy/exotic.md</code></a></p></details></figure><p>Measured on one Ryzen 7950X talking to itself, so no network limit applied. The Raspberry Pi 5’s processor has AES instructions too, and on v1’s gigabit link to a Pi the two ciphers tied; <a href="roadmap.html#item-3-4">roadmap item 3.4</a> measures it.</p>



## THE TEST MACHINE CAN FAKE A RESULT {#honest}

<p>The same transfer to the same server took twice as long on its first runs as it did once the machine had warmed up. Nothing in the code changed.</p>

<figure class="lesson-figure"><figcaption><span>One transfer, timed again and again</span><p>The first runs look like a 2× slowdown that doesn’t exist.</p></figcaption><HoloChart set="lessons" chart="noise" :height="300" label="One transfer, timed again and again" /><details class="lesson-data"><summary>Show the numbers</summary><div class="manual-table-wrap"><table><thead><tr><th scope="col">Runs</th><th scope="col">Seconds</th></tr></thead><tbody><tr><td>Same transfer, first three runs</td><td>23.2, 21.8, 21.0</td></tr><tr><td>Same transfer, after warming up</td><td>11.6, 11.9, 11.4</td></tr></tbody></table></div><p class="lesson-source">Source: <a href="https://github.com/s4njee/xsync/blob/main/legacy/BENCHMARKSv3.md" target="_blank" rel="noopener noreferrer"><code>legacy/BENCHMARKSv3.md</code></a></p></details></figure><p>v1 recorded other ways the environment pretended to be the code:</p>

<ul class="lesson-list"><li><strong>Old binary.</strong> One whole experiment measured a stale build and had to be thrown away.</li><li><strong>Heat.</strong> A Raspberry Pi drifted from 18.1 s to 27.1 s over one session, most likely because it slowed itself down as it got hot.</li><li><strong>Tired disks.</strong> On a drive whose fast write cache kept filling up, one setting took anywhere from 61 to 94 seconds.</li><li><strong>A busy computer.</strong> One measurement ran while the machine’s load average was 265.</li><li><strong>Leftover writes.</strong> rsync can exit with 2.4 GB still waiting to reach the disk, so “finished” isn’t the same as “saved”.</li><li><strong>The network itself.</strong> A slow link and a stale IP address both produced fake regressions.</li></ul><p><strong>What xsync does with this:</strong> every benchmark alternates xsync and rsync, checks every copy byte for byte, records the machine’s state, and repeats each case. See <a href="roadmap.html#method">how we measure</a>.</p>



## WHAT CARRIES OVER TO XSYNC TODAY {#carried}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Lesson from v1</th><th scope="col">In xsync now</th></tr></thead><tbody><tr><td>Bundle small files and keep the pipe full</td><td>Done: 1 MiB blocks hold many small files, and listing, reading, sending and writing overlap</td></tr><tr><td>Clone whole new folders on macOS</td><td>Done for new folders of files and links, up to 4,096 entries</td></tr><tr><td>Check once whether a Linux disk can clone</td><td>Planned: <a href="roadmap.html#item-2-1">roadmap 2.1</a></td></tr><tr><td>Choose threads by disk, not cores</td><td>Planned: <a href="roadmap.html#item-2-3">roadmap 2.3</a></td></tr><tr><td>Compress only what shrinks</td><td>Planned: <a href="roadmap.html#item-3-1">roadmap 3.1</a></td></tr><tr><td>Use extra connections for big files only</td><td>Planned, only if measurements call for it: <a href="roadmap.html#item-3-5">roadmap 3.5</a></td></tr><tr><td>Don’t trust a single run</td><td>Done: paired, verified benchmarks and a CI speed check</td></tr></tbody></table></div>

## SOURCES {#sources}

<p>Every figure links to the v1 files its numbers come from, in the <a href="https://github.com/s4njee/xsync" target="_blank" rel="noopener noreferrer">s4njee/xsync</a> repository. Speed-ups are relative to the version without each change on the same machine and data. Charts are drawn with <a href="https://github.com/holochart/holochart" target="_blank" rel="noopener noreferrer">Holochart</a>. The full analysis, with a citation for every number, is in <code>ROADMAP.md</code>.</p>



