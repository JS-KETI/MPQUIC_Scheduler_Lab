#!/usr/bin/env python3
"""Re-run frozen baseline cases into a NEW directory; preserve per-case logs and provenance."""
import argparse, csv, gzip, hashlib, json, os, shlex, subprocess, time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-dir', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--selection', choices=['incomplete', 'all'], default='incomplete')
    ap.add_argument('--cases', help='optional scenario:scheduler:seed comma-separated filter')
    ap.add_argument('--sim-end', type=float, default=60)
    ap.add_argument('--extra', default='')
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    rows = list(csv.DictReader((a.baseline_dir / 'baseline.csv').open()))
    commands = json.loads((a.baseline_dir / 'commands.json').read_text())
    key = lambda r: (r['scenario'], int(r['scheduler']), int(r['seed']))
    bykey = {key(r): r for r in rows}
    if len(bykey) != len(rows) or {key(c) for c in commands} != set(bykey): ap.error('baseline rows and command keys must match without duplicates')
    selected = {tuple([c.split(':')[0], int(c.split(':')[1]), int(c.split(':')[2])]) for c in a.cases.split(',')} if a.cases else None
    chosen = [c for c in commands if (a.selection == 'all' or int(bykey[key(c)]['done']) == 0) and (selected is None or key(c) in selected)]
    if not chosen: ap.error('no cases selected')
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / 'logs').mkdir()
    diff = subprocess.check_output(['git', 'diff', '--binary', 'HEAD', '--', 'src/quic', 'src/applications', 'scratch'], cwd=root)
    (a.out / 'source.patch').write_bytes(diff)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    meta = {'created_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), 'baseline_sha256': sha(a.baseline_dir/'baseline.csv'), 'source_patch_sha256': hashlib.sha256(diff).hexdigest(), 'selection': a.selection, 'cases': a.cases, 'sim_end': a.sim_end, 'extra': a.extra, 'planned_runs': len(chosen), 'binary_sha256': sha(Path(commands[0]['argv'][0])), 'quic_library_sha256': {p.name: sha(p) for p in (root/'build/lib').glob('libns3*quic*.so')}, 'runner_sha256': sha(Path(__file__)), 'source_file_hashes': {str(f.relative_to(root)): sha(f) for f in sorted(list((root/'src/quic/model').glob('*')) + list((root/'scratch').glob('*.cc'))) if f.is_file()}, 'runner_command': [str(x) for x in __import__('sys').argv]}
    (a.out / 'provenance.json').write_text(json.dumps(meta, indent=2)+'\n')
    env = dict(os.environ, LD_LIBRARY_PATH=str(root/'build/lib'))
    actual, results, errors = [], [], []
    with (a.out/'results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for i,c in enumerate(chosen,1):
            argv = [v for v in c['argv'] if not v.startswith('--SimEnd=')] + [f'--SimEnd={a.sim_end:g}'] + shlex.split(a.extra)
            actual.append({**c, 'argv': argv})
            t=time.monotonic(); run=subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True); wall=time.monotonic()-t
            label=f"{c['scenario']}-{c['scheduler']}-seed{c['seed']:02d}"
            with gzip.open(a.out/'logs'/f'{label}.stdout.gz','wt') as z: z.write(run.stdout)
            if run.stderr:
                with gzip.open(a.out/'logs'/f'{label}.stderr.gz','wt') as z: z.write(run.stderr)
            lines=[l for l in run.stdout.splitlines() if l.startswith('RESULT,')]
            if run.returncode or len(lines)!=1:
                errors.append({'case': label, 'returncode': run.returncode, 'result_lines': len(lines)})
                print(f'[{i}/{len(chosen)}] {label} ERROR; stopping before further runs', flush=True); break
            v=lines[0].split(',')[1:]
            r=dict(zip(list(rows[0]), [c['scenario'],c['scheduler'],bykey[key(c)]['name'],c['seed']]+v[2:]+[round(wall,3)]))
            w.writerow(r); f.flush(); results.append(r)
            print(f"[{i}/{len(chosen)}] {label} done={r['done']} rx={r['rx_app']} fct={r['fct_s']}",flush=True)
    (a.out/'commands.json').write_text(json.dumps(actual,indent=2)+'\n')
    keys=[key(r) for r in results]
    validation={'planned':len(chosen), 'result_rows':len(results), 'errors': errors, 'duplicate_keys':len(keys)-len(set(keys)), 'completed':sum(int(r['done']) for r in results), 'full_received':sum(int(r['rx_app'])==int(r['size']) for r in results), 'baseline_sha256_after':sha(a.baseline_dir/'baseline.csv')}
    (a.out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation),flush=True)
    if errors or len(results)!=len(chosen): raise SystemExit(1)

if __name__ == '__main__': main()
