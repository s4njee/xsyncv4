#!/usr/bin/env python3
"""Race xs-rs against xs-c++ on one machine: each tool copies a corpus to itself through tests/fakessh.sh (its
"remote" side runs locally), so the times compare the two programs on the same disk and CPU, without a network.

    rs/race.py CORPUS [--rounds 3] [--scenario fresh noop update] [--jobs 4] [--rtt MS] [--rs BINARY] [--scratch DIR]

fresh: into an empty destination; noop: again, nothing changed; update: after appending a few bytes to ~10% of
the files (in a scratch copy of the source). Rounds alternate which tool goes first. Each time ends after a sync,
so it counts writing the copy out, not just handing it to the page cache. Prints the median of each tool and
xs-rs's time over xs-c++'s (below 1: xs-rs is faster).

A pipe has no latency, and a real link does: --rtt MS runs the remote side behind rs/delayssh.py, which holds every
byte for half the round trip each way, so anything that waits on the peer costs what it would over the internet. --rs races another xs-rs build (a
baseline kept aside, say) in place of rs/target/release/xs-rs.
"""
import argparse
import os
import pathlib
import random
import shutil
import statistics
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
FAKESSH = REPO / 'tests' / 'fakessh.sh'
DELAYSSH = REPO / 'rs' / 'delayssh.py'
TOOLS = {'xs-c++': REPO / 'build' / 'xs', 'xs-rs': REPO / 'rs' / 'target' / 'release' / 'xs-rs'}
# The main lab measures over this machine's cable too: while this file exists (and is under 12 hours old) its
# runs wait before each block, so a race does not skew them, nor they the race.
FOREGROUND = pathlib.Path('/Volumes/xsbench/lab/runs/.foreground-xs-rs-dev')


def copy(tool, source, dest, jobs, rtt):
    rsh = f'{sys.executable} {DELAYSSH} {rtt}' if rtt else str(FAKESSH)
    argv = [str(TOOLS[tool]), '-a', f'-j{jobs}', '-e', rsh, f'--rsync-path={TOOLS[tool]}', f'{source}/', f'fake:{dest}/']
    start = time.perf_counter()
    done = subprocess.run(argv, capture_output=True, text=True)
    os.sync()
    took = time.perf_counter() - start
    if done.returncode:
        sys.exit(f'{tool} failed ({done.returncode}): {done.stderr.strip()[-600:]}')
    return took


def touch_tenth(source, seed):
    files = sorted(p for p in source.rglob('*') if p.is_file() and not p.is_symlink())
    for path in random.Random(seed).sample(files, max(1, len(files) // 10)):
        with open(path, 'ab') as stream:
            stream.write(b'\nxs-race\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('corpus', type=pathlib.Path)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--scenario', nargs='+', default=['fresh', 'noop'], choices=['fresh', 'noop', 'update'])
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--rtt', type=float, default=0, help='round trip to add between the two sides, in ms')
    parser.add_argument('--rs', type=pathlib.Path, help='the xs-rs binary to race (default: the release build)')
    parser.add_argument('--scratch', type=pathlib.Path, default=pathlib.Path('/Volumes/xsbench/dev/race'))
    args = parser.parse_args()
    if args.rs:
        TOOLS['xs-rs'] = args.rs.resolve()
    for tool, path in TOOLS.items():
        if not path.exists():
            sys.exit(f'{tool} is not built: {path}')
    source = args.corpus.resolve()
    if 'update' in args.scenario:  # the update scenario changes files: it works on its own copy
        work = args.scratch / 'source'
        shutil.rmtree(work, ignore_errors=True)
        work.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['cp', '-Rp', f'{source}/', str(work)], check=True)
        source = work
    times = {(t, s): [] for t in TOOLS for s in args.scenario}
    held = FOREGROUND.parent.is_dir() and not FOREGROUND.exists()
    if held:
        FOREGROUND.touch()
    try:
        race(args, source, times)
    finally:
        if held:
            FOREGROUND.unlink(missing_ok=True)
    rtt = f', {args.rtt:g} ms round trip' if args.rtt else ''
    print(f'\n{args.corpus.name}, {args.rounds} rounds, -a -j{args.jobs}{rtt}, median seconds')
    for scenario in args.scenario:
        cpp, rs = (statistics.median(times[(t, scenario)]) for t in TOOLS)
        print(f'{scenario:6}  xs-c++ {cpp:8.2f}   xs-rs {rs:8.2f}   xs-rs/xs-c++ {rs / cpp:5.2f}')


def race(args, source, times):
    for round_ in range(args.rounds):
        order = list(TOOLS) if round_ % 2 == 0 else list(reversed(TOOLS))
        for tool in order:
            dest = args.scratch / f'dest-{tool}'
            shutil.rmtree(dest, ignore_errors=True)
            dest.mkdir(parents=True)
            for scenario in args.scenario:
                if scenario == 'update':
                    copy(tool, source, dest, args.jobs, args.rtt)  # bring the copy up to date first, untimed
                    touch_tenth(source, round_ * 7 + len(tool))
                took = copy(tool, source, dest, args.jobs, args.rtt)
                times[(tool, scenario)].append(took)
                print(f'round {round_ + 1} {tool:6} {scenario:6} {took:8.2f} s', flush=True)
            shutil.rmtree(dest, ignore_errors=True)
            if FOREGROUND.exists():
                FOREGROUND.touch()  # a long race keeps the main lab waiting


if __name__ == '__main__':
    main()
