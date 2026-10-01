import csv
import json
import os
from pathlib import Path
import subprocess

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
out = root / 'sched-lab/w1-2026-10-01/single-path'
env = dict(os.environ, LD_LIBRARY_PATH=str(root / 'build/lib'))
cases = [
    ('rate-range-5-5p5', 5242880, 5.5, (1, 2, 3)),
    ('decimal-5MB', 5000000, 5.0, (1,)),
]
rows = []
for name, size, max_rate, seeds in cases:
    for seed in seeds:
        run = out / f'{name}-seed-{seed}'
        run.mkdir(exist_ok=False)
        command = [str(root / 'build/scratch/wns3-mpquic-one-path'), '--SchedulerType=4', f'--Seed={seed}', f'--Size={size}', '--Rate0a=5', f'--Rate0b={max_rate}', '--Delay0a=50', '--Delay0b=50', '--LossRate=0', '--CcType=1']
        p = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=120)
        (run / 'stdout.log').write_text(p.stdout)
        (run / 'stderr.log').write_text(p.stderr)
        (run / 'command.json').write_text(json.dumps(command, indent=2))
        lines = [line for line in p.stdout.splitlines() if line.startswith('RESULT_ONE_PATH,')]
        assert p.returncode == 0 and len(lines) == 1
        values = lines[0].split(',')[1:]
        rows.append(dict(case=name, seed=seed, size=size, rate_min_mbps=5.0, rate_max_mbps=max_rate, delay_ms=50.0, fct_s=float(values[3]), fct_full_s=float(values[4]), rx_app=int(values[5]), in_gate_range=8.5 <= float(values[4]) <= 9.0))
        print(name, lines[0])
with (out / 'diagnostics.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(out / 'diagnostics.json').write_text(json.dumps(rows, indent=2))
