"""Reproduce upstream settings and isolate causes of the one-path time difference."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from datetime import datetime, timezone

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--cases', nargs='+', help='Run only named cases; each run uses a new output directory')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, LD_LIBRARY_PATH=str(root / 'build/lib'))
    cases = [
        ('baseline-fixed', 4, 5242880, 5, 50, range(1, 4)),
        ('scheduler-RR-only', 0, 5242880, 5, 50, range(1, 4)),
        ('rate-5-6-only', 0, 5242880, 6, 50, range(1, 11)),
        ('delay-50-55-only', 0, 5242880, 5, 55, range(1, 4)),
        ('upstream-exact', 0, 5242800, 6, 55, range(1, 11)),
        ('reference-full-size', 0, 5242880, 6, 55, range(1, 11)),
    ]
    if args.cases:
        names = {c[0] for c in cases}
        parser.error('Unknown cases: ' + ', '.join(set(args.cases)-names)) if set(args.cases)-names else None
        cases = [c for c in cases if c[0] in args.cases]
    rows = []
    for case, scheduler, size, rate_max, delay_max, seeds in cases:
        for seed in seeds:
            run = out / f'{case}-seed-{seed}'
            run.mkdir()
            command = [str(root/'build/scratch/wns3-mpquic-one-path'), f'--SchedulerType={scheduler}',
                       f'--Seed={seed}', f'--Size={size}', '--Rate0a=5', f'--Rate0b={rate_max}',
                       '--Delay0a=50', f'--Delay0b={delay_max}', '--LossRate=0', '--CcType=1', '--Diag=1']
            t0 = time.monotonic()
            p = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=120)
            (run/'stdout.log').write_text(p.stdout)
            (run/'stderr.log').write_text(p.stderr)
            (run/'command.json').write_text(json.dumps(command, indent=2))
            result = [s.split(',')[1:] for s in p.stdout.splitlines() if s.startswith('RESULT_ONE_PATH,')]
            diag = [s.split(',')[1:] for s in p.stdout.splitlines() if s.startswith('DIAG_ONE_PATH,')]
            assert p.returncode == 0 and len(result)==len(diag)==1, (case, seed, p.returncode)
            v, d = result[0], diag[0]
            fct = float(v[4])
            with (run/'diag-link.csv').open() as f:
                links = [r for r in csv.DictReader(f) if float(r['elapsed_s']) <= fct]
            row = dict(case=case, scheduler=scheduler, seed=seed, size=size,
                       rate_min_mbps=5, rate_max_mbps=rate_max, delay_min_ms=50, delay_max_ms=delay_max,
                       fct_threshold_s=float(v[3]), fct_full_s=fct, rx_app=int(v[5]),
                       first_rx_s=float(d[0]), fct95_s=float(d[1]), fct_5000000_s=float(d[2]),
                       mean_scheduled_rate_mbps=statistics.mean(int(r['rate_bps']) for r in links)/1e6,
                       full_receive=int(v[5])==size, in_gate_range=8.5<=fct<=9.0,
                       wall_s=round(time.monotonic()-t0, 3))
            rows.append(row)
            print(case, seed, fct, row['rx_app'], flush=True)
    with (out/'experiments.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = []
    for case, *_ in cases:
        rs = [r for r in rows if r['case']==case]
        ts = sorted(r['fct_full_s'] for r in rs)
        summary.append(dict(case=case, n=len(rs), completed=sum(r['full_receive'] for r in rs),
                            gate_n=sum(r['in_gate_range'] for r in rs), mean_s=statistics.mean(ts),
                            median_s=statistics.median(ts), min_s=min(ts), max_s=max(ts),
                            p90_s=ts[max(0, int(len(ts)*.9+.999999)-1)]))
    (out/'summary.json').write_text(json.dumps(summary, indent=2))
    meta = dict(created_at=datetime.now(timezone.utc).isoformat(), root=str(root),
                branch=subprocess.check_output(['git','branch','--show-current'], cwd=root,text=True).strip(),
                commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=root,text=True).strip(),
                argv=list(__import__('sys').argv), patch_state='01+02+03+04 + opt-in 05 observer',
                sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                         [root/'scratch/wns3-mpquic-one-path.cc', root/'exp-wns3-one-path.sh',Path(__file__)]})
    (out/'provenance.json').write_text(json.dumps(meta, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
