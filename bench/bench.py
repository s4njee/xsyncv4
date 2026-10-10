#!/usr/bin/env python3
"""Benchmark xsync against rsync on a corpus of many small files.

Usage: bench/bench.py [--corpus DIR] [--runs N] [--only SUBSTR] [--rsync PATH] [--xsync PATH]

Every scenario is run N times per tool, interleaved (rsync, xsync, rsync, ...) so that
background noise hits both alike; the table reports the best and the median wall time.
The destination is removed before each "fresh" run (not timed) and each result is verified
against the source with `rsync -anci --delete` once per tool.

"pipe" scenarios run the real remote code path of both tools (sender and receiver processes
talking over a pipe via tests/fakessh.sh), without ssh encryption or a network in the way.
"""
import argparse
import os
import shutil
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--target" in sys.argv or any(a.startswith("--target=") for a in sys.argv):
        sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
        from run import main as remote_main
        return remote_main()
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=os.path.join(ROOT, ".bench", "corpus"))
    ap.add_argument("--work", default=os.path.join(ROOT, ".bench"))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--rsync", default="/opt/homebrew/bin/rsync")
    ap.add_argument("--xsync", default=os.path.join(ROOT, "build", "xs"))
    args = ap.parse_args()

    src = args.corpus.rstrip("/") + "/"
    dst = os.path.join(args.work, "bench-dst")
    fakessh = os.path.join(ROOT, "tests", "fakessh.sh")
    for p in (args.rsync, args.xsync, src):
        if not os.path.exists(p):
            sys.exit(f"missing: {p}")

    def tool(name):
        return args.rsync if name == "rsync" else args.xsync

    def local(flags):
        return lambda name, extra=(): [tool(name), *flags, *extra, src, dst + "/"]

    def pipe(flags):
        return lambda name, extra=(): [tool(name), *flags, *extra, "-e", fakessh, f"--rsync-path={tool(name)}", src, f"bench:{dst}/"]

    # (title, fresh destination?, command builder, [(label, tool, extra flags)])
    both = [("rsync", "rsync", ()), ("xsync", "xsync", ())]
    with_copy = both + [("xsync --no-clone", "xsync", ("--no-clone",))]
    scenarios = [
        ("local  -a   fresh copy", True, local(["-a"]), with_copy),
        ("local  -az  fresh copy", True, local(["-az"]), with_copy),
        ("local  -a   no-op re-sync", False, local(["-a"]), both),
        ("pipe   -a   fresh copy", True, pipe(["-a"]), both),
        ("pipe   -az  fresh copy", True, pipe(["-az"]), both),
        ("pipe   -az  no-op re-sync", False, pipe(["-az"]), both),
    ]

    def wipe():
        if os.path.exists(dst):
            subprocess.run(["rm", "-rf", dst], check=True)

    def verify():
        r = subprocess.run([args.rsync, "-anci", "--delete", src, dst + "/"], capture_output=True, text=True)
        return r.returncode == 0 and not r.stdout.strip()

    nfiles = sum(len(f) for _, _, f in os.walk(src))
    print(f"corpus: {src}  ({nfiles:,} files)")
    print(f"rsync:  {subprocess.run([args.rsync, '--version'], capture_output=True, text=True).stdout.splitlines()[0]}")
    print(f"runs per tool: {args.runs}\n")
    rows = []
    for title, fresh, build, tools in scenarios:
        if args.only and args.only not in title:
            continue
        times = {label: [] for label, _, _ in tools}
        ok = {label: True for label, _, _ in tools}
        if not fresh:  # no-op scenarios start from a complete destination
            wipe()
            subprocess.run([args.xsync, "-a", src, dst + "/"], check=True)
        for run in range(args.runs):
            for label, name, extra in tools:
                if fresh:
                    wipe()
                cmd = build(name, extra)
                t0 = time.perf_counter()
                r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                dt = time.perf_counter() - t0
                if r.returncode != 0:
                    sys.exit(f"{label} failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr}")
                times[label].append(dt)
                if run == 0 and not verify():
                    ok[label] = False
                print(f"  {title:<28} {label:<18} run {run + 1}: {dt:7.2f}s", flush=True)
        base = min(times["rsync"])
        for label, _, _ in tools:
            t = times[label]
            rows.append((title, label, min(t), statistics.median(t), base / min(t), ok[label]))
    wipe()

    print(f"\n{'scenario':<28} {'tool':<18} {'best':>8} {'median':>8} {'vs rsync':>9}  verified")
    last = None
    for title, label, best, med, speedup, good in rows:
        if last and last != title:
            print()
        last = title
        print(f"{title:<28} {label:<18} {best:7.2f}s {med:7.2f}s {speedup:8.2f}x  {'ok' if good else 'MISMATCH'}")


if __name__ == "__main__":
    main()
