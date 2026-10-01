import csv
import json
import os
from pathlib import Path
import subprocess
import time

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
out = root / 'sched-lab/w1-2026-10-01/single-path'
out.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, LD_LIBRARY_PATH=str(root / 'build/lib'))
rows = []
for seed in (1, 2, 3):
    run = out / f'seed-{seed}'
    run.mkdir()
    command = [str(root / 'build/scratch/wns3-mpquic-one-path'), '--SchedulerType=4', f'--Seed={seed}', '--Size=5242880', '--Rate0a=5', '--Rate0b=5', '--Delay0a=50', '--Delay0b=50', '--LossRate=0', '--CcType=1']
    start = time.monotonic()
    process = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=120)
    wall = time.monotonic() - start
    (run / 'stdout.log').write_text(process.stdout)
    (run / 'stderr.log').write_text(process.stderr)
    (run / 'command.json').write_text(json.dumps(command, indent=2))
    lines = [line for line in process.stdout.splitlines() if line.startswith('RESULT_ONE_PATH,')]
    assert process.returncode == 0 and len(lines) == 1, (seed, process.returncode, process.stderr[-1000:])
    values = lines[0].split(',')[1:]
    rows.append(dict(scheduler=int(values[0]), seed=int(values[1]), size=int(values[2]), fct_s=float(values[3]), fct_full_s=float(values[4]), rx_app=int(values[5]), wall_s=round(wall, 3), in_gate_range=8.5 <= float(values[4]) <= 9.0))
    print(lines[0], f'wall={wall:.3f}s', flush=True)
with (out / 'single_path.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(out / 'single_path.json').write_text(json.dumps(rows, indent=2))
