import argparse,sys,json,csv,hashlib,os,subprocess,concurrent.futures,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sched-lab'))
from week4_run import run_one,find_binary,jsonwrite,sha
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['pilot','all','extend','smallholes','packet','lossextend','closefix','closeextend','streamfix','queuefix','queueobserve'],required=True);p.add_argument('--out',required=True);a=p.parse_args()
out=ROOT/a.out;out.mkdir(parents=True,exist_ok=False)
rows=list(csv.DictReader((ROOT/'artifacts/week4/analysis/2026-10-18/run-01/results.csv').open()))
failed=[r for r in rows if r['done']=='0']
assert len(failed)==277
selected=failed
if a.mode=='pilot':
 selected=[]
 for cond,sc,s,seed in [('buffer1m','competing',6,1),('buffer1m','dominating',3,1),('buffer1m','dominating',6,1),('queue100','competing',6,1),('queue100','dominating',6,1),('loss01','competing',2,1),('loss01','dominating',2,5),('loss1','dominating',1,1),('loss1','degrade',0,1),('loss1','degrade',5,3)]:
  selected += [r for r in failed if (r['condition'],r['scenario'],r['scheduler'],r['seed'])==(cond,sc,str(s),str(seed))]
 selected += [r for r in rows if r['condition']=='reference' and r['scenario']=='dominating' and r['scheduler']=='6' and r['seed']=='1']
 selected += [r for r in failed if r['condition']=='long']
elif a.mode=='extend': selected=[r for r in failed if r['condition']=='long']
elif a.mode=='smallholes':
 classified=list(csv.DictReader((ROOT/'artifacts/week4/analysis/2026-10-18/diagnosis-01/classification.csv').open()))
 ids={r['run_id'] for r in classified if r['condition']=='buffer1m' and r['group'] in ['receiver_gap','rx_buffer_abort']}
 selected=[r for r in failed if r['run_id'] in ids]
elif a.mode=='packet':
 ids=['0241-queue100-dominating-s6-seed1','0276-queue100-competing-s6-seed1','0219-queue100-dominating-s1-seed4','0422-buffer1m-dominating-s0-seed2','0486-buffer1m-competing-s6-seed1','0015-loss01-dominating-s2-seed5']
 selected=[r for r in failed if r['run_id'] in ids]
elif a.mode=='lossextend': selected=[r for r in failed if r['run_id'] in ['0178-loss1-degrade-s0-seed3','0180-loss1-degrade-s0-seed5','0203-loss1-degrade-s5-seed3']]
elif a.mode=='closefix': selected=[r for r in failed if r['condition'] in ['loss01','loss1'] or r['run_id']=='0100-long-competing-s2-seed10']
elif a.mode=='closeextend':
 ids={r['run_id'] for r in csv.DictReader((ROOT/'artifacts/week4/runs/2026-10-18/run-14/results.csv').open()) if r['done']=='0' and r['condition']!='long'}
 selected=[r for r in failed if r['run_id'] in ids]
elif a.mode=='streamfix': selected=[r for r in failed if r['condition']=='buffer1m']
elif a.mode in ['queuefix','queueobserve']: selected=[r for r in failed if r['condition']=='queue100']
plan=[]
for r in selected:
 src=ROOT/'artifacts/week4/runs/2026-10-18'/r['source_run']/'runs'/r['run_id']
 d=json.loads((src/'command.json').read_text());d={k:d[k] for k in ['run_id','condition','scenario','scheduler','name','seed','args']};d['original']=str(src.relative_to(ROOT));d['original_rx']=int(r['rx_app']);d['original_done']=int(r['done'])
 if a.mode=='extend':d['args']['SimEnd']=600
 if a.mode=='lossextend':d['args']['SimEnd']=300
 if a.mode=='closeextend':d['args']['SimEnd']=300
 if a.mode=='closefix' and r['condition']=='long':d['args']['SimEnd']=600
 if a.mode=='packet':d['args']['DiagnosticPackets']=1
 d['args']['DiagnosticPrefix']=str(out/'runs'/d['run_id']/'diag')
 plan.append(d)
jsonwrite(out/'plan.json',plan)
binary=Path(find_binary(str(ROOT)));env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/lib'))
patch=subprocess.check_output(['git','diff','HEAD'],cwd=ROOT);(out/'working.patch').write_bytes(patch)
jsonwrite(out/'metadata.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),binary_sha256=sha(binary),patch_sha256=hashlib.sha256(patch).hexdigest(),mode=a.mode,command=sys.argv,source='existing main 277; no baseline overwrite',schema={
'APP':'time,accepted,rx_app,last_sink_s,last_tx_payload_s,last_rx_payload_s',
'SOCKET':'time,node,state,app_frame_bytes,available_bytes,max_data,close_on_empty,connected,send_event,idle_event,drain_event,pacing_event',
'PATH':'time,node,path,inflight_frame_bytes,cwnd_frame_bytes,last_rtt,srtt,high_tx,last_acked,alarm_running,next_alarm_s,alarm_type,tlp,rto,cc_state',
'STREAM':'time,node,stream,app_payload_bytes,available_bytes,sent_offset,recv_offset,send_event,send_state,recv_state,fin,stored_payload,waiting_payload'}))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 fs={pool.submit(run_one,d,out,binary,env,240):d for d in plan}
 for f in concurrent.futures.as_completed(fs):
  r=f.result();d=fs[f];r['original_rx']=d['original_rx'];r['original_done']=d['original_done'];results.append(r)
  print(len(results),len(plan),r['run_id'],r['status'],r.get('done'),r.get('rx_app'),flush=True)
results.sort(key=lambda r:r['run_id']);keys=list(dict.fromkeys(k for r in results for k in r))
with (out/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(results)
print('DONE',len(results),flush=True)
