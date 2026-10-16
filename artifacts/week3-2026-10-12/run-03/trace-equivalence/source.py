import csv, hashlib, json, os, subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from run_sweep import SCENARIOS,find_binary
r=Path.cwd();out=r/'artifacts/week3-2026-10-12/run-03/trace-equivalence';out.mkdir(exist_ok=False)
tasks=[(s,None) for s in SCENARIOS]+[('dominating',p) for p in (.1,.3,.5)]+[('degrade',.5)]
(out/'protocol.json').write_text(json.dumps(dict(planned_pairs=7,planned_runs=14,
    purpose='toggle only LabLogPrefix with the original Observe diagnostic enabled on both sides; compare all OBS lines and RESULT',
    tasks=tasks,started=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2))
env=dict(os.environ,LD_LIBRARY_PATH=str(r/'build/lib'));rows=[]
for i,(s,p) in enumerate(tasks,1):
    obs=[];res=[]
    for enabled in (0,1):
        d=out/f'{i:02d}-{s}-{p}-lab{enabled}';d.mkdir()
        cmd=[find_binary(str(r)), '--SchedulerType=7','--Seed=1','--Size=5242880', '--CcType=1','--LossRate=0','--CompletionGraceMs=250','--SimEnd=60','--Observe=1']
        cmd += [f'--{k}={v}' for k,v in SCENARIOS[s].items()]
        if p is not None:cmd += ['--FixedRatio=1',f'--Path0Share={p}']
        if enabled:cmd += [f'--LabLogPrefix={d/"trace"}']
        x=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True)
        (d/'command.json').write_text(json.dumps(dict(command=cmd,returncode=x.returncode),indent=2))
        (d/'stdout.log').write_text(x.stdout);(d/'stderr.log').write_text(x.stderr)
        assert x.returncode==0
        result=[z for z in x.stdout.splitlines() if z.startswith('RESULT,')];assert len(result)==1
        obs.append([z for z in x.stderr.splitlines() if z.startswith('OBS,')]);res.append(result[0])
    rows.append(dict(scenario=s,share0='' if p is None else p,seed=1,
        obs_rows_disabled=len(obs[0]),obs_rows_enabled=len(obs[1]),
        obs_exact_match=int(obs[0]==obs[1]),result_exact_match=int(res[0]==res[1]),
        done=int(res[0].split(',')[-1]),rx_app=int(res[0].split(',')[6])))
with (out/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'source.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(rows,indent=2));assert all(x['obs_exact_match'] and x['result_exact_match'] and x['done'] and x['rx_app']==5242880 for x in rows)
