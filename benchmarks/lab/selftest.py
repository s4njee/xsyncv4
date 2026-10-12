#!/usr/bin/env python3
"""Check the analysis on simulated experiments whose true ratios are known.

Each simulated block shares a large drift between its arms, as a real block
shares temperature and load; the paired analysis must cancel it. The checks
are the interval's coverage, the rate of wrong verdicts, and the power the
block-count formulas promise. Exits nonzero if any check is outside its band.
"""
import argparse
import math
import random
import sys

import analyze

DRIFT = 0.30  # block-to-block standard deviation of log time, far above the effects sought


def noise(generator, model, sigma):
    """One arm's log-time error; the difference of two has standard deviation sigma."""
    scale = sigma / math.sqrt(2.0)
    if model == 'heavy':  # Student t with 3 degrees of freedom, same variance
        chi = sum(generator.gauss(0.0, 1.0) ** 2 for _ in range(3))
        return generator.gauss(0.0, 1.0) / math.sqrt(chi / 3.0) * scale / math.sqrt(3.0)
    value = generator.gauss(0.0, scale)
    if model == 'outliers' and generator.random() < 0.05:  # an occasional sample three times slower
        value += math.log(3.0)
    return value


def experiment(generator, blocks, ratio, sigma, model):
    differences = []
    for _ in range(blocks):
        drift = generator.gauss(0.0, DRIFT)
        arm = math.log(ratio) + drift + noise(generator, model, sigma)
        control = drift + noise(generator, model, sigma)
        differences.append(arm - control)
    return differences


def rates(generator, runs, blocks, ratio, sigma, model, delta):
    """Fractions of simulated experiments by interval coverage and by verdict."""
    tally = {'t_covers': 0, 'hl_covers': 0, 'excludes_1': 0, 'faster': 0, 'slower': 0, 'equivalent': 0,
             'inconclusive': 0}
    for _ in range(runs):
        result = analyze.compare(experiment(generator, blocks, ratio, sigma, model), delta, with_p=False)
        tally['t_covers'] += result['lo'] <= ratio <= result['hi']
        tally['hl_covers'] += result['hl_lo'] <= ratio <= result['hl_hi']
        tally['excludes_1'] += not result['lo'] <= 1.0 <= result['hi']
        tally[result['verdict']] += 1
    return {key: value / runs for key, value in tally.items()}


def family_error(generator, runs, blocks, comparisons, sigma):
    """How often Holm-adjusted sign-flip tests reject anything when every null is true."""
    wrong = 0
    for _ in range(runs):
        p_values = [analyze.sign_flip_p(experiment(generator, blocks, 1.0, sigma, 'normal'))
                    for _ in range(comparisons)]
        wrong += min(analyze.holm(p_values)) < analyze.ALPHA
    return wrong / runs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=4000, help='simulated experiments per check')
    parser.add_argument('--seed', type=int, default=20261011)
    args = parser.parse_args(argv)
    generator = random.Random(args.seed)
    delta, sigma = 0.03, 0.05
    detect = analyze.blocks_needed(sigma, delta)
    equivalent = analyze.blocks_for_equivalence(sigma, delta)
    checks = []

    def check(label, value, low, high):
        checks.append((label, value, low, high, low <= value <= high))

    for blocks in (8, 12, 24):
        found = rates(generator, args.runs, blocks, 0.9, sigma, 'normal', delta)
        check(f'coverage of the 95% t interval, {blocks} blocks', found['t_covers'], 0.93, 0.97)
        check(f'coverage of the Hodges-Lehmann interval, {blocks} blocks', found['hl_covers'], 0.93, 1.0)
    for model in ('heavy', 'outliers'):
        found = rates(generator, args.runs, 12, 0.9, sigma, model, delta)
        check(f'coverage of the 95% t interval, {model} noise', found['t_covers'], 0.92, 1.0)
        check(f'coverage of the Hodges-Lehmann interval, {model} noise', found['hl_covers'], 0.93, 1.0)

    found = rates(generator, args.runs, detect, 1.0, sigma, 'normal', delta)
    check(f'no effect, {detect} blocks: verdict faster or slower', found['faster'] + found['slower'], 0.0, 0.005)
    check(f'no effect, {detect} blocks: interval excludes 1', found['excludes_1'], 0.03, 0.07)
    found = rates(generator, args.runs, equivalent, 1.0, sigma, 'normal', delta)
    check(f'no effect, {equivalent} blocks: verdict equivalent', found['equivalent'], 0.70, 0.90)

    found = rates(generator, args.runs, detect, 1.0 + delta, sigma, 'normal', delta)
    check(f'true ratio 1+delta, {detect} blocks: interval excludes 1', found['excludes_1'], 0.74, 0.90)
    check(f'true ratio 1+delta, {detect} blocks: verdict slower', found['slower'], 0.0, 0.035)
    check(f'true ratio 1+delta, {detect} blocks: verdict equivalent', found['equivalent'], 0.0, 0.035)
    found = rates(generator, args.runs, detect, (1.0 + delta) ** 2, sigma, 'normal', delta)
    check(f'true ratio (1+delta)^2, {detect} blocks: verdict slower', found['slower'], 0.70, 0.90)
    found = rates(generator, args.runs, detect, 1.0 / (1.0 + delta) ** 2, sigma, 'normal', delta)
    check(f'true ratio 1/(1+delta)^2, {detect} blocks: verdict faster', found['faster'], 0.70, 0.90)
    check(f'true ratio 1/(1+delta)^2, {detect} blocks: verdict slower', found['slower'], 0.0, 0.0)

    # Ten blocks: with eight, 2/256 times ten comparisons can never fall below 0.05.
    check('ten true nulls, 10 blocks, Holm-adjusted: any rejection',
          family_error(generator, max(500, args.runs // 4), 10, 10, sigma), 0.005, 0.065)

    for label, value, low, high, ok in checks:
        print(f'{"ok  " if ok else "FAIL"} {value:6.3f}  [{low:.3f}, {high:.3f}]  {label}')
    failed = sum(not ok for *_, ok in checks)
    print(f'\n{len(checks) - failed} of {len(checks)} checks passed '
          f'({args.runs} simulated experiments each, sigma_d {sigma}, delta {delta})')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
