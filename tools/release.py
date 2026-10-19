#!/usr/bin/env python3
"""Build and verify musl releases; copy the already-built native artifact."""
import argparse
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=pathlib.Path, help='the macOS universal binary, on a Mac')
    parser.add_argument('--revision', required=True)
    # One machine builds the whole set by default (the release-set target). CI builds each platform on
    # its own runner: macOS with --no-linux, each Linux architecture with --linux-arch on a native runner.
    parser.add_argument('--linux-arch', action='append', choices=('amd64', 'arm64'), dest='linux_arches')
    parser.add_argument('--no-linux', action='store_true')
    args = parser.parse_args()
    if platform.system() == 'Darwin' and not args.native:
        parser.error('--native is required on macOS')
    linux_arches = [] if args.no_linux else args.linux_arches or ['amd64', 'arm64']
    out = REPO / 'dist'
    out.mkdir(exist_ok=True)
    artifacts = []
    if platform.system() == 'Darwin' and args.native:
        arches = run('lipo', '-archs', args.native, capture_output=True, text=True).stdout.split()
        if set(arches) != {'arm64', 'x86_64'}:
            raise RuntimeError('native macOS release must contain arm64 and x86_64')
        dependencies = run('otool', '-L', args.native, capture_output=True, text=True).stdout
        if any('/opt/' in line or '/usr/local/' in line for line in dependencies.splitlines()[1:]):
            raise RuntimeError('macOS release still depends on third-party dynamic libraries')
        binary = out / 'xs-darwin-universal'
        shutil.copy2(args.native, binary)
        artifacts.append(binary)
    for arch in linux_arches:
        image = 'xsync-release-' + arch
        run('docker', 'build', '--platform', 'linux/' + arch, '--build-arg', 'XSYNC_GIT_HASH=' + args.revision,
            '-t', image, '-f', REPO / 'tools/release.Dockerfile', REPO)
        container = 'xsync-release-' + uuid.uuid4().hex[:10]
        try:
            run('docker', 'create', '--platform', 'linux/' + arch, '--name', container, image, '/xs', '--version',
                stdout=subprocess.DEVNULL)
            binary = out / ('xs-linux-' + arch)
            run('docker', 'cp', container + ':/xs', binary)
            binary.chmod(0o755)
            # A scratch image has no loader, libc, ICU data, or compression libraries.
            run('docker', 'start', '-a', container)
            status = run('docker', 'inspect', '-f', '{{.State.ExitCode}}', container,
                         capture_output=True, text=True).stdout.strip()
            if status != '0':
                raise RuntimeError('standalone Linux executable failed: ' + status)
            smoke = r'''set -eu
bin=/releases/xs-linux-ARCH
mkdir /tmp/source
head -c 2097152 /dev/zero >/tmp/source/file
printf 'unicode contents\n' >'/tmp/source/straße with spaces'
ln -s file '/tmp/source/space link'
"$bin" --no-fallback -a /tmp/source/ /tmp/local/
cmp /tmp/source/file /tmp/local/file
cmp '/tmp/source/straße with spaces' '/tmp/local/straße with spaces'
printf '#!/bin/sh\nshift\nexec /bin/sh -c "$*"\n' >/tmp/fakessh
chmod 755 /tmp/fakessh
mkdir /tmp/pushed /tmp/pulled
head -c 1048576 /tmp/source/file >/tmp/pushed/file
head -c 1048576 /tmp/source/file >/tmp/pulled/file
"$bin" --no-fallback -az --partial --out-format='%i|%n|%l|%b' --log-file=/tmp/push.log -e /tmp/fakessh --rsync-path="$bin" /tmp/source/ fake:/tmp/pushed/ >/tmp/push.stdout
"$bin" --no-fallback -az --partial --out-format='%i|%n|%l|%b' --log-file=/tmp/pull.log -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/pushed/ /tmp/pulled/ >/tmp/pull.stdout
cmp /tmp/push.log /tmp/push.stdout
cmp /tmp/pull.log /tmp/pull.stdout
grep -F 'file|2097152|1048576' /tmp/push.stdout
grep -F 'file|2097152|1048576' /tmp/pull.stdout
cmp /tmp/source/file /tmp/pulled/file
cmp '/tmp/source/straße with spaces' '/tmp/pulled/straße with spaces'
test "$(readlink '/tmp/pulled/space link')" = file
ln /tmp/source/file /tmp/source/hardlink
ln -P '/tmp/source/space link' '/tmp/source/space link2'
mkfifo /tmp/source/pipe
ln /tmp/source/pipe /tmp/source/pipe2
"$bin" --no-fallback -aHi /tmp/source/ /tmp/hard-local/
"$bin" --no-fallback -azH --out-format='%i|%n|%L' -e /tmp/fakessh --rsync-path="$bin" /tmp/source/ fake:/tmp/hard-pushed/ >/tmp/hard.stdout
"$bin" --no-fallback -azH -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/source/ /tmp/hard-pulled/
grep -F 'hf+++++++++' /tmp/hard.stdout
grep -F '| => ' /tmp/hard.stdout
for target in /tmp/hard-local /tmp/hard-pushed /tmp/hard-pulled; do
  cmp /tmp/source/file "$target/file"
  test "$(stat -c %d:%i "$target/file")" = "$(stat -c %d:%i "$target/hardlink")"
  test "$(stat -c %d:%i "$target/space link")" = "$(stat -c %d:%i "$target/space link2")"
  test "$(stat -c %d:%i "$target/pipe")" = "$(stat -c %d:%i "$target/pipe2")"
done
head -c 8388608 /dev/urandom >/tmp/delta-source
cp /tmp/delta-source /tmp/delta-local
cp /tmp/delta-source /tmp/delta-pushed
cp /tmp/delta-source /tmp/delta-pulled
printf 'edited delta record' | dd of=/tmp/delta-source bs=1 seek=123456 conv=notrunc 2>/dev/null
"$bin" --no-fallback -aI --no-clone --stats /tmp/delta-source /tmp/delta-local >/tmp/delta-local.stats
"$bin" --no-fallback -azI --stats -e /tmp/fakessh --rsync-path="$bin" /tmp/delta-source fake:/tmp/delta-pushed >/tmp/delta-push.stats
inode=$(stat -c %d:%i /tmp/delta-pulled)
"$bin" --no-fallback -azI --inplace --stats -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/delta-source /tmp/delta-pulled >/tmp/delta-pull.stats
test "$(stat -c %d:%i /tmp/delta-pulled)" = "$inode"
for target in /tmp/delta-local /tmp/delta-pushed /tmp/delta-pulled; do cmp /tmp/delta-source "$target"; done
for stats in /tmp/delta-local.stats /tmp/delta-push.stats /tmp/delta-pull.stats; do grep -E 'Delta matched data: [1-9]' "$stats"; done
"$bin" --no-fallback -al --list-only /tmp/source/ /tmp/uncreated-list-target >/tmp/list-local.stdout
"$bin" --no-fallback -al -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/source/ >/tmp/list-remote.stdout
cmp /tmp/list-local.stdout /tmp/list-remote.stdout
test ! -e /tmp/uncreated-list-target
grep -E '^d.* [.]$' /tmp/list-local.stdout
grep -F 'space link -> file' /tmp/list-local.stdout
grep -E '^p.* pipe$' /tmp/list-local.stdout
"$bin" --no-fallback -c --stats /tmp/delta-source >/tmp/list.stats
grep -F 'Number of regular files transferred: 0' /tmp/list.stats
set +e
"$bin" --no-fallback --list-only /tmp/missing-one /tmp/missing-two /tmp/ignored >/tmp/errors.stdout 2>/tmp/errors.stderr
status=$?
set -e
test "$status" = 23
test ! -s /tmp/errors.stdout
grep -F 'xs: error summary: 2 errors (showing first 2)' /tmp/errors.stderr
grep -F 'partial transfer (code 23): 2 errors' /tmp/errors.stderr
test "$(tail -n 1 /tmp/errors.stderr)" = 'xs error: some files/attrs were not transferred (see previous errors) (code 23)'
set +e
"$bin" --no-fallback --list-only -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/missing-one fake:/tmp/missing-two /tmp/ignored >/tmp/errors-remote.stdout 2>/tmp/errors-remote.stderr
status=$?
set -e
test "$status" = 23
test ! -s /tmp/errors-remote.stdout
grep -F 'xs: error summary: 2 errors (showing first 2)' /tmp/errors-remote.stderr
head -c 393216 /dev/zero >/tmp/rate-source
for direction in local push pull; do
  source=/tmp/rate-source
  target=/tmp/rate-$direction
  test "$direction" != push || target=fake:$target
  test "$direction" != pull || source=fake:$source
  started=$(date +%s)
  "$bin" --no-fallback -aW --bwlimit=128 --timeout=1 -e /tmp/fakessh --rsync-path="$bin" "$source" "$target"
  test "$(($(date +%s) - started))" -ge 2
  cmp /tmp/rate-source /tmp/rate-$direction
done
printf '#!/bin/sh\nexec sleep 10\n' >/tmp/stall-rsh
chmod 755 /tmp/stall-rsh
set +e
"$bin" --no-fallback --timeout=1 -e /tmp/stall-rsh fake:/tmp/source/ >/tmp/timeout.stdout 2>/tmp/timeout.stderr
status=$?
set -e
test "$status" = 30
test ! -s /tmp/timeout.stdout
grep -F 'idle timeout (code 30): 1 error' /tmp/timeout.stderr
mkdir -p /tmp/filter-source/chain/empty /tmp/filter-source/data
printf 'actual data' >/tmp/filter-source/data/file
printf '# newly transferred receiver rules\nP stale\n' >/tmp/filter-source/.rules
for direction in local push pull; do
  target=/tmp/filter-$direction
  mkdir "$target"
  printf 'R stale\n' >"$target/.rules"
  printf 'must survive refreshed protection' >"$target/stale"
  source=/tmp/filter-source/
  destination=$target/
  test "$direction" != push || destination=fake:$destination
  test "$direction" != pull || source=fake:$source
  "$bin" --no-fallback -amC --delete-after --filter=': .rules' --stats \
    -e /tmp/fakessh --rsync-path="$bin" "$source" "$destination" >"$target.stats"
  cmp /tmp/filter-source/data/file "$target/data/file"
  cmp /tmp/filter-source/.rules "$target/.rules"
  test -f "$target/stale"
  test ! -e "$target/chain"
  grep -F 'Number of files: 3 (reg: 2, dir: 1)' "$target.stats"
done
"$bin" --no-fallback -rmC --filter=': .rules' -e /tmp/fakessh --rsync-path="$bin" \
  fake:/tmp/filter-source/ >/tmp/filter.list
grep -F 'data/file' /tmp/filter.list
test "$(grep -c chain /tmp/filter.list)" = 0
mkdir -p /tmp/select-source/deep/leaf /tmp/select-source/empty
printf 'selected data' >/tmp/select-source/deep/leaf/file
ln /tmp/select-source/deep/leaf/file /tmp/select-source/linked
odd=$(printf 'line\nbreak')
printf 'odd filename' >"/tmp/select-source/$odd"
printf 'deep/leaf/file\0linked\0line\nbreak\0' >/tmp/select.names
for direction in local push pull; do
  source=/tmp/select-source/
  target=/tmp/select-$direction
  mkdir -p "$target/deep"
  printf 'keep unlisted implied sibling' >"$target/deep/unlisted"
  destination=$target/
  test "$direction" != push || destination=fake:$destination
  test "$direction" != pull || source=fake:$source
  "$bin" --no-fallback -aH0 --files-from=/tmp/select.names --delete \
    -e /tmp/fakessh --rsync-path="$bin" "$source" "$destination"
  cmp /tmp/select-source/deep/leaf/file "$target/deep/leaf/file"
  cmp "/tmp/select-source/$odd" "$target/$odd"
  test "$(stat -c %d:%i "$target/deep/leaf/file")" = "$(stat -c %d:%i "$target/linked")"
  test -f "$target/deep/unlisted"
  test ! -e "$target/empty"
done
"$bin" --no-fallback -aH0 --files-from=:/tmp/select.names -e /tmp/fakessh --rsync-path="$bin" \
  /tmp/select-source/ fake:/tmp/select-remote-push/
"$bin" --no-fallback -aH0 --files-from=:/tmp/select.names -e /tmp/fakessh --rsync-path="$bin" \
  fake:/tmp/select-source/ /tmp/select-remote-pull/
for target in /tmp/select-remote-push /tmp/select-remote-pull; do
  cmp /tmp/select-source/deep/leaf/file "$target/deep/leaf/file"
  cmp "/tmp/select-source/$odd" "$target/$odd"
done
cat /tmp/select.names | "$bin" --no-fallback -a0 --files-from=- /tmp/select-source/ /tmp/select-stdin/
cmp "/tmp/select-source/$odd" "/tmp/select-stdin/$odd"
"$bin" --no-fallback -aR /tmp/select-source/./deep/leaf/file /tmp/select-relative/
cmp /tmp/select-source/deep/leaf/file /tmp/select-relative/deep/leaf/file
printf 'line\nbreak\0' >/tmp/select.exclude
"$bin" --no-fallback -a0 --exclude-from=/tmp/select.exclude /tmp/select-source/ /tmp/select-filtered/
test ! -e "/tmp/select-filtered/$odd"
cmp /tmp/select-source/deep/leaf/file /tmp/select-filtered/deep/leaf/file
"$bin" --no-fallback -rl0 --list-only --files-from=/tmp/select.names \
  -e /tmp/fakessh --rsync-path="$bin" fake:/tmp/select-source/ /tmp/uncreated-selected >/tmp/select.list
grep -F 'deep/leaf/file' /tmp/select.list
test ! -e /tmp/uncreated-selected
"$bin" --version
'''.replace('ARCH', arch)
            run('docker', 'run', '--rm', '--platform', 'linux/' + arch,
                '-v', str(out) + ':/releases:ro', 'debian:bookworm-slim', 'sh', '-ec', smoke)
            artifacts.append(binary)
        finally:
            subprocess.run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    manifest = {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'bytes': p.stat().st_size, 'git': args.revision} for p in artifacts}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Retire the previously generated binary names after the new set is verified.
    for name in ('xsync-linux-amd64', 'xsync-linux-arm64', 'xsync-darwin-universal'):
        (out/name).unlink(missing_ok=True)
    print('Verified releases: ' + ', '.join(manifest), flush=True)


if __name__ == '__main__':
    main()
