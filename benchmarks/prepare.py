#!/usr/bin/env python3
"""Create owned benchmark fixtures without modifying the source corpus."""
import argparse
import hashlib
import json
import os
import pathlib
import random
import shutil
import stat
import subprocess
import time


def inventory(root):
    files=directories=size=0
    for parent,children,names in os.walk(root):
        children.sort(); names.sort(); directories+=len(children)
        for name in names:
            entry=(pathlib.Path(parent)/name).lstat()
            if stat.S_ISREG(entry.st_mode): files+=1;size+=entry.st_size
    return {'files':files,'directories':directories,'bytes':size}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=pathlib.Path)
    p.add_argument('--source',type=pathlib.Path)
    p.add_argument('--dataset',choices=('congress','mixed','large','tiny','update-1pct'),required=True)
    args=p.parse_args();root=args.root.resolve()
    if not (root/'.xsync-benchmark-owner.json').is_file(): p.error('missing ownership marker')
    target=root/'data'/args.dataset
    if target.exists(): p.error('dataset already exists; reuse it instead of overwriting')
    if args.dataset=='congress':
        if not args.source or not args.source.is_dir(): p.error('--source must name the original data directory')
        subprocess.run(['cp','-a','--reflink=auto',str(args.source),str(target)],check=True)
    elif args.dataset=='update-1pct':
        base=root/'data/congress'
        if not base.is_dir(): p.error('congress baseline is missing')
        subprocess.run(['cp','-al',str(base),str(target)],check=True)
        visited=changed=0
        for parent,children,names in os.walk(target):
            children.sort(); names.sort()
            for name in names:
                q=pathlib.Path(parent)/name;info=q.lstat()
                if not stat.S_ISREG(info.st_mode): continue
                visited+=1
                if visited%100: continue
                # Replace the shared inode; never write through a baseline link.
                temporary=q.with_name(q.name+'.xs-bench-update')
                with q.open('rb') as src,temporary.open('wb') as dest:
                    prefix=src.read(32)
                    if prefix: dest.write(bytes([prefix[0]^1])+prefix[1:])
                    else: dest.write(b'x')
                    shutil.copyfileobj(src,dest,1024*1024)
                os.chmod(temporary,stat.S_IMODE(info.st_mode))
                os.utime(temporary,ns=(info.st_atime_ns,info.st_mtime_ns+2_000_000_000))
                temporary.replace(q);changed+=1
        (root/'logs/update-selection.json').write_text(json.dumps({'files':visited,'changed':changed,'fraction':changed/visited})+'\n')
    else:
        target.mkdir(parents=True)
        rng=random.Random(20261010)
        if args.dataset=='tiny': (target/'file').write_bytes(b'one small transfer\n')
        if args.dataset=='mixed':
            for d in range(100):
                parent=target/f'dir-{d:03d}';parent.mkdir()
                for n in range(100): (parent/f'file-{n:03d}').write_bytes((f'{d}:{n}:'.encode()*1024)[:4096])
        if args.dataset in ('mixed','large'):
            amount=(256 if args.dataset=='mixed' else 1024)*1024*1024
            for name in ('compressible','random'):
                with (target/(name+'.bin')).open('wb') as out:
                    for offset in range(0,amount,1024*1024):
                        out.write(b'x'*(1024*1024) if name=='compressible' else rng.randbytes(1024*1024))
    metadata=inventory(target);metadata.update({'dataset':args.dataset,'path':str(target),'prepared_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    (root/'logs'/('dataset-'+args.dataset+'.json')).write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata),flush=True)


if __name__=='__main__': main()
