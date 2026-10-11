#!/usr/bin/env python3
"""Build xs from a commit and stage it, with the lab's scripts, on the benchmark hosts.

A build is made from `git archive` of a commit, never from the working tree,
so a binary cannot contain uncommitted changes. Each host keeps it as
ROOT/bin/xs-<rev12>; `check` refuses a host whose copy is missing, is not
byte-for-byte the recorded build, or reports another or a dirty revision.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

import preflight

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
BUILDS = REPO / '.bench' / 'lab' / 'builds'             # binaries, not tracked
RECORDS = HERE.parent / 'results' / 'lab' / 'builds'    # their hashes, tracked
ARCHES = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
SCRIPTS = (HERE / 'probe.py', HERE / 'corpus.py', HERE / 'corpora.json', HERE.parent / 'measure.py')


def run(*command, **options):
    return subprocess.run(list(map(str, command)), check=True, **options)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def resolve(revision):
    """The full hash of a commit, or exit."""
    done = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--verify', '--quiet', revision + '^{commit}'],
                          capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f'{revision} is not a commit')
    return done.stdout.strip()


def load_build(revision):
    record = BUILDS / resolve(revision)[:12] / 'build.json'
    if not record.exists():
        raise SystemExit(f'{revision} has not been built: run stage.py build --rev {revision}')
    return json.loads(record.read_text())


def build(revision, rebuild=False):
    """Build the static Linux release of a commit for both architectures."""
    full = resolve(revision)
    short = full[:12]
    output = BUILDS / short
    if (output / 'build.json').exists() and not rebuild:
        return json.loads((output / 'build.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    with tempfile.TemporaryDirectory() as source:
        archive = subprocess.Popen(['git', '-C', str(REPO), 'archive', '--format=tar', full], stdout=subprocess.PIPE)
        run('tar', '-x', '-C', source, stdin=archive.stdout)
        if archive.wait():
            raise SystemExit('git archive failed')
        for arch in ('amd64', 'arm64'):
            image, name = f'xsbench-xs-{short}-{arch}', f'xs-linux-{arch}'
            print(f'building {name} from {short}', flush=True)
            with open(output / f'build-{arch}.log', 'w') as log:
                done = subprocess.run(['docker', 'build', '--platform', f'linux/{arch}', '--build-arg',
                                       f'XSYNC_GIT_HASH={short}', '-t', image, '-f',
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
            if problem := version_problem(version, short):
                raise SystemExit(f'{name}: {problem}')
            artifacts[name] = {'sha256': sha256(output / name), 'bytes': (output / name).stat().st_size,
                               'version': version}
    record = {'revision': full, 'rev12': short, 'artifacts': artifacts,
              'dockerfile_sha256': hashlib.sha256(run('git', '-C', REPO, 'show', f'{full}:tools/release.Dockerfile',
                                                      capture_output=True).stdout).hexdigest(),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    (output / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    RECORDS.mkdir(parents=True, exist_ok=True)
    (RECORDS / f'{short}.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def version_problem(version, short):
    """Why a `--version` line is not the clean build of a revision, or None."""
    if not version:
        return 'does not run'
    if '-dirty' in version:
        return f'was built from a dirty tree ("{version}")'
    if f'git {short}' not in version.split('  '):
        return f'reports "{version}", expected git {short}'
    return None


def script_hashes():
    return {path.name: sha256(path) for path in SCRIPTS}


def check_host(name, record, scripts, report):
    """Problems with what one host has staged, as a list of sentences."""
    if 'error' in report:
        return [f'{name}: {report["error"]}']
    short, binary = record['rev12'], f'xs-{record["rev12"]}'
    arch = ARCHES.get(report.get('machine'))
    if not arch:
        return [f'{name}: no build for a {report.get("machine")} host']
    problems = []
    found = report.get('files', {}).get(binary)
    if found is None:
        problems.append(f'{name}: {binary} is not staged')
    elif found != record['artifacts'][f'xs-linux-{arch}']['sha256']:
        problems.append(f'{name}: {binary} is not the recorded build of {short} (stale or replaced)')
    elif problem := version_problem(report.get('versions', {}).get(binary), short):
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
    return preflight.probe(host, 'staged', '--root', host['root'], *names)


def check(config, names, record):
    """Reports and problems for the named hosts."""
    reports, problems, scripts = {}, [], script_hashes()
    for name in names:
        reports[name] = staged_report(config['hosts'][name], record)
        problems += check_host(name, record, scripts, reports[name])
    return reports, problems


def push(config, names, record):
    """Copy the build and the scripts to each host, verifying the binary before it takes its name."""
    short = record['rev12']
    for name in names:
        host = config['hosts'][name]
        machine = subprocess.run([*preflight.SSH, host['ssh'], 'uname', '-m'], capture_output=True, text=True,
                                 timeout=30).stdout.strip()
        arch = ARCHES.get(machine)
        if not arch:
            raise SystemExit(f'{name}: no build for a {machine or "unreachable"} host')
        artifact, directory = f'xs-linux-{arch}', host['root'] + '/bin'
        run(*preflight.SSH, host['ssh'], 'mkdir', '-p', directory)
        run('scp', '-q', '-oBatchMode=yes', BUILDS / short / artifact, f'{host["ssh"]}:{directory}/xs-{short}.incoming')
        run('scp', '-q', '-oBatchMode=yes', *SCRIPTS, f'{host["ssh"]}:{directory}/')
        report = preflight.probe(host, 'staged', '--root', host['root'], f'xs-{short}.incoming')
        if report.get('files', {}).get(f'xs-{short}.incoming') != record['artifacts'][artifact]['sha256']:
            raise SystemExit(f'{name}: the copy of {artifact} arrived damaged; nothing was replaced')
        run(*preflight.SSH, host['ssh'], f'chmod 755 {directory}/xs-{short}.incoming && '
            f'mv -f {directory}/xs-{short}.incoming {directory}/xs-{short}')
        print(f'{name}: staged xs-{short} ({artifact}) and {len(SCRIPTS)} scripts', flush=True)


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
