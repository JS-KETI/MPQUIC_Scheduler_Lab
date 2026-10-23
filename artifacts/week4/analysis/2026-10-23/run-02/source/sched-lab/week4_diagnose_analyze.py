"""Summarize the preserved week4 diagnostic experiments; does not run simulations."""
from pathlib import Path
import csv, json, collections, hashlib, subprocess, shutil
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT/'artifacts/week4/runs/2026-10-18'
OUT=ROOT/'artifacts/week4/analysis/2026-10-18/diagnosis-01'
def read(path): return list(csv.DictReader(path.open()))
def write(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
original={r['run_id']:r for r in read(ROOT/'artifacts/week4/analysis/2026-10-18/run-01/results.csv')}
initial=OUT/'classification-initial.csv'
if not initial.exists(): shutil.copy2(OUT/'classification.csv',initial)
rows=read(initial)
rx={r['run_id']:r for r in read(RUNS/'run-10/results.csv')}
q={r['run_id']:r for r in read(RUNS/'run-13/results.csv')}
for r in rows:
    rid=r['run_id'];r['initial_group']=r['group']
    r['evidence_run']='run-08'
    r['max_tx_frame_bundle_bytes']='';r['max_rx_frame_bundle_bytes']=''
    r['oversize_tx_bundles']='';r['oversize_rx_bundles']=''
    if rid in rx:
        events=[s.split(',') for s in (RUNS/'run-10/runs'/rid/'stdout.log').read_text().splitlines() if s.startswith('DIAG_ABORT,') and 'full RX buffer' in s]
        assert events and all(e[2]=='5' for e in events)
        r.update(group='rx_buffer_abort',evidence_run='run-10',rx_buffer_abort_count=len(events),first_rx_abort=events[0][1])
    if rid in q:
        summary=[s.split(',') for s in (RUNS/'run-13/runs'/rid/'stdout.log').read_text().splitlines() if s.startswith('DIAG_WIRE_SUMMARY,')]
        assert len(summary)==1, rid
        _,mt,mr,ot,orr=summary[0]
        assert int(mt)>65507 and int(ot)>0 and int(orr)==0
        r.update(group='oversized_retransmission_bundle',evidence_run='run-13',max_tx_frame_bundle_bytes=mt,max_rx_frame_bundle_bytes=mr,oversize_tx_bundles=ot,oversize_rx_bundles=orr)
    assert r['group'] not in ['receiver_gap','unclassified']
write(OUT/'classification.csv',rows)
byid={r['run_id']:r for r in rows}
fields='fct_s fct95_s rx_app rx_p0 rx_p1 delay_p0_ms delay_p1_ms done full_fct_s queue_drops error_drops active_subflows tx_payload_p0 rx_payload_p0 tx_payload_p1 rx_payload_p1 tx_payload_p2 rx_payload_p2 tx_payload_p3 rx_payload_p3 size'.split()
reproductions=[]
for run in ['run-08','run-10','run-13']:
    rr=read(RUNS/run/'results.csv')
    differences=[(r['run_id'],k,r[k],original[r['run_id']][k]) for r in rr for k in fields if Decimal(r[k])!=Decimal(original[r['run_id']][k])]
    assert not differences,differences[:4]
    reproductions.append(dict(run=run,runs=len(rr),fields=len(fields),matched_cells=len(rr)*len(fields)))
groups=collections.Counter(r['group'] for r in rows)
assert groups==dict(premature_close_socket_backlog=78,stream_backlog=68,rx_buffer_abort=37,oversized_retransmission_bundle=87,progress_at_deadline=7)
groupstats=[dict(group=g,count=n,conditions='; '.join(f'{c}={v}' for c,v in collections.Counter(r['condition'] for r in rows if r['group']==g).items())) for g,n in groups.items()]
write(OUT/'group-summary.csv',groupstats)
combos=collections.Counter((r['group'],r['condition'],r['scenario'],r['scheduler'],r['name']) for r in rows)
write(OUT/'group-combinations.csv',[dict(zip(['group','condition','scenario','scheduler','name','incomplete'],[*k,v])) for k,v in sorted(combos.items())])
totals=[];trials=[];strata=[]
for i in range(7,21):
    run=f'run-{i:02d}';rr=read(RUNS/run/'results.csv')
    done=sum(r['done']=='1' for r in rr);full=sum(r['rx_app']==r['size'] for r in rr)
    assert all(r['status']=='ok' and r['returncode']=='0' for r in rr)
    totals.append(dict(run=run,executions=len(rr),completed=done,full_received=full))
    for r in rr:
        trials.append(dict(run=run,run_id=r['run_id'],original_group=byid.get(r['run_id'],{}).get('group','reference_complete'),condition=r['condition'],scenario=r['scenario'],scheduler=r['scheduler'],name=r['name'],seed=r['seed'],sim_end=r['sim_end'],done=r['done'],rx_app=r['rx_app'],size=r['size'],fct_s=r['fct_s'],full_fct_s=r['full_fct_s']))
    if i>=14:
        for g in groups:
            ss=[r for r in rr if byid[r['run_id']]['group']==g]
            if ss:strata.append(dict(run=run,original_group=g,executions=len(ss),completed=sum(r['done']=='1' for r in ss),full_received=sum(r['rx_app']==r['size'] for r in ss)))
write(OUT/'experiment-summary.csv',totals);write(OUT/'experiment-results.csv',trials);write(OUT/'candidate-by-original-group.csv',strata)
frozen=[]
for line in (ROOT/'artifacts/week4/SHA256SUMS').read_text().splitlines():
    expected,rel=line.split('  ',1);p=ROOT/'artifacts/week4'/rel
    assert sha(p)==expected,rel
    frozen.append(rel)
baseline='artifacts/week2-completion-2026-10-08/run-01/'
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','47e82c0','--',baseline,'artifacts/BASELINE.json'],cwd=ROOT,text=True).splitlines()
for rel in paths:
    expected=subprocess.check_output(['git','show',f'47e82c0:{rel}'],cwd=ROOT)
    assert (ROOT/rel).read_bytes()==expected,rel
validation=dict(original_failures=len(rows),groups=groups,matched_fields=fields,reproductions=reproductions,additional_executions=sum(x['executions'] for x in totals),frozen_week4_files_preserved=len(frozen),approved_baseline_files_preserved=len(paths),candidate_adopted=False)
(OUT/'classification-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
for name in ['classification.csv','group-summary.csv','group-combinations.csv','experiment-summary.csv','experiment-results.csv','candidate-by-original-group.csv']:
    shutil.copy2(OUT/name,ROOT/'reports/week4/data'/('incomplete-'+name))
print(json.dumps(validation,ensure_ascii=False,indent=2))
print('CANDIDATE STRATA',json.dumps(strata))
for i in [9,12,17,19,20]:
    rr=read(RUNS/f'run-{i:02d}'/'results.csv');full=[r for r in rr if r['rx_app']==r['size']]
    print('RANGE',i,min(float(r['fct_s']) for r in full),max(float(r['fct_s']) for r in full))
print('FILES',sum(1 for p in RUNS.glob('run-*/*') if p.is_file()))
