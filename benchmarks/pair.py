#!/usr/bin/env python3
"""Run the prepared neo/freya suite sequentially; keep durable local evidence."""
import argparse
import json
import pathlib
import shlex
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=pathlib.Path,default=pathlib.Path('.bench/p3-state.json'))
    p.add_argument('--datasets',default='mixed,large,tiny,congress,update-1pct')
    p.add_argument('--runs',type=int,default=3)
    p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('benchmarks/results'))
    args=p.parse_args();state=json.loads(args.state.read_text());root=state['root']
    scenarios={'mixed':'fresh,fresh-z,noop,checksum','large':'fresh,fresh-z,noop,checksum',
               'tiny':'tiny','congress':'fresh,fresh-z,noop,checksum','update-1pct':'update-1pct'}
    for dataset in args.datasets.split(','):
        if dataset not in scenarios: p.error('unknown dataset '+dataset)
    args.output.mkdir(parents=True,exist_ok=True)
    for dataset in args.datasets.split(','):
        for direction in ('push','pull'):
            name=state['run_id']+'-'+dataset+'-'+direction
            destination=args.output/(name+'.json')
            if destination.exists() and json.loads(destination.read_text()).get('complete'):
                print('Already completed: '+name,flush=True);continue
            remote_output=root+'/logs/'+dataset+'-'+direction+'.json'
            command=['python3',root+'/bin/run.py','--corpus',root+'/data/'+dataset,
                     '--work',root+'/work','--target',state['freya']+':'+root,'--direction',direction,
                     '--xsync',root+'/bin/xs','--remote-xs',root+'/bin/xs',
                     '--remote-measure',root+'/bin/measure.py','--runs',str(args.runs),
                     '--scenarios',scenarios[dataset],'--label',dataset,'--output',remote_output]
            if dataset=='update-1pct':command+=['--base-corpus',root+'/data/congress']
            print('Starting '+name,flush=True)
            with (args.output/(name+'.log')).open('w') as log:
                child=subprocess.Popen(['ssh','-oBatchMode=yes',state['neo'],shlex.join(command)],
                                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
                try:
                    for line in child.stdout:
                        log.write(line);log.flush();print(line,end='',flush=True)
                    status=child.wait()
                finally:
                    child.stdout.close()
                    subprocess.run(['scp','-q',state['neo']+':'+remote_output,str(destination)],check=False)
                if status:sys.exit(status)
    print('Prepared pair suite complete.',flush=True)


if __name__=='__main__': main()
