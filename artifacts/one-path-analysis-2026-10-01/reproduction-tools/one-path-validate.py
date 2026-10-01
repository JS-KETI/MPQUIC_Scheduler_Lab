"""Validate experimental evidence and package the one-path diagnosis artifacts."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
out = root / 'sched-lab/one-path-analysis-2026-10-01'
rows = [r for p in [out/'experiments/experiments.csv', out/'reference-full-size/experiments.csv']
        for r in csv.DictReader(p.open())]
assert len(rows) == len({(r['case'], r['seed']) for r in rows}) == 39
assert all(int(r['rx_app']) == int(r['size']) for r in rows)
expected = {'baseline-fixed':3, 'scheduler-RR-only':3, 'rate-5-6-only':10,
            'delay-50-55-only':3, 'upstream-exact':10, 'reference-full-size':10}
assert {c:sum(r['case']==c for r in rows) for c in expected} == expected
ref = [r for r in rows if r['case']=='reference-full-size']
assert len(ref)==10 and all(8.5<=float(r['fct_full_s'])<=9.0 and int(r['size'])==5242880 for r in ref)
old = root/'sched-lab/w1-2026-10-01/single-path/seed-1'
disabled = out/'observer-disabled'
enabled = out/'experiments/baseline-fixed-seed-1'
assert (old/'stdout.log').read_bytes() == (disabled/'stdout.log').read_bytes()
assert (old/'scheduler4-rx.txt').read_bytes() == (disabled/'scheduler4-rx.txt').read_bytes() == (enabled/'scheduler4-rx.txt').read_bytes()
assert not (disabled/'diag-rx.csv').exists()
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True).strip()
base = 'c09aa53e2f67a5481389839b06a7edadf3d00d86'
subprocess.run(['git','diff','--check',base,'HEAD'],cwd=root,check=True)
subprocess.run(['git','apply','--reverse','--check',str(out/'05-one-path-diagnosis.patch')],cwd=root,check=True)
with (out/'all_experiments.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sources = [root/'AGENTS.md',root/'scratch/wns3-mpquic-one-path.cc',root/'sched-lab/one-path-investigate.py',
           root/'sched-lab/one-path-diagnosis.md',root/'exp-wns3-one-path.sh']
validation = dict(created_at=datetime.now(timezone.utc).isoformat(),
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    base_commit=base, branch='lab/w1-one-path-diagnosis-20261001',
    matrix_runs=39,observer_disabled_runs=1,unique_combinations=39,full_receive_count=39,counts=expected,
    reference_full_size_time_range_pass=10,observer_disabled_stdout_equal=True,
    observer_disabled_ip_trace_equal=True,observer_enabled_ip_trace_equal=True,
    diag_default_off=True,tracked_worktree_clean=True,patch_reverse_check=True,
    source_sha256={str(p.relative_to(root)):sha(p) for p in sources},validator_sha256=sha(Path(__file__)))
(out/'validation.json').write_text(json.dumps(validation,indent=2))
(out/'REPORT.md').write_bytes((root/'sched-lab/one-path-diagnosis.md').read_bytes())
repro=out/'reproduction-tools'; repro.mkdir(exist_ok=False)
for p in sources + [Path(__file__)]:
    (repro/p.name).write_bytes(p.read_bytes())
print(json.dumps(validation,indent=2))
