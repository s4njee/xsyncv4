---
slug: performance
title: xs-bench(7)
name: Performance
summary: Measured transfer times against rsync, with the hosts, datasets and evidence behind every number.
group: PROJECT
after: development
---

## SUMMARY {#summary}

<p>Every number on this page comes from a verified benchmark result file in <code>benchmarks/results/</code>, and each table row links to it. Each run is reported separately, together with its hosts, filesystems, dataset sizes and cache policy. Results from different runs are never merged.</p>

<p>The current picture is mixed. Over a 1 Gb/s LAN, uncompressed transfers of medium and large files are limited by the network, and the two tools take about the same time. With <code>-z</code>, xs is faster on the mixed tree in both directions. Several cases are slower today, including a checksum pass over large files pulled to the Raspberry Pi, the single tiny-file pull, and an APFS re-sync with nothing to do. They are tracked as F-07, F-08, F-13 and F-14 in the <a href="development.html#open">development status</a>.</p>

<aside class="manual-note"><span>READING THE TABLES</span><p>Times are medians of verified samples, with the fastest–slowest range underneath. “xs speedup” is rsync’s median divided by xs’s, so values below 1.00× mean xs was slower. CPU is summed across the client and remote process trees; peak memory is the larger of the two endpoints, not their sum.</p></aside>

## METHOD {#method}

<p>The runner alternates tool order between samples and records wall time, CPU and peak resident memory on both ends. After every sample it checks the destination with an independent <code>rsync -anci --delete</code> dry run. A nonzero exit or any verification output fails the run. Setup, deletion of the previous destination, and verification are not timed. A result file is marked complete only after every requested scenario finishes.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Scenario</th><th scope="col">What is timed</th></tr></thead><tbody>
<tr><td><code>fresh</code></td><td><code>-a</code> into an empty destination</td></tr>
<tr><td><code>fresh-z</code></td><td>the same with <code>-z</code></td></tr>
<tr><td><code>noop</code></td><td>a re-sync when nothing has changed</td></tr>
<tr><td><code>checksum</code></td><td>a <code>-c</code> re-sync when nothing has changed</td></tr>
<tr><td><code>tiny</code></td><td>one 19-byte file, where fixed startup and handshake costs dominate</td></tr>
</tbody></table></div>

<p>Unless a run says otherwise, operating-system caches are left as they are. That is not a cold-cache measurement, and a corpus larger than memory is not necessarily resident either.</p>

## RESULTS {#results}

<!--generated:benchmarks-->

## HISTORICAL LOCAL BASELINE {#historical}

<aside class="manual-note"><span>HISTORICAL</span><p>These numbers come from an earlier binary, before the trust fixes and the atomic-write default. They used a different harness (best of three, not a median) on an M1 Max with the 109th Congress slice: 76,838 files, 494 MiB, on one APFS volume. Do not compare them with the runs above.</p></aside>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Scenario</th><th scope="col">rsync</th><th scope="col">xs</th><th scope="col">Speedup</th></tr></thead><tbody>
<tr><td>local <code>-a</code>, fresh copy</td><td>15.02 s</td><td>2.02 s</td><td>7.4×</td></tr>
<tr><td>local <code>-az</code>, fresh copy</td><td>15.05 s</td><td>1.97 s</td><td>7.6×</td></tr>
<tr><td>local <code>-a</code>, fresh, <code>--no-clone</code></td><td>15.02 s</td><td>6.65 s</td><td>2.3×</td></tr>
<tr><td>local <code>-a</code>, nothing to do</td><td>0.77 s</td><td>0.40 s</td><td>1.9×</td></tr>
<tr><td>pipe <code>-a</code>, fresh copy</td><td>19.92 s</td><td>8.47 s</td><td>2.4×</td></tr>
<tr><td>pipe <code>-az</code>, fresh copy</td><td>18.00 s</td><td>7.77 s</td><td>2.3×</td></tr>
<tr><td>pipe <code>-az</code>, nothing to do</td><td>0.99 s</td><td>0.52 s</td><td>1.9×</td></tr>
</tbody></table></div>

<p>The local rows with clones only apply on the same APFS volume with <code>-a</code>, or at least <code>-pt</code>. Across volumes, or with <code>--no-clone</code>, expect the byte-copy row. “Pipe” runs the real remote code path of both tools through a local pipe (<code>-e tests/fakessh.sh</code>), with no SSH or network in between. The current APFS no-op diagnostic above is much slower than this historical no-op row, on a heavily loaded host with a 98% full volume; quieter, free-volume measurements are still needed.</p>

## REPRODUCE {#reproduce}

<div class="example-caption">Paired SSH run between two hosts, then a summary table</div>

```sh
python3 benchmarks/pair.py --runs 3
python3 benchmarks/report.py --run-id RUN_ID --output benchmarks/results/RUN_ID-summary.md
```

<div class="example-caption">One SSH target through the original harness</div>

```sh
python3 bench/bench.py --target user@host:/absolute/root
```

<p>The full procedure, including fixture preparation, cache-reset requirements and the SSH stream probe, is in <a href="https://github.com/s4njee/xsyncv4/blob/main/benchmarks/README.md">benchmarks/README.md ↗</a>. After adding a run to <code>benchmarks/results/</code>, run <code>npm run docs:refresh</code> in <code>sites/xsync</code>; the new run appears on this page without hand edits.</p>

## NOT YET MEASURED {#gaps}

<ul>
<li>Cold-cache runs on either host.</li>
<li>The full 10.53 GB Congress corpus in both directions (the push above is still in progress), and the 1% update fixture.</li>
<li>Local copies on Linux filesystems such as ext4 and XFS, where a parallel receiver should matter more than on APFS.</li>
<li>A regression gate that fails CI when a scenario loses ground (backlog F-02).</li>
</ul>
