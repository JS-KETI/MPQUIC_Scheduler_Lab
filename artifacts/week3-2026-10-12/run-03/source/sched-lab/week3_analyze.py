#!/usr/bin/env python3
"""Analyze week-3 raw observations without changing simulations or exclusions."""
import argparse, csv, hashlib, json, math, statistics
from collections import defaultdict, Counter
from pathlib import Path

def read(p):
    with p.open(newline='') as f: return list(csv.DictReader(f))
def write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    with p.open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def quantile(v,q):
    if not v:return None
    v=sorted(v);i=(len(v)-1)*q;a=int(i);return v[a]+(v[min(a+1,len(v)-1)]-v[a])*(i-a)
def mean(v):return statistics.mean(v) if v else None
def key(p):return tuple(p[k] for k in ('path','packet_number','stream','offset','payload_bytes'))
def interval_add(intervals, a,b):
    overlap=sum(max(0,min(b,y)-max(a,x)) for x,y in intervals)
    merged=[];done=False
    for x,y in intervals:
        if y<a:merged.append((x,y))
        elif b<x:
            if not done:merged.append((a,b));done=True
            merged.append((x,y))
        else:a=min(a,x);b=max(b,y)
    if not done:merged.append((a,b))
    return merged,overlap

def analyze(root):
    out=root/'analysis';out.mkdir(exist_ok=True)
    results=read(root/'results.csv');fixed=[];all_metrics=[];observations=[];usage=[];invariants=[]
    for r in results:
        rd=root/'runs'/r['run_id']; dp=rd/'trace-decisions.csv'
        if not dp.exists():continue
        ds=read(dp);packets=read(rd/'trace-packets.csv');reorders=read(rd/'trace-reorder.csv')
        groups=defaultdict(list)
        for d in ds:
            if d['node']=='4':groups[d['connection'],d['decision_id']].append(d)
        bytime=defaultdict(list)
        for k,g in groups.items():bytime[round(float(g[0]['time_s']),10)].append(k)
        tx=[p for p in packets if p['node']=='4' and p['direction']=='Tx']
        rx=[p for p in packets if p['node']=='5' and p['direction']=='Rx']
        rxkeys={}
        for p in rx:
            rxkeys.setdefault(key(p),float(p['time_s']))
        txtime=defaultdict(list)
        for p in tx:txtime[round(float(p['time_s']),10)].append(p)
        cumulative_gap=0.;tot=[0,0];eligible=[0,0];ex=[0,0];count=Counter();stop=Counter()
        for (conn,did),g in groups.items():
            g=sorted(g,key=lambda d:int(d['path']))
            limited=any(int(d['cwnd_limited']) for d in g)
            count['decisions']+=1;count['excluded' if limited else 'eligible']+=1
            for d in g:
                path=int(d['path']);b=int(d['actual_frame_bytes']);tot[path]+=b
                (ex if limited else eligible)[path]+=b
                if not limited:stop[d['stop_reason']]+=1
            mode=g[0].get('fixed_diagnostic_mode','legacy_partial')
            if mode=='wait' and any(int(d['actual_frame_bytes']) or int(d['actual_packets']) for d in g):
                invariants.append(dict(run_id=r['run_id'],decision_id=did,error='wait sent data'))
            if mode=='bootstrap' and not limited:
                invariants.append(dict(run_id=r['run_id'],decision_id=did,error='bootstrap lacked raw cwnd constraint'))
            paths={int(d['path']):d for d in g};state='no_two_path_send';actual=None;pred=None
            if set(paths)=={0,1}:
                a,b=paths[0],paths[1]
                if all(int(d['rtt_valid']) and int(d['nominal_demand_frame_bytes'])>0 for d in (a,b)):
                    pred=float(b['predicted_requested_end_s'])-float(a['predicted_requested_end_s'])
                if all(int(d['actual_packets'])>0 for d in (a,b)):
                    ts=round(float(g[0]['time_s']),10);cohort=txtime.get(ts,[])
                    if len(bytime[ts])!=1:state='ambiguous_same_time_decisions'
                    elif any(len({p['packet_number'] for p in cohort if int(p['path'])==i})!=int(paths[i]['actual_packets']) for i in (0,1)):
                        state='unmatched_tx_count'
                    elif not all(key(p) in rxkeys for p in cohort):state='original_packet_not_received'
                    else:
                        ends=[max(rxkeys[key(p)] for p in cohort if int(p['path'])==i) for i in (0,1)]
                        actual=ends[1]-ends[0];cumulative_gap+=abs(actual);state='valid'
            count[state]+=1
            observations.append(dict(run_id=r['run_id'],scenario=r['scenario'],share0=r['share0'],seed=r['seed'],
                connection=conn,decision_id=did,time_s=g[0]['time_s'],mode=mode,cwnd_excluded=int(limited),
                actual_frame_p0=sum(int(d['actual_frame_bytes']) for d in g if d['path']=='0'),
                actual_frame_p1=sum(int(d['actual_frame_bytes']) for d in g if d['path']=='1'),
                predicted_signed_gap_s=pred,arrival_state=state,actual_signed_gap_s=actual,
                actual_absolute_gap_s=None if actual is None else abs(actual),cumulative_absolute_gap_samples_s=cumulative_gap))
        seen=defaultdict(list);new=[0,0];retrans=[0,0];payload=[0,0]
        for p in tx:
            i=int(p['path']);n=int(p['payload_bytes']);a=int(p['offset']);s=p['stream']
            seen[s],overlap=interval_add(seen[s],a,a+n)
            payload[i]+=n;retrans[i]+=overlap;new[i]+=n-overlap
            usage.append(dict(run_id=r['run_id'],time_s=p['time_s'],path=i,stream=s,offset=a,payload_bytes=n,
                new_payload_bytes=n-overlap,retransmitted_payload_bytes=overlap,
                cumulative_payload_p0=payload[0],cumulative_payload_p1=payload[1],
                cumulative_new_p0=new[0],cumulative_new_p1=new[1],
                cumulative_retransmitted_p0=retrans[0],cumulative_retransmitted_p1=retrans[1]))
        receiver=[d for d in reorders if d['node']=='5' and int(d['stream'])>0]
        episodes={}
        for d in receiver:
            if int(d['episode_id']):episodes[(d['connection'],d['stream'],d['episode_id'])]=d
        closed=[float(d['episode_elapsed_s']) for d in episodes.values() if d['episode_state']=='end']
        open_episodes=[d for d in episodes.values() if d['episode_state']!='end']
        ro=[o for o in observations if o['run_id']==r['run_id']]
        gaps=[o['actual_absolute_gap_s'] for o in ro if o['arrival_state']=='valid']
        signed=[o['actual_signed_gap_s'] for o in ro if o['arrival_state']=='valid']
        predicted=[abs(o['predicted_signed_gap_s']) for o in ro if o['predicted_signed_gap_s'] is not None and o['arrival_state']=='valid']
        metric=dict(run_id=r['run_id'],case=r['case'],scenario=r['scenario'],seed=r['seed'],share0=r['share0'],
            done=r['done'],exact_full=int(int(r['rx_app'])==int(r['size'])),rx_app=r['rx_app'],fct_s=r['fct_s'],
            decisions=count['decisions'],eligible_decisions=count['eligible'],cwnd_excluded_decisions=count['excluded'],
            actual_frame_p0=tot[0],actual_frame_p1=tot[1],eligible_frame_p0=eligible[0],eligible_frame_p1=eligible[1],
            eligible_byte_fraction=sum(eligible)/sum(tot) if sum(tot) else 0,
            eligible_share0=eligible[0]/sum(eligible) if sum(eligible) else None,
            tx_payload_p0=payload[0],tx_payload_p1=payload[1],new_payload_p0=new[0],new_payload_p1=new[1],
            retrans_payload_p0=retrans[0],retrans_payload_p1=retrans[1],unique_payload_total=sum(new),
            arrival_valid_batches=count['valid'],arrival_censored_batches=count['original_packet_not_received'],
            arrival_ambiguous_batches=count['ambiguous_same_time_decisions'],arrival_unmatched_batches=count['unmatched_tx_count'],
            actual_gap_mean_s=mean(gaps),actual_gap_p95_s=quantile(gaps,.95),actual_signed_gap_mean_s=mean(signed),
            predicted_gap_mean_s=mean(predicted),reorder_waiting_max_bytes=max((int(d['waiting_payload_bytes']) for d in receiver),default=0),
            reorder_closed_episodes=len(closed),reorder_open_episodes=len(open_episodes),
            reorder_closed_duration_p95_s=quantile(closed,.95),reorder_final_waiting_bytes=int(receiver[-1]['waiting_payload_bytes']) if receiver else None,
            eligible_stop_reasons=json.dumps(dict(stop),sort_keys=True))
        if r['case']=='fixed_ratio':
            target=float(r['share0']);v=metric['eligible_share0']
            e0=None if v is None else abs(v-target)/target;e1=None if v is None else abs((1-v)-(1-target))/(1-target)
            metric.update(error_percentage_points=None if v is None else (v-target)*100,
                relative_error_p0=e0,relative_error_p1=e1,allocation_pass=int(v is not None and max(e0,e1)<=.05))
            fixed.append(metric.copy())
        all_metrics.append(metric)
    # Use a common rectangular schema for fixed vs plain observations.
    common=list(dict.fromkeys(k for m in all_metrics for k in m))
    write(out/'run_metrics.csv',[{k:m.get(k) for k in common} for m in all_metrics])
    write(out/'fixed_ratio_summary.csv',fixed);write(out/'decision_metrics.csv',observations);write(out/'path_usage.csv',usage)
    write(out/'invariant_errors.csv',invariants)
    aggregates=[]
    for scenario in ('dominating','competing','degrade'):
        for share in (.1,.3,.5):
            ms=[m for m in fixed if m['scenario']==scenario and float(m['share0'])==share]
            aggregates.append(dict(scenario=scenario,target_share0=share,runs=len(ms),completed=sum(int(m['done']) for m in ms),
                exact_full=sum(int(m['exact_full']) for m in ms),allocation_pass=sum(m['allocation_pass'] for m in ms),
                actual_share0_min=min(m['eligible_share0'] for m in ms),actual_share0_max=max(m['eligible_share0'] for m in ms),
                eligible_byte_fraction_min=min(m['eligible_byte_fraction'] for m in ms),
                mean_actual_batch_gap_s=mean([m['actual_gap_mean_s'] for m in ms if m['actual_gap_mean_s'] is not None]),
                mean_batch_gap_p95_s=mean([m['actual_gap_p95_s'] for m in ms if m['actual_gap_p95_s'] is not None]),
                valid_arrival_batches=sum(m['arrival_valid_batches'] for m in ms),
                censored_arrival_batches=sum(m['arrival_censored_batches'] for m in ms),
                reorder_waiting_max_bytes=max(m['reorder_waiting_max_bytes'] for m in ms)))
    write(out/'condition_summary.csv',aggregates)
    common_state=[]
    for share in (.5,.3,.1):
        b0=round(10*share)*1460;b1=14600-b0;rtt0=.1;rtt1=.15;cwnd0=cwnd1=29200
        t0=rtt0/2+b0*rtt0/cwnd0;t1=rtt1/2+b1*rtt1/cwnd1
        common_state.append(dict(share0=share,share1=1-share,rtt0_s=rtt0,rtt1_s=rtt1,cwnd0=cwnd0,cwnd1=cwnd1,
            requested0=b0,requested1=b1,predicted_gap_s=t1-t0))
    write(out/'arrival_same_state_check.csv',common_state)
    summary=dict(allocation_pass=sum(m['allocation_pass'] for m in fixed),allocation_runs=len(fixed),invariant_errors=invariants,
        actual_arrival_valid_batches=sum(m['arrival_valid_batches'] for m in fixed),
        minimum_eligible_byte_fraction=min(m['eligible_byte_fraction'] for m in fixed),
        comparison='per-run byte-weighted shares; whole decision excluded only for nominal demand > cwnd room',
        arrival='last original application packet receive time on path1 minus path0 within one unique decision timestamp; censored and ambiguous kept',
        cumulative_gap='sum of absolute valid batch gap samples; diagnostic accumulator, no control feedback',
        completed=sum(int(x['done']) for x in results),full=sum(int(x['rx_app'])==int(x['size']) for x in results),runs=len(results))
    (out/'analysis_validation.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2,ensure_ascii=False));print(json.dumps(aggregates,indent=2))
    (out/'analyzer_sha256.txt').write_text(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();analyze(a.run.resolve())
