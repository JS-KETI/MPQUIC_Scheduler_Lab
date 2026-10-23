"""Replay a named subset for one-factor diagnosis, preserving exact base settings."""
from pathlib import Path
import argparse,csv,json,copy,sys,subprocess,os,hashlib,concurrent.futures
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sched-lab'))
from week4_run import run_one,find_binary,jsonwrite,sha
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--ids',nargs='+',required=True);p.add_argument('--diagnostics',action='store_true');a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);base={x['run_id']:x for x in json.loads((a.source/'plan.json').read_text())};previous={x['run_id']:x for x in csv.DictReader((a.source/'results.csv').open())}
 plan=[copy.deepcopy(base[i]) for i in a.ids];assert len(set(a.ids))==len(a.ids)
 for d in plan:
  if a.diagnostics:d['args']['DiagnosticPrefix']=str(a.out/'runs'/d['run_id']/'diag')
  assert {k:v for k,v in d['args'].items() if not k.startswith('Diagnostic')}=={k:v for k,v in base[d['run_id']]['args'].items() if not k.startswith('Diagnostic')}
 jsonwrite(a.out/'plan.json',plan)
 binary=Path(find_binary(str(ROOT)));env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/lib'))
 patch=subprocess.check_output(['git','diff','HEAD','--','src/quic','scratch','sched-lab'],cwd=ROOT);(a.out/'working.patch').write_bytes(patch)
 ldd=subprocess.check_output(['ldd',str(binary)],env=env,text=True);libs={}
 for line in ldd.splitlines():
  for word in line.split():
   if word.startswith('/') and Path(word).is_file():libs[str(Path(word).resolve())]=sha(Path(word))
 jsonwrite(a.out/'metadata.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),started_utc=datetime.now(timezone.utc).isoformat(),command=sys.argv,source_run=str(a.source),binary_sha256=sha(binary),patch_sha256=hashlib.sha256(patch).hexdigest(),runtime_libraries=libs,planned=len(plan)))
 done=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  fs={pool.submit(run_one,d,a.out,binary,env,240):d for d in plan}
  for f in concurrent.futures.as_completed(fs):
   r=f.result();r['base_done']=previous[r['run_id']]['done'];r['base_rx']=previous[r['run_id']]['rx_app'];done.append(r);print(len(done),len(plan),r['run_id'],r['status'],r.get('done'),r.get('rx_app'),flush=True)
 done.sort(key=lambda r:r['run_id']);fields=list(dict.fromkeys(k for r in done for k in r))
 with (a.out/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(done)
 jsonwrite(a.out/'execution.json',dict(rows=len(done),process_ok=sum(r['status']=='ok' for r in done),completed=sum(r.get('done')=='1' for r in done),full_received=sum(r.get('rx_app')==str(r['size']) for r in done)))
if __name__=='__main__':main()
