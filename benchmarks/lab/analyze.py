#!/usr/bin/env python3
"""Estimate each arm's time ratio to the control from the valid blocks of an experiment.

The unit of replication is the block. For a cell and an arm, each block gives
one paired log-ratio, ln(arm) - ln(control). The estimate is their mean,
exponentiated; the interval is the paired t interval; a Hodges-Lehmann
estimate with its distribution-free interval and an exact sign-flip test are
the robust check. A verdict compares the interval with the declared smallest
effect of interest, and needs both intervals to agree.

Standard library only. Writes effects, absolutes, pairs and noise tables as
JSON and CSV under EXPERIMENT/analysis/.
"""
import argparse
import csv
import functools
import json
import math
import pathlib
import random
import statistics
import sys

MIN_BLOCKS = 8
ALPHA = 0.05
EXACT_FLIPS = 20            # sign patterns are enumerated up to 2**20
FLIP_SAMPLES = 100_000
SECONDARY = ('wall_s', 'durable_s', 'cpu_s', 'rss_bytes')
CELL_FIELDS = ('corpus', 'scenario', 'sender', 'receiver', 'client', 'link', 'cache')
METRICS = {
    'wall_s': lambda s: s['wall_s'],
    'durable_s': lambda s: s['durable_s'],
    'cpu_s': lambda s: sum(s[end]['user_seconds'] + s[end]['system_seconds'] for end in ('client', 'peer')),
    'rss_bytes': lambda s: max(s['client']['max_rss_bytes'], s['peer']['max_rss_bytes']),
    'wire_bytes': lambda s: s['stats']['total_bytes_sent'] + s['stats']['total_bytes_received'],
}


# -- distributions ---------------------------------------------------------

def _beta_fraction(a, b, x):
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    result = d
    for m in range(1, 400):
        for numerator in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
                          -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):
            d = 1.0 + numerator * d
            c = 1.0 + numerator / c
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = c if abs(c) > tiny else tiny
            result *= d * c
        if abs(d * c - 1.0) < 1e-15:
            break
    return result


