#!/usr/bin/env python3
"""Validate the complete sweep and summarize completed FCTs and same-seed pairs.

Example: python3 sched-lab/stats.py --csv artifacts/.../baseline.csv --out artifacts/.../analysis
FCT is the bench's size-3000B completion time, not exact full-reception time.
"""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, t

SCENARIOS = ['dominating', 'competing', 'degrade']
ORDER = [0, 1, 2, 3, 4, 6, 5]
NAMES = {0: 'RR', 1: 'MinRTT', 2: 'BLEST', 3: 'ECF', 4: 'Peekaboo',
         5: 'EAT(new)', 6: 'MinRTT-multi(new)'}
KEYS = ['scenario', 'scheduler', 'seed']
METRICS = ['size', 'fct_s', 'fct95_s', 'rx_app', 'rx_p0', 'rx_p1',
           'delay_p0_ms', 'delay_p1_ms', 'done']


def load_sweep(path, seeds=30):
    df = pd.read_csv(path)
    required = set(KEYS + METRICS + ['name', 'wall_s'])
    if missing := required - set(df):
        raise ValueError(f'Missing columns: {sorted(missing)}')
    if df[KEYS].duplicated().any():
        raise ValueError('Duplicate scenario/scheduler/seed')
    expected = set(itertools.product(SCENARIOS, ORDER, range(1, seeds + 1)))
    actual = set(df[KEYS].itertuples(index=False, name=None))
    if actual != expected:
        raise ValueError(f'Incomplete sweep: missing={len(expected-actual)}, unexpected={len(actual-expected)}')
    if not np.isfinite(df[METRICS + ['wall_s']].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite measurement')
    if not df['size'].eq(5242880).all() or not df['done'].isin([0, 1]).all():
        raise ValueError('Unexpected size or done flag')
    if not df['name'].eq(df['scheduler'].map(NAMES)).all():
        raise ValueError('Scheduler id/name mismatch')
    if (df[['rx_app', 'rx_p0', 'rx_p1', 'wall_s']] < 0).any().any():
        raise ValueError('Negative byte count or wall time')
    if (df['rx_app'] > df['size']).any():
        raise ValueError('Received application bytes exceed target')
    expected_done = df['rx_app'].ge(df['size'] - 3000).astype(int)
    if not expected_done.eq(df['done']).all():
        raise ValueError('Completion flag disagrees with bench threshold')
    if not df.loc[df.done.eq(0), 'fct_s'].eq(60).all():
        raise ValueError('Unexpected incomplete-run FCT sentinel')
    return df


def mean_ci(values):
    x = np.asarray(values, dtype=float)
    if not len(x):
        return (np.nan,) * 4
    mean = float(x.mean())
    if len(x) < 2:
        return mean, np.nan, np.nan, np.nan
    half = float(t.ppf(.975, len(x)-1) * x.std(ddof=1) / np.sqrt(len(x)))
    return mean, mean-half, mean+half, 2*half


def signed_rank_exact(differences):
    """Two-sided exact sign permutation of midranks; discard zero differences.

    Bench CSV precision is 0.0001s. Integer ticks avoid false unequal ranks.
    Dynamic programming enumerates the signed-rank distribution (<=30 pairs),
    including tied absolute differences. No asymptotic or Monte Carlo fallback.
    """
    ticks = np.rint(np.asarray(differences, dtype=float) * 10000).astype(np.int64)
    nonzero = ticks[ticks != 0]
    if not len(ticks):
        return np.nan, np.nan, 0
    if not len(nonzero):
        return 0., 1., 0
    ranks2 = np.rint(rankdata(np.abs(nonzero), method='average') * 2).astype(int)
    plus = int(ranks2[nonzero > 0].sum())
    total = int(ranks2.sum())
    ways = [0] * (total + 1)
    ways[0] = 1
    reachable = 0
    for r in ranks2:
        for k in range(reachable, -1, -1):
            ways[k+r] += ways[k]
        reachable += int(r)
    tail = min(plus, total-plus)
    pvalue = min(1., 2 * sum(ways[:tail+1]) / 2**len(nonzero))
    return tail / 2, pvalue, len(nonzero)


def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    result = np.full(len(p), np.nan)
    indices = np.flatnonzero(np.isfinite(p))
    order = indices[np.argsort(p[indices])]
    previous = 0.
    for i, j in enumerate(order):
        previous = max(previous, min(1., (len(order)-i)*p[j]))
        result[j] = previous
    return result


def summarize(df):
    rows = []
    for sc, sid in itertools.product(SCENARIOS, ORDER):
        g = df[(df.scenario == sc) & (df.scheduler == sid)]
        complete = g[g.done.eq(1)]
        fct = complete.fct_s
        mean, low, high, width = mean_ci(fct)
        shares = complete.rx_p1 / (complete.rx_p0 + complete.rx_p1).replace(0, np.nan)
        rows.append(dict(scenario=sc, scheduler=sid, name=NAMES[sid], runs=len(g),
                         completed=len(complete), incomplete=int(g.done.eq(0).sum()),
                         full_received=int(g.rx_app.eq(g['size']).sum()),
                         completed_short=int((g.done.eq(1) & g.rx_app.lt(g['size'])).sum()),
                         completion_rate=len(complete)/len(g), mean_s=mean,
                         median_s=fct.median(), p90_s=fct.quantile(.9),
                         std_s=fct.std(ddof=1), ci95_low_s=low, ci95_high_s=high,
                         ci95_width_s=width, mean_fct95_s=complete.fct95_s.mean(),
                         mean_path1_ip_share=shares.mean()))
    return pd.DataFrame(rows)


def paired_comparisons(df):
    rows, observations = [], []
    for sc in SCENARIOS:
        g = df[df.scenario.eq(sc)]
        for a, b in itertools.combinations(ORDER, 2):
            ga = g[g.scheduler.eq(a)].set_index('seed')
            gb = g[g.scheduler.eq(b)].set_index('seed')
            both = ga.done.eq(1) & gb.done.eq(1)
            diff = (ga.loc[both, 'fct_s'] - gb.loc[both, 'fct_s']).round(4)
            mean, low, high, width = mean_ci(diff)
            stat, pvalue, nonzero = signed_rank_exact(diff)
            rows.append(dict(scenario=sc, scheduler_a=a, name_a=NAMES[a],
                             scheduler_b=b, name_b=NAMES[b], runs_each=len(ga),
                             completed_a=int(ga.done.sum()), completed_b=int(gb.done.sum()),
                             paired_completed=len(diff), a_only=int((ga.done.eq(1)&gb.done.eq(0)).sum()),
                             b_only=int((ga.done.eq(0)&gb.done.eq(1)).sum()),
                             neither=int((ga.done.eq(0)&gb.done.eq(0)).sum()),
                             mean_diff_a_minus_b_s=mean, ci95_low_s=low, ci95_high_s=high,
                             ci95_width_s=width, a_faster=int((diff < 0).sum()),
                             b_faster=int((diff > 0).sum()), ties=int((diff == 0).sum()),
                             wilcoxon_statistic=stat, wilcoxon_p=pvalue, nonzero_pairs=nonzero,
                             paired_seeds=','.join(map(str, diff.index))))
            observations += [dict(scenario=sc, scheduler_a=a, scheduler_b=b, seed=int(seed),
                                  fct_a_s=float(ga.loc[seed,'fct_s']), fct_b_s=float(gb.loc[seed,'fct_s']),
                                  diff_a_minus_b_s=float(value)) for seed, value in diff.items()]
    result = pd.DataFrame(rows)
    result['wilcoxon_p_holm_scenario'] = result.groupby('scenario')['wilcoxon_p'].transform(holm)
    return result, pd.DataFrame(observations)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--seeds', type=int, default=30)
    ap.add_argument('--week1-csv', type=Path)
    args = ap.parse_args()
    df = load_sweep(args.csv, args.seeds)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = summarize(df)
    pairs, observations = paired_comparisons(df)
    for filename, table in [('summary.csv',summary), ('paired_comparisons.csv',pairs),
                            ('paired_observations.csv',observations),
                            ('below_target_runs.csv',df[df.rx_app.lt(df['size'])])]:
        table.to_csv(args.out/filename, index=False, float_format='%.10g')
    widths = summary[summary.scenario.eq('dominating')][['scheduler','name','completed','runs','ci95_width_s']].copy()
    widths['width_le_0_1_s'] = widths.ci95_width_s.le(.1)
    widths.to_csv(args.out/'dominating_ci_gate.csv', index=False, float_format='%.10g')
    validation = dict(rows=len(df), unique_keys=len(df[KEYS].drop_duplicates()),
                      completed=int(df.done.sum()), full_received=int(df.rx_app.eq(df['size']).sum()),
                      paired_comparison_rows=len(pairs),
                      dominating_all_seven_ci_widths_le_0_1_s=bool(widths.width_le_0_1_s.all()),
                      ci_method='95% two-sided Student t; completed runs only',
                      wilcoxon_method='exact conditional sign permutation; zero differences discarded; tied midranks; 0.0001s precision',
                      multiplicity='Holm adjustment across 21 pairs within each scenario')
    if args.week1_csv:
        old = load_sweep(args.week1_csv, 10).set_index(KEYS).sort_index()
        new = df[df.seed.le(10)].set_index(KEYS).sort_index()
        changed = old[METRICS].ne(new[METRICS])
        validation['week1_reproduction'] = dict(compared_rows=len(old), compared_metrics=METRICS,
                                                differing_cells=int(changed.sum().sum()),
                                                differing_rows=int(changed.any(axis=1).sum()))
        changed.to_csv(args.out/'week1_comparison_cells.csv')
    (args.out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(validation,ensure_ascii=False,indent=2))
    print(widths.to_string(index=False))


if __name__ == '__main__':
    main()
