from pathlib import Path
import csv,json,collections
ROOT=Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic');base=ROOT/'artifacts/week4/runs/2026-10-18/run-08'
fields=json.loads((base/'metadata.json').read_text())['schema'];results=[]
orig=list(csv.DictReader((ROOT/'artifacts/week4/analysis/2026-10-18/run-01/results.csv').open()));original={r['run_id']:r for r in orig}
matches=[]
for r in csv.DictReader((base/'results.csv').open()):
 folder=base/'runs'/r['run_id'];lines=(folder/'stdout.log').read_text().splitlines()
 ev=[x.split(',') for x in lines if x.startswith('DIAG_')]
 samples=collections.defaultdict(list)
 for row in csv.reader((folder/'diag-state.csv').open()):
  if float(row[1])>=float(r['sim_end']):continue
  d=dict(zip(fields[row[0]].split(','),row[1:]));samples[row[0]].append(d)
 app=samples['APP'][-1];sock=[d for d in samples['SOCKET'] if d['node']=='4'][-1]
 stx=[d for d in samples['STREAM'] if d['node']=='4' and d['stream']=='1'][-1]
 srx=[d for d in samples['STREAM'] if d['node']=='5' and d['stream']=='1'][-1]
 paths=[d for d in samples['PATH'] if d['node']=='4' and d['time']==app['time']]
 rxabort=[e for e in ev if e[0]=='DIAG_ABORT' and 'full RX buffer' in e[-1]]
 earlyclose=[e for e in ev if e[0]=='DIAG_CLOSE' and e[2]=='4' and float(e[1])<float(r['sim_end']) and e[3]=='4' and e[4]=='1' and e[6]=='1']
 if rxabort:group='rx_buffer_abort'
 elif int(stx['app_payload_bytes'])>0 and int(sock['app_frame_bytes'])==0:group='stream_backlog'
 elif earlyclose and any(int(e[5])>0 for e in earlyclose):group='premature_close_socket_backlog'
 elif float(app['time'])-float(app['last_sink_s'])<1:group='progress_at_deadline'
 elif int(srx['waiting_payload'])>0:group='receiver_gap'
 else:group='unclassified'
 out={k:r[k] for k in ['run_id','condition','scenario','scheduler','name','seed','size','rx_app']}
 out.update(group=group,last_sink_s=app['last_sink_s'],last_tx_s=app['last_tx_payload_s'],last_rx_payload_s=app['last_rx_payload_s'],app_accepted=app['accepted'],sender_state=sock['state'],socket_backlog=sock['app_frame_bytes'],stream_backlog=stx['app_payload_bytes'],receiver_waiting=srx['waiting_payload'],rx_buffer_abort_count=len(rxabort),first_rx_abort=rxabort[0][1] if rxabort else '',early_close_count=len(earlyclose),first_early_close=earlyclose[0][1] if earlyclose else '',inflight=sum(int(p['inflight_frame_bytes']) for p in paths),cwnd=sum(int(p['cwnd_frame_bytes']) for p in paths),alarms=sum(int(p['alarm_running']) for p in paths))
 results.append(out)
 keys=['done','rx_app','fct_s','fct95_s','rx_p0','rx_p1','delay_p0_ms','delay_p1_ms','full_fct_s','queue_drops','error_drops']
 matches.append(all(float(r[k])==float(original[r['run_id']][k]) for k in keys))
print('reproduced',sum(matches),len(matches));print('groups',dict(collections.Counter(r['group'] for r in results)));print('cross',dict(collections.Counter((r['condition'],r['group']) for r in results)))
for group in dict.fromkeys(r['group'] for r in results):
 print(group,[r for r in results if r['group']==group][:2])
out=ROOT/'artifacts/week4/analysis/2026-10-18/diagnosis-01';out.mkdir(exist_ok=True)
with (out/'classification.csv').open('w',newline='') as f:w=csv.DictWriter(f,results[0]);w.writeheader();w.writerows(results)
(out/'classification-validation.json').write_text(json.dumps(dict(reproduced=sum(matches),total=len(matches),matched_fields=keys,groups=dict(collections.Counter(r['group'] for r in results))),indent=2))