def beta_inc(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_fraction(a, b, x) / a
    return 1.0 - front * _beta_fraction(b, a, 1.0 - x) / b


def t_cdf(value, df):
    tail = 0.5 * beta_inc(df / 2.0, 0.5, df / (df + value * value))
    return 1.0 - tail if value > 0 else tail


def t_quantile(probability, df):
    """Student's t quantile for probability > 0.5, by bisection on the CDF."""
    low, high = 0.0, 1.0
    while t_cdf(high, df) < probability:
        high *= 2.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if t_cdf(middle, df) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


@functools.lru_cache(maxsize=None)
def signed_rank_cdf(n):
    """P(W+ <= k) for k = 0..n(n+1)/2 under the null, exactly."""
    counts = [1] + [0] * (n * (n + 1) // 2)
    for rank in range(1, n + 1):
        for total in range(len(counts) - 1, rank - 1, -1):
            counts[total] += counts[total - rank]
    cumulative, running = [], 0
    for count in counts:
        running += count
        cumulative.append(running / 2 ** n)
    return cumulative


# -- estimators ------------------------------------------------------------

def hodges_lehmann(differences, alpha):
    """(estimate, low, high): the median of the Walsh averages and its exact interval.

    The bounds are None when no interval of that confidence exists, which is
    the case below six differences at alpha 0.05.
    """
    n = len(differences)
    walsh = sorted((differences[i] + differences[j]) / 2.0 for i in range(n) for j in range(i, n))
    estimate = statistics.median(walsh)
    cdf = signed_rank_cdf(n)
    cut = max((k for k in range(len(cdf)) if cdf[k] <= alpha / 2.0), default=None)
    if cut is None:
        return estimate, None, None
    return estimate, walsh[cut], walsh[len(walsh) - 1 - cut]


def sign_flip_p(differences):
    """Two-sided p-value of the mean under random sign flips of the block differences."""
    n, observed = len(differences), abs(sum(differences))
    threshold = observed * (1.0 - 1e-12)
    if n <= EXACT_FLIPS:
        signs, total, extreme = [1] * n, sum(differences), 0
        for pattern in range(1 << n):
            if pattern:
                bit = (pattern & -pattern).bit_length() - 1  # Gray code: one sign changes per step
                signs[bit] = -signs[bit]
                total += 2 * signs[bit] * differences[bit]
            extreme += abs(total) >= threshold
        return extreme / (1 << n)
    generator, extreme = random.Random(20261011), 0
    for _ in range(FLIP_SAMPLES):
        bits = generator.getrandbits(n)
        extreme += abs(sum(d if bits >> i & 1 else -d for i, d in enumerate(differences))) >= threshold
    return (extreme + 1) / (FLIP_SAMPLES + 1)


def classify(low, high, delta):
    """Where an interval of ratios lies relative to the smallest effect of interest."""
    if high < 1.0 / (1.0 + delta):
        return 'faster'
    if low > 1.0 + delta:
        return 'slower'
    if low >= 1.0 / (1.0 + delta) and high <= 1.0 + delta:
        return 'equivalent'
    return 'inconclusive'


def compare(differences, delta, level=1.0 - ALPHA, with_p=True):
    """Everything known about one arm against the control in one cell."""
    n = len(differences)
    mean = statistics.fmean(differences)
    result = {'n_blocks': n, 'ratio': math.exp(mean), 'level': level, 'delta': delta,
              'lo': None, 'hi': None, 'hl_ratio': None, 'hl_lo': None, 'hl_hi': None, 'p': None, 'sd_log': None}
    if n < 2:
        result['verdict'] = 'too few blocks'
        return result
    deviation = statistics.stdev(differences)
    half = t_quantile(1.0 - (1.0 - level) / 2.0, n - 1) * deviation / math.sqrt(n)
    estimate, low, high = hodges_lehmann(differences, 1.0 - level)
    result.update(lo=math.exp(mean - half), hi=math.exp(mean + half), sd_log=deviation, hl_ratio=math.exp(estimate),
                  hl_lo=None if low is None else math.exp(low), hl_hi=None if high is None else math.exp(high),
                  p=sign_flip_p(differences) if with_p else None)
    if n < MIN_BLOCKS:
        result['verdict'] = 'too few blocks'
    else:
        verdict, robust = classify(result['lo'], result['hi'], delta), classify(result['hl_lo'], result['hl_hi'], delta)
        result['verdict'] = verdict if verdict == robust else 'inconclusive'
    return result


def holm(p_values):
    """Holm's step-down adjustment, in the order given."""
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted, running = [0.0] * len(p_values), 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def blocks_needed(sigma, delta):
    """Blocks for 80% power that the 95% interval excludes 1 when the true ratio is 1 + delta.

    With this many blocks a true ratio of (1 + delta) squared earns the
    verdict faster or slower with about the same power; a true ratio of
    exactly 1 + delta almost never does, since the interval must clear delta.
    """
    return max(MIN_BLOCKS, math.ceil(((1.96 + 0.84) * sigma / math.log1p(delta)) ** 2) + 2)


def blocks_for_equivalence(sigma, delta, power=0.8):
    """Blocks for the verdict equivalent, with the given power, when the true ratio is 1."""
    quantile = statistics.NormalDist().inv_cdf((1.0 + power) / 2.0)
    return max(MIN_BLOCKS, math.ceil(((1.96 + quantile) * sigma / math.log1p(delta)) ** 2) + 2)


# -- experiment data -------------------------------------------------------

def records(path):
    """The complete lines of a JSONL file; a last line still being written is left out."""
    lines = path.read_text().split('\n')
    return [json.loads(line) for line in lines[:-1] if line]


def load(directories):
    """Samples of valid blocks, grouped as {cell_id: {(run, block): {arm: sample}}}, with the plans."""
    cells, plans, voids = {}, [], []
    for directory in directories:
        directory = pathlib.Path(directory)
        plans.append(json.loads((directory / 'plan.json').read_text()))
        attempts = records(directory / 'blocks.jsonl')
        valid = {(a['cell_id'], a['block'], a['attempt']) for a in attempts if a['valid']}
        voids += [a for a in attempts if not a['valid']]
        for sample in records(directory / 'samples.jsonl'):
            if (sample['cell_id'], sample['block'], sample['attempt']) in valid:
                block = cells.setdefault(sample['cell_id'], {}).setdefault((sample['run_id'], sample['block']), {})
                block[sample['arm']] = sample
    return cells, plans, voids


def analyse(directories, delta=None, looks=1, control=None):
    """The effects, absolutes, pairs and noise tables of an experiment's runs."""
    cells, plans, voids = load(directories)
    plan = plans[0]
    if len({p['experiment'] for p in plans}) != 1:
        raise SystemExit('the runs belong to different experiments')
    delta = delta if delta is not None else (plan.get('delta') or 0.03)
    level = 1.0 - ALPHA / looks
    control, primary = control or plan['control'], plan['primary']
    if control not in {arm['name'] for arm in plan['arms']}:
        raise SystemExit(f'{control} is not an arm of this experiment')
    cell_info = {cell['id']: cell for p in plans for cell in p['cells']}
    arms = [arm['name'] for arm in plan['arms'] if arm['name'] != control]
    metrics = [primary] + [metric for metric in SECONDARY if metric != primary]
    effects, absolutes, pairs, noise = [], [], [], []
    for cell_id in sorted(cells):
        blocks = cells[cell_id]
        labels = {'experiment': plan['experiment'], 'kind': plan['kind'], 'cell_id': cell_id,
                  **{field: cell_info[cell_id][field] for field in CELL_FIELDS}}
        for metric in metrics:
            value = METRICS[metric]
            for arm in [control] + arms:
                logs = [math.log(value(block[arm])) for block in blocks.values() if arm in block]
                if len(logs) >= 2:
                    half = t_quantile(1.0 - (1.0 - level) / 2.0, len(logs) - 1) * statistics.stdev(logs) / math.sqrt(len(logs))
                else:
                    half = None
                centre = statistics.fmean(logs)
                absolutes.append({**labels, 'arm': arm, 'metric': metric, 'n_blocks': len(logs),
                                  'geomean': math.exp(centre), 'lo': half and math.exp(centre - half),
                                  'hi': half and math.exp(centre + half)})
            for arm in arms:
                keys = [key for key, block in blocks.items() if arm in block and control in block]
                differences = [math.log(value(blocks[key][arm])) - math.log(value(blocks[key][control])) for key in keys]
                if not differences:
                    continue
                row = {**labels, 'arm': arm, 'control': control, 'metric': metric, 'primary': metric == primary,
                       **compare(differences, delta, level)}
                row['err_minus'] = None if row['lo'] is None else row['ratio'] - row['lo']
                row['err_plus'] = None if row['hi'] is None else row['hi'] - row['ratio']
                row['p_holm'] = None
                if metric != primary and row['verdict'] != 'too few blocks':
                    row['verdict'] = 'descriptive'  # only the declared primary metric is judged
                effects.append(row)
                if metric == primary:
                    for (run_id, number), difference in zip(keys, differences):
                        pairs.append({**labels, 'arm': arm, 'run_id': run_id, 'block': number, 'metric': metric,
                                      't_arm': value(blocks[(run_id, number)][arm]),
                                      't_control': value(blocks[(run_id, number)][control]),
                                      'log_ratio': difference, 'ratio': math.exp(difference)})
                    if row['sd_log'] is not None:
                        noise.append({**labels, 'arm': arm, 'n_blocks': row['n_blocks'], 'sigma_d': row['sd_log'],
                                      **{f'blocks_for_{int(d * 100)}pct': blocks_needed(row['sd_log'], d)
                                         for d in (0.02, 0.03, 0.05, 0.10)},
                                      **{f'blocks_equivalent_{int(d * 100)}pct': blocks_for_equivalence(row['sd_log'], d)
                                         for d in (0.02, 0.03, 0.05, 0.10)}})
    judged = [row for row in effects if row['primary'] and row['p'] is not None]
    for row, adjusted in zip(judged, holm([row['p'] for row in judged])):
        row['p_holm'] = adjusted
    summary = {'experiment': plan['experiment'], 'kind': plan['kind'], 'hypothesis': plan.get('hypothesis'),
               'primary': primary, 'control': control, 'delta': delta, 'level': level, 'looks': looks,
               'runs': [p['run_id'] for p in plans], 'spec_sha256': sorted({p['spec_sha256'] for p in plans}),
               'valid_blocks': sum(len(blocks) for blocks in cells.values()), 'void_attempts': len(voids),
               'void_reasons': sorted({(a['void_reason'] or '')[:160] for a in voids})}
    return {'summary': summary, 'effects': effects, 'absolutes': absolutes, 'pairs': pairs, 'noise': noise}


def write(result, directory):
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'summary.json').write_text(json.dumps(result['summary'], indent=2) + '\n')
    for name in ('effects', 'absolutes', 'pairs', 'noise'):
        rows = result[name]
        (directory / f'{name}.json').write_text(json.dumps(rows, indent=1) + '\n')
        with open(directory / f'{name}.csv', 'w', newline='') as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows({key: '' if value is None else value for key, value in row.items()} for row in rows)


def output_name(stem, control):
    """Where an analysis against a non-default control goes, so it cannot replace the declared one."""
    return f'{stem}-vs-{control}' if control else stem


def run_directories(experiment):
    experiment = pathlib.Path(experiment)
    return sorted(path.parent for path in experiment.glob('*/samples.jsonl'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=pathlib.Path, help='benchmarks/results/lab/EXPERIMENT')
    parser.add_argument('--delta', type=float, help='smallest effect of interest (default: the spec\'s)')
    parser.add_argument('--looks', type=int, default=1, help='declared analysis looks; each uses 1 - 0.05/looks')
    parser.add_argument('--control', help='compare against this arm instead of the spec\'s control')
    args = parser.parse_args(argv)
    directories = run_directories(args.experiment)
    if not directories:
        parser.error('no fetched runs under ' + str(args.experiment))
    result = analyse(directories, args.delta, args.looks, args.control)
    write(result, args.experiment / output_name('analysis', args.control))
    for row in result['effects']:
        if row['primary']:
            interval = '' if row['lo'] is None else f' [{row["lo"]:.3f}, {row["hi"]:.3f}]'
            print(f'{row["cell_id"]:48} {row["arm"]:10} n={row["n_blocks"]:<3} {row["ratio"]:.3f}{interval}  {row["verdict"]}')
    print(args.experiment / output_name('analysis', args.control))


if __name__ == '__main__':
    main()
