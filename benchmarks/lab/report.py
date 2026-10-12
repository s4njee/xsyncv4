#!/usr/bin/env python3
"""Write an experiment's analysis as a Markdown report.

Runs analyze.py's analysis over every fetched run of the experiment, saves
its tables, and renders EXPERIMENT/report.md from them.
"""
import argparse
import pathlib

import analyze


def ratio(row, prefix=''):
    """'0.912 [0.880, 0.945]', or the estimate alone when there is no interval."""
    centre, low, high = row[prefix + 'ratio'], row[prefix + 'lo'], row[prefix + 'hi']
    if centre is None:
        return ''
    return f'{centre:.3f}' if low is None else f'{centre:.3f} [{low:.3f}, {high:.3f}]'


def seconds(value):
    return f'{value:.3f}' if value < 100 else f'{value:.1f}'


def table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join('---' for _ in header) + '|']
    return lines + ['| ' + ' | '.join(str(cell) for cell in row) + ' |' for row in rows]


def render(result):
    summary, effects = result['summary'], result['effects']
    primary = [row for row in effects if row['primary']]
    lines = [f'# {summary["experiment"]}', '', summary['hypothesis'] or '', '',
             f'- Kind: {summary["kind"]}. Primary metric: `{summary["primary"]}`. Control arm: `{summary["control"]}`.',
             f'- Smallest effect of interest: {summary["delta"]:.0%}. Interval level: {summary["level"]:.1%}'
             + (f' ({summary["looks"]} declared looks).' if summary['looks'] > 1 else '.'),
             f'- Runs: {", ".join(summary["runs"])}.',
             f'- Valid blocks: {summary["valid_blocks"]}. Voided block attempts: {summary["void_attempts"]}.']
    if len(summary['spec_sha256']) > 1:
        lines.append('- **The runs were made from different versions of the spec.**')
    if any(row['verdict'] == 'too few blocks' for row in primary):
        lines.append(f'- **Fewer than {analyze.MIN_BLOCKS} blocks in some cells: estimates only, no verdict.**')
    lines += ['', '## Ratio to the control', '',
              'Time of the arm divided by time of the control in the same block; below 1 is faster. '
              'The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate '
              'with its distribution-free interval.', '']
    adjusted = summary['kind'] == 'confirmatory'
    header = ['Cell', 'Arm', 'Blocks', 'Ratio', 'Robust', 'p'] + (['p (Holm)'] if adjusted else []) + ['Verdict']
    rows = []
    for row in primary:
        p = '' if row['p'] is None else f'{row["p"]:.4f}'
        holm = ['' if row['p_holm'] is None else f'{row["p_holm"]:.4f}'] if adjusted else []
        rows.append([f'`{row["cell_id"]}`', row['arm'], row['n_blocks'], ratio(row), ratio(row, 'hl_'), p, *holm,
                     row['verdict']])
    lines += table(header, rows)
    if not adjusted:
        lines += ['', 'This is a screening experiment: the p-values are unadjusted and nothing here is a claim. '
                  'A candidate is re-measured in a confirmatory run.']
    secondary = sorted({row['metric'] for row in effects if not row['primary']})
    if secondary:
        lines += ['', '## Other metrics', '', 'Descriptive only; the same ratio and interval for each.', '']
        wide = {}
        for row in effects:
            if not row['primary']:
                wide.setdefault((row['cell_id'], row['arm']), {})[row['metric']] = ratio(row)
        lines += table(['Cell', 'Arm'] + [f'`{metric}`' for metric in secondary],
                       [[f'`{cell}`', arm] + [values.get(metric, '') for metric in secondary]
                        for (cell, arm), values in wide.items()])
    lines += ['', f'## Absolute `{summary["primary"]}`', '', 'Geometric mean over valid blocks, in seconds.', '']
    absolute = {}
    for row in result['absolutes']:
        if row['metric'] == summary['primary']:
            absolute.setdefault(row['cell_id'], {})[row['arm']] = seconds(row['geomean'])
    arms = sorted({arm for values in absolute.values() for arm in values})
    lines += table(['Cell'] + arms, [[f'`{cell}`'] + [values.get(arm, '') for arm in arms]
                                     for cell, values in absolute.items()])
    if result['noise']:
        lines += ['', '## Noise', '',
                  'Standard deviation of the block log-ratios, and the blocks that would give 80% power for the '
                  '95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.', '']
        lines += table(['Cell', 'Arm', 'sigma_d', 'Blocks to detect 3%', 'Blocks for equivalent at 3%'],
                       [[f'`{row["cell_id"]}`', row['arm'], f'{row["sigma_d"]:.4f}', row['blocks_for_3pct'],
                         row['blocks_equivalent_3pct']] for row in result['noise']])
    if summary['void_reasons']:
        lines += ['', '## Voided attempts', ''] + [f'- {reason}' for reason in summary['void_reasons']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=pathlib.Path, help='benchmarks/results/lab/EXPERIMENT')
    parser.add_argument('--delta', type=float)
    parser.add_argument('--looks', type=int, default=1)
    parser.add_argument('--control', help='compare against this arm instead of the spec\'s control')
    args = parser.parse_args(argv)
    directories = analyze.run_directories(args.experiment)
    if not directories:
        parser.error('no fetched runs under ' + str(args.experiment))
    result = analyze.analyse(directories, args.delta, args.looks, args.control)
    analyze.write(result, args.experiment / analyze.output_name('analysis', args.control))
    output = args.experiment / (analyze.output_name('report', args.control) + '.md')
    output.write_text(render(result))
    print(output)


if __name__ == '__main__':
    main()
