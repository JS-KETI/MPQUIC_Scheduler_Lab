import csv
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import runpy
import statistics
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
out = root / 'sched-lab/w1-2026-10-01'
def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))
def key(r):
    return (r['scenario'], int(r['scheduler']), int(r['seed']))

new = read(out / 'w1.csv')
ref = read(root.parent / 'results/results_fixed_stack.csv')
expected = set(itertools.product(('dominating', 'competing', 'degrade'), range(7), range(1, 11)))
new_keys = [key(r) for r in new]
assert len(new) == 210 and set(new_keys) == expected and len(set(new_keys)) == len(new_keys)
assert len(ref) == 210 and set(map(key, ref)) == expected
ref_by_key = {key(r): r for r in ref}
metrics = ('size', 'fct_s', 'fct95_s', 'rx_app', 'rx_p0', 'rx_p1', 'delay_p0_ms', 'delay_p1_ms', 'done')
diffs = []
for row in new:
    reference = ref_by_key[key(row)]
    for metric in metrics:
        if Decimal(row[metric]) != Decimal(reference[metric]):
            diffs.append(dict(scenario=row['scenario'], scheduler=row['scheduler'], seed=row['seed'], metric=metric, actual=row[metric], reference=reference[metric]))
with (out / 'reference_differences.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=('scenario', 'scheduler', 'seed', 'metric', 'actual', 'reference'))
    writer.writeheader()
    writer.writerows(diffs)

summary = read(out / 'w1_summary.csv')
reference_summary = read(root.parent / 'results/results_fixed_stack_summary.csv')
reference_group = {(r['scenario'], r['scheduler']): r for r in reference_summary}
comparisons = []
for row in summary:
    reference = reference_group[(row['scenario'], row['scheduler'])]
    mean, ref_mean = float(row['fct_mean']), float(reference['fct_mean'])
    new_group = [r for r in new if r['scenario'] == row['scenario'] and r['name'] == row['scheduler']]
    comparisons.append(dict(scenario=row['scenario'], scheduler=row['scheduler'], runs=int(row['runs']), completed=int(row['completed']), completion_pct=10 * int(row['completed']), reference_completed=int(reference['completed']), fct_mean=mean, reference_fct_mean=ref_mean, fct_diff_pct=(mean/ref_mean-1)*100, fct_median=float(row['fct_median']), fct_p90=float(row['fct_p90']), fct95_mean_completed=float(row['fct95_mean']), fct95_mean_all=statistics.mean(float(r['fct95_s']) for r in new_group), share_p1=float(row['share_p1'])))
with (out / 'reference_comparison.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(comparisons[0]))
    writer.writeheader()
    writer.writerows(comparisons)
stalled = [r for r in new if r['done'] == '0']
with (out / 'stalled_runs.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(new[0]))
    writer.writeheader()
    writer.writerows(stalled)
one = json.loads((out / 'single-path/single_path.json').read_text())
diagnostics = json.loads((out / 'single-path/diagnostics.json').read_text())
rr = next(r for r in comparisons if r['scenario'] == 'dominating' and r['scheduler'] == 'RR')
pass_rr = abs(rr['fct_mean'] / 3.27 - 1) <= .05
sweep_text = (out / 'sweep.log').read_text()
failure_count = sweep_text.count('FAILED rc=')
scenarios = {sc: dict(runs=sum(r['scenario']==sc for r in new), completed=sum(r['scenario']==sc and r['done']=='1' for r in new)) for sc in ('dominating','competing','degrade')}
report = dict(date=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(), rows=len(new), unique_combinations=len(set(new_keys)), missing=sorted(expected-set(new_keys)), duplicates=len(new_keys)-len(set(new_keys)), execution_failures=failure_count, matched_reference_rows=len(new)-len(set((d['scenario'],d['scheduler'],d['seed']) for d in diffs)), differing_fields=len(diffs), completed=sum(r['done']=='1' for r in new), exact_target_bytes=sum(r['rx_app']==r['size'] for r in new), stalled=len(stalled), scenarios=scenarios, simulation_metrics_checked=metrics, new_wall_total_s=round(sum(float(r['wall_s']) for r in new),1), reference_wall_total_s=round(sum(float(r['wall_s']) for r in ref),1), over_five_pct=[r for r in comparisons if abs(r['fct_diff_pct']) >5], single_path=one, single_path_diagnostics=diagnostics, gate=dict(schedulers_pass=failure_count==0 and set(int(r['scheduler']) for r in new)==set(range(7)), dominating_rr_pass=pass_rr, dominating_rr_mean_s=rr['fct_mean'], dominating_rr_target_s=3.27, dominating_rr_difference_pct=(rr['fct_mean']/3.27-1)*100, single_path_pass=all(r['in_gate_range'] for r in one), single_path_full_fct_s=statistics.mean(r['fct_full_s'] for r in one), single_path_upper_bound_s=9.0, single_path_exceeds_upper_pct=(statistics.mean(r['fct_full_s'] for r in one)/9-1)*100, overall='미달: 단일 경로 시간 기준 초과'))
(out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert failure_count == 0

commands = {'sweep':'python3 -u sched-lab/run_sweep.py --seeds 10 --out sched-lab/w1-2026-10-01/w1.csv', 'analysis':'python3 sched-lab/analyze.py sched-lab/w1-2026-10-01/w1.csv', 'one_path':'build/scratch/wns3-mpquic-one-path --SchedulerType=4 --Seed=<1..3> --Size=5242880 --Rate0a=5 --Rate0b=5 --Delay0a=50 --Delay0b=50 --LossRate=0 --CcType=1'}
(out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
version = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
branch = subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()
patches = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root.parent/'patches').glob('*.patch'))}
(out / 'provenance.json').write_text(json.dumps(dict(date=report['date'], code_commit=version, branch=branch, applied_patches={n:h for n,h in patches.items() if not n.startswith('00-')}, code_change='04 adds only passive Rx tracing and result printing to the one-path executable; multi-path sweep unchanged'),indent=2)+'\n')

sys.argv=[str(root/'sched-lab/analyze.py'),str(out/'w1.csv')]
ns=runpy.run_path(str(root/'sched-lab/analyze.py'),run_name='__main__')
ns['fig'].savefig(out/'w1_fct.svg')
svg=(out/'w1_fct.svg').read_text()
svg=svg[svg.index('<svg'):]
html='<!doctype html><html lang="ko"><meta charset="utf-8"><title>1주차 FCT 결과</title><body style="font-family:system-ui;padding:18px"><h1 style="background:#d9ead3;padding:12px">1주차 · 210회 결과</h1><ul><li>3시나리오 × 7스케줄러 × 10seed = 210회</li><li>FCT: 완료 실행만 표시 / n/N: 완료 수·전체 실행 수</li><li>기준 데이터 210행과 시뮬레이션 지표 동일</li><li>게이트 1: 단일 경로 시간 기준 초과로 미달</li></ul><div style="width:100%;overflow:auto">'+svg+'</div></body></html>'
(out / 'w1_plot.html').write_text(html)
print(json.dumps(report, ensure_ascii=False, indent=2))
