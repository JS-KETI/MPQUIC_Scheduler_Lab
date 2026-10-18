#!/usr/bin/env python3
"""Week 4, new-directory-only controlled experiments. No transport algorithm changes."""
import argparse, concurrent.futures, csv, hashlib, json, os, platform, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from run_sweep import SCENARIOS, NAMES, find_binary

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['scheduler','seed','size','fct_s','fct95_s','rx_app','rx_p0','rx_p1','delay_p0_ms','delay_p1_ms','done']
BASE = dict(Size=5242880, LossRate=0, LossUnit='byte', BufferBytes=40000000,
            QueueMaxPackets=0, CcType=1, CompletionGraceMs=250, SimEnd=60, BenchMetrics=1, PathCount=2)

def cases(group):
    rows=[]
    def add(condition, scenario, scheds=range(7), seeds=range(1,6), **params):
        for s in scheds:
            for seed in seeds:
                rows.append(dict(condition=condition, scenario=scenario, scheduler=s, name=NAMES[s], seed=seed,
                                 args=dict(BASE, **SCENARIOS[scenario]) | params | dict(SchedulerType=s, Seed=seed)))
    if group == 'pilot':
        add('reference','dominating', [0,6], [1])
        for sc in SCENARIOS: add('long',sc,[6],[1],Size=52428800,SimEnd=180)
        add('queue100','competing',[6],[1],QueueMaxPackets=100)
        add('buffer1m','competing',[6],[1],BufferBytes=1048576)
        add('loss01','competing',[6],[1],LossUnit='packet',LossRate=0.001)
        add('loss1','competing',[6],[1],LossUnit='packet',LossRate=0.01)
        add('four_path','dominating',[0,6],[1],PathCount=4)
        add('metrics_off','dominating',[6],[1],BenchMetrics=0)
    elif group == 'short':
        for sc in SCENARIOS: add('reference',sc)
        for name, params in [('early',dict(EventTime=.75)),('late',dict(EventTime=3)),
                             ('rate_mild',dict(Rate1After=3)),('rate_severe',dict(Rate1After=.5)),
                             ('delay_mild',dict(Delay1After=80)),('delay_severe',dict(Delay1After=180))]:
            add(name,'degrade',**params)
    elif group == 'long':
        for sc in SCENARIOS: add('long',sc,seeds=range(1,11),Size=52428800,SimEnd=180)
    elif group == 'robustness':
        variants = [('loss01',dict(LossUnit='packet',LossRate=.001)),('loss1',dict(LossUnit='packet',LossRate=.01)),
                    ('queue100',dict(QueueMaxPackets=100)),('queue1000',dict(QueueMaxPackets=1000)),
                    ('buffer1m',dict(BufferBytes=1048576)),('buffer8m',dict(BufferBytes=8388608))]
        for cond, args in variants:
            for sc in SCENARIOS: add(cond,sc,**args)
    elif group == 'four_path':
        add('four_path','dominating',range(8),[1],PathCount=4)
    else: raise ValueError(group)
    for n,r in enumerate(rows): r['run_id']=f'{n+1:04}-{r["condition"]}-{r["scenario"]}-s{r["scheduler"]}-seed{r["seed"]}'
    return rows

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jsonwrite(p, obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def run_one(item, out, binary, env, timeout):
    folder=out/'runs'/item['run_id'];folder.mkdir(parents=True)
    command=[str(binary)]+[f'--{k}={v}' for k,v in item['args'].items()]
    meta=dict(item,command=command,cwd=str(ROOT),started_utc=datetime.now(timezone.utc).isoformat())
    jsonwrite(folder/'command.json',meta)
    start=time.monotonic(); rc=None; status='error'
    try:
        p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=timeout)
        stdout,stderr,rc=p.stdout,p.stderr,p.returncode
        lines=[x for x in stdout.splitlines() if x.startswith('RESULT,')]
        status='ok' if rc==0 and len(lines)==1 else 'process_error'
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout or b'';stderr=e.stderr or b''
        stdout=stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
        stderr=stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
        status='wall_timeout';lines=[]
    (folder/'stdout.log').write_text(stdout);(folder/'stderr.log').write_text(stderr)
    row={k:item[k] for k in ['run_id','condition','scenario','scheduler','name','seed']}
    row.update(status=status,returncode=rc,wall_s=round(time.monotonic()-start,4),size=item['args']['Size'],
               sim_end=item['args']['SimEnd'],loss_unit=item['args']['LossUnit'],loss_rate=item['args']['LossRate'],
               queue_packets=item['args']['QueueMaxPackets'],buffer_bytes=item['args']['BufferBytes'],path_count=item['args']['PathCount'])
    if status=='ok':
        values=lines[0].split(',')[1:]
        if len(values)!=len(FIELDS): raise ValueError(lines)
        row.update(dict(zip(FIELDS,values)))
        metrics=[x for x in stdout.splitlines() if x.startswith('METRICS4,')]
        if metrics:
            names=['full_fct_s','queue_drops','error_drops','active_subflows']+[f'{d}_payload_p{i}' for i in range(4) for d in ['tx','rx']]
            row.update(dict(zip(names,metrics[-1].split(',')[1:])))
    jsonwrite(folder/'result.json',row)
    return row

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--group',choices=['pilot','short','long','robustness','four_path'],required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--timeout',type=int,default=180);p.add_argument('--plan-only',action='store_true')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    plan=cases(a.group);jsonwrite(out/'plan.json',plan)
    if a.plan_only: print(len(plan));return
    binary=Path(find_binary(str(ROOT)));env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/lib'))
    tracked=subprocess.check_output(['git','ls-files','scratch','src/quic','sched-lab'],cwd=ROOT,text=True).splitlines()
    source_hashes={f:sha(ROOT/f) for f in tracked if (ROOT/f).is_file() and not '/__pycache__/' in f}
    sources=out/'source';sources.mkdir()
    for name in ['week4_run.py','week4_analyze.py','analyze.py','stats.py','run_sweep.py']:
        f=ROOT/'sched-lab'/name
        if f.exists(): (sources/name).write_bytes(f.read_bytes())
    (sources/'mpquic-sched-lab.cc').write_bytes((ROOT/'scratch/mpquic-sched-lab.cc').read_bytes())
    (sources/'working.patch').write_bytes(subprocess.check_output(['git','diff','HEAD','--','scratch','src/quic','sched-lab'],cwd=ROOT))
    meta=dict(group=a.group,planned=len(plan),started_utc=datetime.now(timezone.utc).isoformat(),
              commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              binary_sha256=sha(binary),source_hashes=source_hashes,platform=platform.platform(),
              python=platform.python_version(),cpu=Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0],
              compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
              supplied_reference='No supplied reference for new conditions; reference rows compare accepted week2 baseline.',
              patch_state='01+02 + accepted week2 common fixes + week3 + recorded week4 harness delta',
              full_command=__import__('sys').argv,wall_timeout_s=a.timeout)
    jsonwrite(out/'metadata.json',meta)
    completed=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        pending=[pool.submit(run_one,r,out,binary,env,a.timeout) for r in plan]
        for f in concurrent.futures.as_completed(pending):
            row=f.result();completed.append(row)
            if len(completed)%10==0 or row['status']!='ok' or len(completed)==len(plan):
                print(f'{len(completed)}/{len(plan)} {row["run_id"]} status={row["status"]} done={row.get("done")} rx={row.get("rx_app")}',flush=True)
    completed.sort(key=lambda r:r['run_id'])
    fields=list(dict.fromkeys(k for row in completed for k in row))
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(completed)
    jsonwrite(out/'execution.json',dict(planned=len(plan),rows=len(completed),process_ok=sum(r['status']=='ok' for r in completed),
                                      failures=[r['run_id'] for r in completed if r['status']!='ok'],finished_utc=datetime.now(timezone.utc).isoformat()))
    print(out,flush=True)

if __name__=='__main__':main()
