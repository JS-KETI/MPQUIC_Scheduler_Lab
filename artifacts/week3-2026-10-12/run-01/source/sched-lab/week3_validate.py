#!/usr/bin/env python3
"""Week 3 finite validation protocol; run from the actual ns-3 repository."""
import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from run_sweep import NAMES, SCENARIOS, find_binary

RESULT_FIELDS = ['scheduler', 'seed', 'size', 'fct_s', 'fct95_s', 'rx_app',
                 'rx_p0', 'rx_p1', 'delay_p0_ms', 'delay_p1_ms', 'done']
SOURCE_FILES = ['src/quic/model/mp-quic-scheduler.h', 'src/quic/model/mp-quic-scheduler.cc',
                'src/quic/model/quic-socket-base.h', 'src/quic/model/quic-socket-base.cc',
                'src/quic/model/quic-stream-base.h', 'src/quic/model/quic-stream-base.cc',
                'src/quic/model/quic-l5-protocol.cc', 'src/quic/model/quic-stream-rx-buffer.h',
                'src/quic/model/quic-stream-rx-buffer.cc', 'src/quic/test/mp-quic-scheduler-test.cc',
                'src/quic/wscript', 'scratch/mpquic-sched-lab.cc',
                'sched-lab/run_sweep.py', 'sched-lab/week3_validate.py']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    root, out = Path(a.root).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'runs').mkdir()
    binary = find_binary(str(root))
    env = dict(os.environ, LD_LIBRARY_PATH=str(root / 'build/lib') + ':' + os.environ.get('LD_LIBRARY_PATH', ''))
    baseline_path = root / 'artifacts/week2-completion-2026-10-08/run-01/baseline.csv'
    frozen_hash_before = sha(baseline_path)
    baseline = {(x['scenario'], int(x['scheduler']), int(x['seed'])): x
                for x in csv.DictReader(baseline_path.open())}
    tasks = []
    for scenario in SCENARIOS:
        tasks += [('regression', scenario, s, 1, None, False) for s in range(7)]
        tasks += [('baseline_extra', scenario, 6, seed, None, False) for seed in (2, 3)]
        tasks += [('slot_plain', scenario, 7, seed, None, False) for seed in (1, 2, 3)]
        tasks += [('slot_trace', scenario, 7, seed, None, True) for seed in (1, 2, 3)]
        tasks += [('fixed_ratio', scenario, 7, seed, share, True)
                  for share in (0.3, 0.1, 0.5) for seed in (1, 2, 3)]
    assert len(tasks) == 72
    protocol = {
        'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        'scope': 'week3 D11-D15 only; fixed ratios are integration tests, not a new algorithm',
        'planned_runs': len(tasks), 'seed_range': [1, 3],
        'baseline': str(baseline_path.relative_to(root)), 'baseline_sha256': frozen_hash_before,
        'parameters': {'Size': 5242880, 'CcType': 1, 'LossRate': 0, 'CompletionGraceMs': 250, 'SimEnd': 60},
        'fixed_mode': 'ID7; up to 10 MSS packet burst, 3/7,1/9,5/5 on full burst; reduced/tail cases retained',
        'gate': {'relative_tolerance': 0.05, 'also_report': 'percentage-point error',
                 'unit': 'serialized STREAM frame bytes returned by SendDataPacket, excluding ACK/QUIC/IP',
                 'aggregation': 'sum actual bytes per path over eligible decisions in each run, not mean of decision ratios',
                 'exclude': 'whole decision if any path nominal_demand_frame_bytes exceeds pre-send cwnd_room_bytes',
                 'retain': 'flow-control/pacing/state/refill/quantization/tail discrepancies, no extra exclusions',
                 'no_eligible_bytes': 'indeterminate, never pass'},
        'packet_unit': 'application STREAM payload bytes; stream0 handshake excluded; Tx offsets deduplicated across paths',
        'arrival_estimate': 'RTT/2 + requested frame bytes*RTT/cwnd, cwnd/RTT service model; not physical arrival guarantee',
        'versions': {'python': platform.python_version(), 'platform': platform.platform(),
                     'cpu': subprocess.check_output(['lscpu'], text=True)},
        'commit': git(root, 'rev-parse', 'HEAD'), 'branch': git(root, 'branch', '--show-current'),
        'source_hashes': {f: sha(root / f) for f in SOURCE_FILES},
        'build_binary_sha256': sha(Path(binary)),
    }
    (out / 'protocol.json').write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    (out / 'working-tree.patch').write_text(git(root, 'diff', '--binary', 'HEAD') + '\n')
    for f in SOURCE_FILES:
        target = out / 'source' / f
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / f, target)
    rows, manifest = [], []
    fields = ['case', 'scenario', 'name', 'share0', 'trace', *RESULT_FIELDS, 'wall_s', 'run_id']
    with (out / 'results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, (case, scenario, scheduler, seed, share, traced) in enumerate(tasks, 1):
            run_id = f'{i:03d}-{case}-{scenario}-s{scheduler}-seed{seed}'
            if share is not None: run_id += f'-p0-{share:.1f}'
            run_dir = out / 'runs' / run_id
            run_dir.mkdir()
            args = [binary, f'--SchedulerType={scheduler}', f'--Seed={seed}', '--Size=5242880',
                    '--CcType=1', '--LossRate=0', '--CompletionGraceMs=250', '--SimEnd=60']
            args += [f'--{k}={v}' for k, v in SCENARIOS[scenario].items()]
            if share is not None: args += ['--FixedRatio=1', f'--Path0Share={share}']
            # Exercise reserved parameter propagation once, while preserving the
            # initial MinRTT-multi decision behavior.
            if case == 'slot_plain' and scenario == 'dominating' and seed == 1:
                args += ['--NewKappa=0.2', '--NewBeta=0.7', '--NewSmax=0.04']
            if traced: args += [f'--LabLogPrefix={run_dir / "trace"}']
            started = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
            t0 = time.perf_counter()
            proc = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
            wall = time.perf_counter() - t0
            (run_dir / 'stdout.log').write_text(proc.stdout)
            (run_dir / 'stderr.log').write_text(proc.stderr)
            record = dict(run_id=run_id, started_at=started, command=args, returncode=proc.returncode, wall_s=wall)
            (run_dir / 'command.json').write_text(json.dumps(record, indent=2))
            manifest.append(record)
            lines = [x for x in proc.stdout.splitlines() if x.startswith('RESULT,')]
            if proc.returncode or len(lines) != 1:
                (out / 'execution-manifest.json').write_text(json.dumps(manifest, indent=2))
                raise RuntimeError(f'{run_id}: execution/result failure; raw logs preserved')
            row = dict(zip(RESULT_FIELDS, lines[0].split(',')[1:]))
            if len(lines[0].split(',')) != 12: raise RuntimeError('unexpected RESULT columns')
            row.update(case=case, scenario=scenario, name=NAMES[scheduler],
                       share0='' if share is None else share, trace=int(traced), wall_s=wall, run_id=run_id)
            writer.writerow(row)
            handle.flush()
            rows.append(row)
            if i % 9 == 0: print(f'{i}/{len(tasks)} runs recorded', flush=True)
    checks = []
    for row in rows:
        if row['case'] not in ('regression', 'baseline_extra', 'slot_plain', 'slot_trace'): continue
        source_id = 6 if int(row['scheduler']) == 7 else int(row['scheduler'])
        ref = baseline[row['scenario'], source_id, int(row['seed'])]
        compare = [k for k in RESULT_FIELDS if k not in ('scheduler', 'seed')]
        mismatches = [k for k in compare if float(row[k]) != float(ref[k])]
        checks.append({'run_id': row['run_id'], 'reference_scheduler': source_id,
                       'reference_seed': int(row['seed']), 'matched': not mismatches, 'mismatches': mismatches})
    assert len(checks) == 45
    validation = {'planned_runs': 72, 'actual_rows': len(rows),
                  'unique_run_ids': len({x['run_id'] for x in rows}),
                  'completed': sum(int(x['done']) == 1 for x in rows),
                  'exact_full_received': sum(int(x['rx_app']) == int(x['size']) for x in rows),
                  'reference_checks': checks,
                  'reference_matches': sum(x['matched'] for x in checks),
                  'baseline_sha256_unchanged': frozen_hash_before == sha(baseline_path)}
    (out / 'execution-manifest.json').write_text(json.dumps(manifest, indent=2))
    (out / 'validation.json').write_text(json.dumps(validation, indent=2))
    print(json.dumps({k:v for k,v in validation.items() if k != 'reference_checks'}, indent=2))

if __name__ == '__main__':
    main()
