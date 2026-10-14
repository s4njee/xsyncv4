#!/usr/bin/env python3
"""Build xs from a commit and stage it, with the lab's scripts, on the benchmark hosts.

A build is made from `git archive` of a commit, never from the working tree,
so a binary cannot contain uncommitted changes. Each host keeps it as
ROOT/bin/xs-<rev12>; `check` refuses a host whose copy is missing, is not
byte-for-byte the recorded build, or reports another or a dirty revision.

The lab's scripts are staged as a bundle, ROOT/lib/<id>, named by the hash of
its contents and never changed once written. A plan names the bundle it was
made with, so staging newer scripts cannot disturb a queued or running plan.

A revision written REV-tune is the same commit built with XSYNC_TUNABLES=ON,
for experiments that set engine constants. It is a separate build with its own
record, staged as ROOT/bin/xs-<rev12>-tune.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile

import preflight

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
BUILDS = REPO / '.bench' / 'lab' / 'builds'             # binaries, not tracked
RECORDS = HERE.parent / 'results' / 'lab' / 'builds'    # their hashes, tracked
ARCHES = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}


def artifact_for(system, machine):
    """The build a host of this kind runs, or None."""
    arch = ARCHES.get(machine)
    return f'xs-{"darwin" if system == "Darwin" else "linux"}-{arch}' if arch else None


def run_on(host, script, **options):
    """Run a shell command on a host: directly if it is this machine, else over SSH."""
    # The login shell there may not be a POSIX one, so sh runs the script on either kind of host.
    command = ['sh', '-c', script] if host.get('local') else [*preflight.SSH, host['ssh'], 'sh -c ' + shlex.quote(script)]
    return subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL, **options)


def copy_to(host, paths, directory):
    if host.get('local'):
        for path in paths:
            shutil.copy2(path, directory)
    else:
        run('scp', '-q', '-oBatchMode=yes', *paths, f'{host["ssh"]}:{directory}/')
SCRIPTS = (HERE / 'probe.py', HERE / 'corpus.py', HERE / 'corpora.json', HERE / 'agent.py', HERE / 'runner.py',
           HERE.parent / 'measure.py')


def run(*command, **options):
    return subprocess.run(list(map(str, command)), check=True, **options)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


TUNE = '-tune'


def identify(revision):
    """(full commit hash, build id, whether it is the tunables build) of REV or REV-tune."""
    tunables = revision.endswith(TUNE)
    full = resolve(revision[:-len(TUNE)] if tunables else revision)
    return full, full[:12] + (TUNE if tunables else ''), tunables


def build_id(revision):
    return identify(revision)[1]


def resolve(revision):
    """The full hash of a commit, or exit."""
    done = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--verify', '--quiet', revision + '^{commit}'],
                          capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f'{revision} is not a commit')
    return done.stdout.strip()


def load_build(revision):
    record = BUILDS / build_id(revision) / 'build.json'
    if not record.exists():
        raise SystemExit(f'{revision} has not been built: run stage.py build --rev {revision}')
    return json.loads(record.read_text())


def build(revision, rebuild=False):
    """Build the static Linux release of a commit for both architectures."""
    full, name_id, tunables = identify(revision)
    short = full[:12]
    output = BUILDS / name_id
    option = 'ON' if tunables else 'OFF'
    native = artifact_for(platform.system(), platform.machine()) if platform.system() == 'Darwin' else None
    artifacts = {}
    if (output / 'build.json').exists() and not rebuild:
        record = json.loads((output / 'build.json').read_text())
        if not native or native in record['artifacts']:
            return record
        artifacts = record['artifacts']  # built before this machine was an endpoint: add its own binary
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as source:
        archive = subprocess.Popen(['git', '-C', str(REPO), 'archive', '--format=tar', full], stdout=subprocess.PIPE)
        run('tar', '-x', '-C', source, stdin=archive.stdout)
        if archive.wait():
            raise SystemExit('git archive failed')
        if native and native not in artifacts:
            # This machine's own binary, from the same exported commit, for when it is an endpoint.
            print(f'building {native} from {short}', flush=True)
            with open(output / 'build-native.log', 'w') as log:
                done = subprocess.run(f'cmake -S {shlex.quote(source)} -B {shlex.quote(source)}/native -G Ninja '
                                      f'-DCMAKE_BUILD_TYPE=Release -DXSYNC_GIT_HASH={short} -DXSYNC_TUNABLES={option} && '
                                      f'cmake --build {shlex.quote(source)}/native --target xsync -j 8',
                                      shell=True, stdout=log, stderr=subprocess.STDOUT)
            if done.returncode:
                raise SystemExit(f'native build failed; see {output / "build-native.log"}')
            shutil.copy2(pathlib.Path(source) / 'native' / 'xs', output / native)
            version = run(output / native, '--version', capture_output=True, text=True).stdout.splitlines()[0]
            if problem := version_problem(version, short, tunables):
                raise SystemExit(f'{native}: {problem}')
            artifacts[native] = {'sha256': sha256(output / native), 'bytes': (output / native).stat().st_size,
                                 'version': version}
        for arch in ('amd64', 'arm64'):
            if f'xs-linux-{arch}' in artifacts:
                continue
            image, name = f'xsbench-xs-{name_id}-{arch}', f'xs-linux-{arch}'
            print(f'building {name} from {name_id}', flush=True)
            with open(output / f'build-{arch}.log', 'w') as log:
                done = subprocess.run(['docker', 'build', '--platform', f'linux/{arch}', '--build-arg',
                                       f'XSYNC_GIT_HASH={short}', '--build-arg', f'XSYNC_TUNABLES={option}',
                                       '-t', image, '-f',
                                       f'{source}/tools/release.Dockerfile', source],
                                      stdout=log, stderr=subprocess.STDOUT)
            if done.returncode:
                raise SystemExit(f'docker build failed; see {output / f"build-{arch}.log"}')
            container = run('docker', 'create', '--platform', f'linux/{arch}', image, '/xs', '--version',
                            capture_output=True, text=True).stdout.strip()
            try:
                run('docker', 'cp', f'{container}:/xs', output / name)
                version = run('docker', 'start', '-a', container, capture_output=True, text=True).stdout
            finally:
                run('docker', 'rm', '-f', container, capture_output=True)
            (output / name).chmod(0o755)
            version = version.splitlines()[0] if version else ''
            if problem := version_problem(version, short, tunables):
                raise SystemExit(f'{name}: {problem}')
            artifacts[name] = {'sha256': sha256(output / name), 'bytes': (output / name).stat().st_size,
                               'version': version}
    record = {'revision': full, 'rev12': name_id, 'git': short, 'tunables': tunables, 'artifacts': artifacts,
              'dockerfile_sha256': hashlib.sha256(run('git', '-C', REPO, 'show', f'{full}:tools/release.Dockerfile',
                                                      capture_output=True).stdout).hexdigest(),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    (output / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    RECORDS.mkdir(parents=True, exist_ok=True)
    (RECORDS / f'{name_id}.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def version_problem(version, short, tunables=False):
    """Why a `--version` line is not the clean build of a revision, or None."""
    if not version:
        return 'does not run'
    if '-dirty' in version:
        return f'was built from a dirty tree ("{version}")'
    fields = version.split('  ')
    if f'git {short}' not in fields:
        return f'reports "{version}", expected git {short}'
    if ('tunables' in fields) != tunables:
        return f'is {"" if "tunables" in fields else "not "}a tunables build ("{version}")'
    return None


def script_hashes():
    return {path.name: sha256(path) for path in SCRIPTS}


def bundle_id(hashes=None):
    """The name of the script bundle: a hash of every script's name and contents."""
    hashes = script_hashes() if hashes is None else hashes
    return hashlib.sha256(json.dumps(sorted(hashes.items())).encode()).hexdigest()[:12]


