#!/usr/bin/env python3
"""Verified, interleaved local or direct SSH benchmarks with JSON evidence."""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import re
import shlex
import shutil
import socket
import statistics
import subprocess
import sys
import time

from measure import measure


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', required=True, type=pathlib.Path)
    p.add_argument('--base-corpus', type=pathlib.Path, help='unmodified source used to seed update runs')
    p.add_argument('--work', required=True, type=pathlib.Path)
    p.add_argument('--target', help='user@host:absolute-owned-benchmark-root')
    p.add_argument('--direction', choices=('push','pull'), default='push')
    p.add_argument('--xsync', default='xs')
    p.add_argument('--rsync', default='rsync')
    p.add_argument('--remote-xs', default='xs')
    p.add_argument('--remote-rsync', default='rsync')
    p.add_argument('--remote-measure', help='remote path to benchmarks/measure.py')
    p.add_argument('--rsh', default='ssh -oBatchMode=yes -oCompression=no -oControlMaster=no -oConnectTimeout=10')
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--scenarios', default='fresh,fresh-z,noop,checksum')
    p.add_argument('--threads', type=int)
    p.add_argument('--label', default='corpus')
    p.add_argument('--cache', choices=('warm','cold'), default='warm')
    p.add_argument('--cold-command', help='local cache reset command, run untimed before every sample')
    p.add_argument('--remote-cold-command', help='remote cache reset command, run untimed before every sample')
    p.add_argument('--output', required=True, type=pathlib.Path)
    args=p.parse_args(argv)
    scenarios=args.scenarios.split(',')
    allowed={'fresh','fresh-z','noop','checksum','update-1pct','delete','tiny'}
    if not scenarios or any(s not in allowed for s in scenarios): p.error('unknown scenario')
    if args.runs<1: p.error('--runs must be positive')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,80}',args.label): p.error('--label must be a safe file name')
    if args.cache=='cold' and (not args.cold_command or (args.target and not args.remote_cold_command)):
        p.error('cold measurements require explicit cache-reset commands on both endpoints')
    if args.direction=='pull' and not args.target: p.error('--direction=pull requires --target')
    corpus=args.corpus.resolve(); work=args.work.resolve()
    if work==corpus or work in corpus.parents or corpus in work.parents: p.error('work and source must be disjoint')
    if not corpus.is_dir(): p.error('source corpus is missing')
    host=remote_root=None
    if args.target:
        host,sep,remote_root=args.target.partition(':')
        if not sep or not host or host.startswith('-') or not remote_root.startswith('/'): p.error('--target requires host:absolute-path')
        if not args.remote_measure: p.error('--target requires --remote-measure for receiver/sender resource evidence')
    work.mkdir(parents=True,exist_ok=True)
    marker=work/'.xs-benchmark-work'
    if any(work.iterdir()) and not marker.exists(): p.error('nonempty work directory has no benchmark ownership marker')
    marker.write_text('owned by benchmarks/run.py\n')
    lock=(work/'.xs-benchmark-lock').open('a+')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: p.error('another benchmark owns this work directory')
    rsh=shlex.split(args.rsh)
    def remote(command, **kwargs):
        return subprocess.run([*rsh,host,command],check=True,**kwargs)
    if host:
        remote('mkdir -p '+shlex.quote(remote_root),capture_output=True)
        # A benchmark root must have been staged explicitly by the operator.
        remote('test -f '+shlex.quote(remote_root+'/.xsync-benchmark-owner.json'),capture_output=True)
        remote('mkdir -p '+shlex.quote(remote_root+'/work')+' '+shlex.quote(remote_root+'/logs'),capture_output=True)
    src=str(corpus)+'/'
    base=str((args.base_corpus or corpus).resolve())+'/'
    def paths(target_name, source=src):
        destination=str(work/target_name)+'/'
        if host and args.direction=='push': destination=host+':'+remote_root+'/work/'+target_name+'/'
        elif host: source=host+':'+source
        return source,destination
    def wipe(name):
        if host and args.direction=='push':
            # Only descendants of the owned root/work are eligible for removal.
            remote('rm -rf -- '+shlex.quote(remote_root+'/work/'+name),capture_output=True)
        else: shutil.rmtree(work/name,ignore_errors=True)
    def build(tool, flags, name, source=src, *, measured=True):
        command=[args.rsync if tool=='rsync' else args.xsync,*flags]
        if tool=='xs':
            command += ['--no-fallback','--no-progress']
            if args.threads: command += ['-j'+str(args.threads)]
        if host:
            program=args.remote_rsync if tool=='rsync' else args.remote_xs
            if measured:
                program=shlex.join(['python3',args.remote_measure,'--metrics',remote_root+'/logs/'+name+'-remote.json','--',program])
            command += ['-e',args.rsh,'--rsync-path='+program]
        return command+list(paths(name,source))
    def verify(name):
        result=subprocess.run(build('rsync',['-anci','--delete'],name,measured=False),capture_output=True,text=True)
        if result.returncode or result.stdout.strip():
            raise RuntimeError('verification failed: '+result.stdout[:4000]+result.stderr[:4000])
    records=[]
    versions={tool:subprocess.check_output([binary,'--version'],text=True).splitlines()[0]
              for tool,binary in [('xs',args.xsync),('rsync',args.rsync)]}
    metadata={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'client':socket.gethostname(),
              'target':args.target,'direction':args.direction,'label':args.label,'cache':args.cache,
              'versions':versions,'argv':sys.argv,'records':records}
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(metadata,indent=2)+'\n')
    save()
    flags={'fresh':['-a'],'fresh-z':['-az'],'noop':['-a'],'checksum':['-ac'],
           'update-1pct':['-a'],'delete':['-a','--delete'],'tiny':['-a']}
    for scenario in scenarios:
        for run in range(args.runs):
            # Alternate the first tool to distribute order/warmup effects.
            for tool in (['rsync','xs'] if run%2==0 else ['xs','rsync']):
                name=f'{args.label}-{scenario}-{tool}'
                tag=name+'-'+str(run+1)
                if run==0 or scenario in ('fresh','fresh-z','tiny'): wipe(name)
                if (run==0 and scenario in ('noop','checksum')) or scenario in ('update-1pct','delete'):
                    seed_source=base if scenario in ('update-1pct','delete') else src
                    subprocess.run(build('rsync',['-a','--delete'],name,seed_source,measured=False),check=True,stdout=subprocess.DEVNULL)
                if args.cache=='cold':
                    subprocess.run(shlex.split(args.cold_command),check=True)
                    if host: remote(args.remote_cold_command)
                stdout=work/(tag+'.stdout');stderr=work/(tag+'.stderr')
                with stdout.open('wb') as out,stderr.open('wb') as err:
                    result=measure(build(tool,flags[scenario]+['--stats'],name),stdout=out,stderr=err)
                if result['returncode']:
                    metadata['failed_sample']={'name':tag,'metrics':result,'stderr':stderr.read_text(errors='replace')[:4000]}
                    save()
                    raise RuntimeError(f'{name} failed: '+repr(metadata['failed_sample']))
                peer=None
                if host:
                    peer=json.loads(remote('cat '+shlex.quote(remote_root+'/logs/'+name+'-remote.json'),capture_output=True,text=True).stdout)
                    if peer['returncode']: raise RuntimeError('remote helper failed: '+repr(peer))
                verify(name)
                result.update({'scenario':scenario,'tool':tool,'run':run+1,'verified':True,'remote':peer,
                               'stdout':stdout.read_text(errors='replace'),'stderr':stderr.read_text(errors='replace')})
                records.append(result);save()
                print(f"{args.label} {args.direction} {scenario} {tool} {run+1}/{args.runs}: {result['wall_seconds']:.3f}s verified",flush=True)
                if scenario in ('fresh','fresh-z','tiny') or run==args.runs-1: wipe(name)
    summary=[]
    for scenario in scenarios:
        samples={tool:[r['wall_seconds'] for r in records if r['scenario']==scenario and r['tool']==tool] for tool in ('rsync','xs')}
        medians={tool:statistics.median(values) for tool,values in samples.items()}
        summary.append({'scenario':scenario,'median_seconds':medians,'xs_speedup':medians['rsync']/medians['xs']})
    metadata['summary']=summary;metadata['complete']=True;save()
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
