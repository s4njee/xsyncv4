#!/usr/bin/env python3
"""Compare corrected APFS clones with the old binary and byte copies."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shlex
import shutil
import stat
import statistics
import subprocess

from measure import measure


def metadata(root):
    result = {}
    for path in [root, *sorted(root.rglob('*'))]:
        st = path.lstat()
        result[str(path.relative_to(root))] = [st.st_mode, st.st_uid, st.st_gid, st.st_mtime_ns,
                                             st.st_size if stat.S_ISREG(st.st_mode) else
                                             os.readlink(path) if stat.S_ISLNK(st.st_mode) else None]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=pathlib.Path, required=True)
    parser.add_argument('--reference', type=pathlib.Path, required=True)
    parser.add_argument('--rsync', default='rsync')
    parser.add_argument('--work', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--runs', type=int, default=5)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or args.runs < 1:
        parser.error('requires macOS and at least one sample')
    os.umask(0o77)
    os.environ['XSYNC_CONFIG'] = os.environ['XSYNC_OPTS'] = ''
    work = args.work.resolve()
    if work.exists() and any(work.iterdir()): parser.error('use a fresh empty work directory')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.xs-clone-modes-owned').write_text('created by clone_modes.py\n')
    binaries = {'reference': str(args.reference.resolve()), 'candidate': str(args.candidate.resolve()),
                'byte-copy': str(args.candidate.resolve()), 'rsync': shutil.which(args.rsync) or args.rsync}
    result = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'platform': platform.platform(), 'host': platform.node(), 'cpus': os.cpu_count(),
              'initial_loadavg': list(os.getloadavg()),
              'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
              'cache': 'retained OS caches', 'umask': '0077', 'jobs': 4,
              'disk': subprocess.check_output(['df', '-k', str(work)], text=True),
              'binaries': {name: {'sha256': hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),
                                  'version': subprocess.check_output([binary, '--version'], text=True).splitlines()[0]}
                           for name, binary in binaries.items()}, 'records': []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(result, indent=2) + '\n')
        temp.replace(args.output)
    save()
    try:
        sources = work / 'sources'
        sources.mkdir()
        large = sources / 'large'
        large.mkdir()
        block = b'corrected read-only clone\n' * 41943
        block = (block + bytes(2**20))[:2**20]
        with (large / 'read-only.bin').open('wb') as out:
            for _ in range(1024): out.write(block)
        (large / 'read-only.bin').chmod(0o444)
        small = sources / 'small'
        small.mkdir()
        for number in range(1000):
            parent = small / f'leaf-{number//25:02}'
            parent.mkdir(exist_ok=True)
            path = parent / f'file-{number:04}.json'
            path.write_bytes(block[:65536])
            path.chmod(0o444 if number % 2 else 0o644)
        (small / 'link').symlink_to('leaf-00/file-0000.json')
        for path in [large, small, *large.rglob('*'), *small.rglob('*')]:
            os.utime(path, ns=(1500000000123456789, 1500000000123456789), follow_symlinks=False)
        result['fixtures'] = {'large': {'files': 1, 'logical_bytes': 2**30},
                              'small': {'files': 1000, 'directories': 40, 'symlinks': 1, 'logical_bytes': 65536000}}
        tools = list(binaries)
        for source in (large, small):
            before = metadata(source)
            for flag in ('-rt', '-rlt'):
                oracle = work / 'oracle'
                subprocess.run([binaries['rsync'], flag, str(source) + '/', str(oracle) + '/'],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, umask=0o77)
                expected = metadata(oracle)
                for run in range(args.runs):
                    order = tools[run % len(tools):] + tools[:run % len(tools)]
                    if run % 2: order.reverse()
                    for tool in order:
                        dest = work / 'destination'
                        command = [binaries[tool], flag]
                        if tool != 'rsync':
                            command += ['--no-fallback', '--no-progress', '-j4']
                            if tool == 'byte-copy': command += ['--no-clone']
                        command += [str(source) + '/', str(dest) + '/']
                        log = work / f'{source.name}-{flag[1:]}-{tool}-{run+1}'
                        with log.with_suffix('.stdout').open('wb') as out, log.with_suffix('.stderr').open('wb') as err:
                            metrics = measure(command, stdout=out, stderr=err)
                        if metrics['returncode']: raise RuntimeError('transfer failed: ' + shlex.join(command))
                        # The oracle embodies rsync's selection and creation
                        # semantics (-rt deliberately omits source symlinks).
                        verified = subprocess.run([binaries['rsync'], '-acni', '--delete', str(oracle) + '/', str(dest) + '/'],
                                                  capture_output=True, text=True)
                        if verified.returncode or verified.stdout.strip() or metadata(dest) != expected:
                            raise RuntimeError('checksum or metadata verification failed: ' + verified.stdout + verified.stderr)
                        if metadata(source) != before: raise RuntimeError('source metadata changed')
                        metrics.update({'dataset': source.name, 'flags': flag, 'tool': tool, 'run': run + 1,
                                        'verified': True, 'command': command})
                        result['records'].append(metrics)
                        save()
                        print(f'{source.name} {flag} {tool} {run+1}: {metrics["wall_seconds"]:.4f}s verified', flush=True)
                        shutil.rmtree(dest)
                shutil.rmtree(oracle)
        result['medians'] = [{'dataset': dataset, 'flags': flag,
                              'seconds': {tool: statistics.median(r['wall_seconds'] for r in result['records']
                                          if r['dataset'] == dataset and r['flags'] == flag and r['tool'] == tool)
                                          for tool in binaries}}
                             for dataset in ('large', 'small') for flag in ('-rt', '-rlt')]
        result['complete'] = True
        result['final_loadavg'] = list(os.getloadavg())
        save()
        shutil.rmtree(sources)
        return 0
    except Exception as error:
        result['error'] = str(error)
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
