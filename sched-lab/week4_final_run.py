"""Replay the original week4 command plans on one integrated QUIC version."""
from pathlib import Path
import argparse,sys,json,csv,os,subprocess,concurrent.futures,platform,hashlib,time,copy
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sched-lab'))
from week4_run import run_one,find_binary,jsonwrite,sha

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=ROOT/'artifacts/week4/analysis/2026-10-18/run-01/results.csv'
 original=list(csv.DictReader(old.open()));assert len(original)==1163
 plan=[];before={r['run_id']:r for r in original};assert len(before)==1163
 for r in original:
  source=ROOT/'artifacts/week4/runs/2026-10-18'/r['source_run']/'runs'/r['run_id']/'command.json'
  d=json.loads(source.read_text());item={k:copy.deepcopy(d[k]) for k in ['run_id','condition','scenario','scheduler','name','seed','args']}
  item['source_command']=str(source.relative_to(ROOT));item['original_done']=int(r['done']);item['original_rx']=int(r['rx_app'])
  if a.pilot:
   choose=(r['condition']=='reference' and r['scheduler'] in ['0','6'] and r['seed']=='1') or (r['condition'] in ['buffer1m','queue100','loss1'] and r['scheduler'] in ['0','2','6'] and r['seed']=='1') or (r['condition']=='loss01' and r['scheduler'] in ['2','6'] and r['seed']=='1') or (r['condition']=='long' and r['done']=='0') or r['condition']=='four_path'
   if not choose:continue
   item['args']['DiagnosticPrefix']=str(out/'runs'/item['run_id']/'diag')
  # Every transport/environment argument is replayed verbatim. Diagnostics are
  # optional read-only outputs, and are disabled for the complete final run.
  assert all(v==d['args'][k] for k,v in item['args'].items() if not k.startswith('Diagnostic'))
  plan.append(item)
 assert a.pilot or len(plan)==1163
 jsonwrite(out/'plan.json',plan)
 binary=Path(find_binary(str(ROOT)));env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/lib'))
 git=lambda args:subprocess.check_output(['git',*args],cwd=ROOT)
 patch=git(['diff','HEAD','--','src/quic','scratch','sched-lab']);(out/'working.patch').write_bytes(patch)
 files=git(['ls-files','src/quic','scratch','sched-lab']).decode().splitlines()
 hashes={f:sha(ROOT/f) for f in files if (ROOT/f).is_file() and '__pycache__' not in f}
 jsonwrite(out/'metadata.json',dict(commit=git(['rev-parse','HEAD']).decode().strip(),started_utc=datetime.now(timezone.utc).isoformat(),full_command=sys.argv,planned=len(plan),pilot=a.pilot,original_csv_sha256=sha(old),binary_sha256=sha(binary),patch_sha256=hashlib.sha256(patch).hexdigest(),source_sha256=hashes,python=platform.python_version(),platform=platform.platform(),compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],cpu=Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0],sim_end_and_buffers='verbatim original commands; no extension or enlargement',baseline='preserved accepted week2; compare previous week4 separately',wall_timeout_s=240))
 ldd=subprocess.check_output(['ldd',str(binary)],env=env,text=True);libraries={}
 for line in ldd.splitlines():
  for word in line.split():
   if word.startswith('/') and Path(word).is_file():libraries[str(Path(word).resolve())]=sha(Path(word))
 jsonwrite(out/'runtime-libraries.json',dict(captured_before_execution=True,ld_library_path=env['LD_LIBRARY_PATH'],ldd=ldd,libraries=libraries))
 complete=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
  futures={pool.submit(run_one,d,out,binary,env,240):d for d in plan}
  for future in concurrent.futures.as_completed(futures):
   d=futures[future]
   try:r=future.result()
   except ValueError as error:
    r={k:d[k] for k in ['run_id','condition','scenario','scheduler','name','seed']}
    r.update(status='parse_error',returncode=None,wall_s=None,size=d['args']['Size'],sim_end=d['args']['SimEnd'],loss_unit=d['args']['LossUnit'],loss_rate=d['args']['LossRate'],queue_packets=d['args']['QueueMaxPackets'],buffer_bytes=d['args']['BufferBytes'],path_count=d['args']['PathCount'],parse_error=str(error))
    jsonwrite(out/'runs'/d['run_id']/'result.json',r)
   r['original_done']=d['original_done'];r['original_rx']=d['original_rx'];complete.append(r)
   if len(complete)%25==0 or len(complete)==len(plan) or r['status']!='ok': print(len(complete),len(plan),r['run_id'],r['status'],r.get('done'),r.get('rx_app'),flush=True)
 complete.sort(key=lambda r:r['run_id']);fields=list(dict.fromkeys(k for r in complete for k in r))
 with (out/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(complete)
 jsonwrite(out/'execution.json',dict(planned=len(plan),rows=len(complete),process_ok=sum(r['status']=='ok' for r in complete),completed=sum(r.get('done')=='1' for r in complete),full_received=sum(r.get('rx_app')==str(r['size']) for r in complete),previously_completed=sum(r['original_done']==1 for r in complete),regressions=[r['run_id'] for r in complete if r['original_done']==1 and (r.get('done')!='1' or r.get('rx_app')!=str(r['size']))],finished_utc=datetime.now(timezone.utc).isoformat()))
 print(json.loads((out/'execution.json').read_text()),flush=True)
if __name__=='__main__':main()