def check_host(name, record, scripts, report):
    """Problems with what one host has staged, as a list of sentences."""
    if 'error' in report:
        return [f'{name}: {report["error"]}']
    short, binary = record['rev12'], f'xs-{record["rev12"]}'
    artifact = artifact_for(report.get('system', 'Linux'), report.get('machine'))
    if artifact not in record['artifacts']:
        return [f'{name}: no build for a {report.get("system", "Linux")} {report.get("machine")} host']
    problems = []
    found = report.get('files', {}).get(binary)
    if found is None:
        problems.append(f'{name}: {binary} is not staged')
    elif found != record['artifacts'][artifact]['sha256']:
        problems.append(f'{name}: {binary} is not the recorded build of {short} (stale or replaced)')
    elif problem := version_problem(report.get('versions', {}).get(binary), record.get('git', short),
                                    record.get('tunables', False)):
        problems.append(f'{name}: {binary} {problem}')
    for script, digest in scripts.items():
        found = report.get('files', {}).get(script)
        if found is None:
            problems.append(f'{name}: {script} is not staged')
        elif found != digest:
            problems.append(f'{name}: {script} differs from the working copy')
    if not report.get('rsync', {}).get('path'):
        problems.append(f'{name}: rsync is not installed')
    return problems


def staged_report(host, record):
    names = [f'xs-{record["rev12"]}', *script_hashes()]
    return preflight.probe(host, 'staged', '--root', host['root'], '--bundle', bundle_id(), *names)


def check(config, names, record):
    """Reports and problems for the named hosts."""
    reports, problems, scripts = {}, [], script_hashes()
    for name in names:
        reports[name] = staged_report(config['hosts'][name], record)
        problems += check_host(name, record, scripts, reports[name])
    return reports, problems


