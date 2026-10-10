#!/usr/bin/env python3
"""Summarize completed, independently verified pair measurements."""
import argparse
import json
import pathlib
import statistics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=pathlib.Path,default=pathlib.Path('benchmarks/results'))
    p.add_argument('--run-id',required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    args=p.parse_args()
    rows=[];corpora={}
    for path in sorted(args.results.glob(args.run_id+'-*.json')):
        data=json.loads(path.read_text())
        if 'dataset' in data and all(key in data for key in ('files','directories','bytes')):
            label=data['dataset']
            if label in corpora and any(corpora[label][key]!=data[key] for key in ('files','directories','bytes')):
                raise ValueError('endpoint dataset inventories differ: '+label)
            corpora[label]=data
        if not data.get('complete') or not data.get('summary') or 'label' not in data or data['label']=='smoke': continue
        records=data.get('records',[])
        if not records or not all(r.get('verified') and r.get('returncode')==0 and
                                   (not r.get('remote') or r['remote']['returncode']==0) for r in records):
            raise ValueError('unverified completed result: '+str(path))
        flow='neo → freya' if data['direction']=='push' else 'freya → neo'
        for summary in data['summary']:
            scenario=summary['scenario']
            samples={tool:[r for r in records if r['tool']==tool and r['scenario']==scenario] for tool in ('rsync','xs')}
            if not samples['xs'] or len(samples['xs'])!=len(samples['rsync']):raise ValueError('unbalanced sample counts')
            medians={tool:statistics.median(r['wall_seconds'] for r in values) for tool,values in samples.items()}
            totalcpu={tool:statistics.median(r['user_seconds']+r['system_seconds']+
                      (r['remote']['user_seconds']+r['remote']['system_seconds'] if r.get('remote') else 0) for r in values)
                      for tool,values in samples.items()}
            rss={tool:max(max(r['max_rss_bytes'],r['remote']['max_rss_bytes'] if r.get('remote') else 0) for r in values)/2**20
                 for tool,values in samples.items()}
            rows.append((data['label'],flow,data['cache'],scenario,len(samples['xs']),medians,medians['rsync']/medians['xs'],totalcpu,rss,path.name))
    lines=['# neo / freya benchmark results','',
           f'Run `{args.run_id}`. Times are medians of alternating-order samples; each completed sample passed `rsync -anci --delete` verification.',
           '', 'The client is neo for both flows (push to freya, pull from freya). Cache policy retains existing OS caches unless explicitly recorded otherwise. Setup, cleanup and checksum verification are excluded from transfer timings.','',
           '| Dataset | Files | Directories | Logical bytes |','|---|---:|---:|---:|']
    for label,data in sorted(corpora.items()): lines.append(f"| {label} | {data['files']:,} | {data['directories']:,} | {data['bytes']:,} |")
    lines+=['','| Dataset | Data flow | Cache | Scenario | Runs/tool | rsync s | xs s | xs speedup | CPU s rsync / xs | Peak MiB rsync / xs | Evidence |',
            '|---|---|---|---|---:|---:|---:|---:|---:|---:|---|']
    for label,flow,cache,scenario,n,med,ratio,cpu,rss,evidence in rows:
        lines.append(f"| {label} | {flow} | {cache} | {scenario} | {n} | {med['rsync']:.3f} | {med['xs']:.3f} | {ratio:.2f}× | {cpu['rsync']:.3f} / {cpu['xs']:.3f} | {rss['rsync']:.1f} / {rss['xs']:.1f} | [{evidence}]({evidence}) |")
    lines+=['','CPU is summed across the measured client and peer process trees. Peak RSS is the larger endpoint peak, not their sum. Filesystem/NIC/tool/source metadata accompanies the JSON files. Incomplete runs and smoke checks are excluded.','']
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text('\n'.join(lines))
    print(f'{len(rows)} completed scenario rows: {args.output}')


if __name__=='__main__': main()