def push_bundle(name, host):
    """Put the current scripts on a host as ROOT/lib/<id>, unless that bundle is already there."""
    bundle = bundle_id()
    library = host['root'] + '/lib'
    final, incoming = f'{library}/{bundle}', f'{library}/{bundle}.incoming'
    if run_on(host, f'test -d {shlex.quote(final)}').returncode == 0:
        return bundle
    made = run_on(host, f'rm -rf {shlex.quote(incoming)} && mkdir -p {shlex.quote(incoming)}')
    if made.returncode:
        raise SystemExit(f'{name}: cannot create {incoming}: {made.stderr.strip()}')
    copy_to(host, SCRIPTS, incoming)
    report = preflight.probe(host, 'staged', '--root', host['root'], '--bundle', f'{bundle}.incoming', *script_hashes())
    if report.get('files') != script_hashes():
        raise SystemExit(f'{name}: the scripts arrived damaged; nothing was installed')
    # A directory rename is atomic, and a bundle is never written to again.
    moved = run_on(host, f'mv {shlex.quote(incoming)} {shlex.quote(final)}')
    if moved.returncode:
        raise SystemExit(f'{name}: {moved.stderr.strip()}')
    return bundle


def push(config, names, record):
    """Copy the build and the scripts to each host, verifying the binary before it takes its name."""
    short = record['rev12']
    for name in names:
        host = config['hosts'][name]
        system, machine = run_on(host, 'uname -s; uname -m', timeout=30).stdout.split() or (None, None)
        artifact = artifact_for(system, machine)
        if artifact not in record['artifacts']:
            raise SystemExit(f'{name}: no build for a {system or "unreachable"} {machine or ""} host')
        directory = host['root'] + '/bin'
        if run_on(host, f'mkdir -p {shlex.quote(directory)}/.incoming').returncode:
            raise SystemExit(f'{name}: cannot create {directory}')
        # Everything arrives beside its name and is renamed into place, so a run in progress
        # never executes a half-written file.
        staging = BUILDS / short / f'xs-{short}.incoming'
        shutil.copy2(BUILDS / short / artifact, staging)
        copy_to(host, [staging], directory)
        staging.unlink()
        push_bundle(name, host)
        report = preflight.probe(host, 'staged', '--root', host['root'], f'xs-{short}.incoming')
        if report.get('files', {}).get(f'xs-{short}.incoming') != record['artifacts'][artifact]['sha256']:
            raise SystemExit(f'{name}: the copy of {artifact} arrived damaged; nothing was replaced')
        moved = run_on(host, f'cd {shlex.quote(directory)} && chmod 755 xs-{short}.incoming && '
                             f'mv -f xs-{short}.incoming xs-{short}; rmdir .incoming 2>/dev/null; true')
        if moved.returncode:
            raise SystemExit(f'{name}: {moved.stderr.strip()}')
        print(f'{name}: staged xs-{short} ({artifact}) and script bundle {bundle_id()}', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command, text in (('build', 'build a commit for linux/amd64 and linux/arm64'),
                          ('push', 'copy a build and the lab scripts to the hosts'),
                          ('check', 'verify what the hosts have staged')):
        p = commands.add_parser(command, help=text)
        p.add_argument('--rev', default='HEAD', help='commit to build or stage (default HEAD)')
        if command == 'build':
            p.add_argument('--rebuild', action='store_true', help='replace an existing build of this commit')
        else:
            p.add_argument('--hosts', type=pathlib.Path, default=HERE / 'hosts.toml')
            p.add_argument('--host', action='append', help='host to act on (default: every host with a root)')
    args = parser.parse_args(argv)
    if args.command == 'build':
        record = build(args.rev, args.rebuild)
        for name, artifact in record['artifacts'].items():
            print(name, artifact['sha256'], artifact['version'])
        return
    try:
        config = preflight.load(args.hosts)
    except (OSError, preflight.ConfigError) as error:
        parser.error(str(error))
    names = args.host or [name for name, host in config['hosts'].items() if host.get('root')]
    if unknown := [name for name in names if not config['hosts'].get(name, {}).get('root')]:
        parser.error('no benchmark root declared for: ' + ', '.join(unknown))
    record = load_build(args.rev)
    if args.command == 'push':
        push(config, names, record)
    reports, problems = check(config, names, record)
    for name, report in reports.items():
        rsync = report.get('rsync', {})
        print(f'{name}: xs-{record["rev12"]} {(report.get("files", {}).get("xs-" + record["rev12"]) or "missing")[:16]}, '
              f'{rsync.get("version")} {(rsync.get("sha256") or "")[:16]}')
    for problem in problems:
        print('PROBLEM', problem)
    if problems:
        sys.exit(1)
    print(f'every host has the recorded build of {record["rev12"]}')


if __name__ == '__main__':
    main()
