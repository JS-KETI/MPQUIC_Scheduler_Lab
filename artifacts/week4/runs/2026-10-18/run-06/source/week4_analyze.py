#!/usr/bin/env python3
"""Week 4 statistics: retained failures, condition-aware pairs, explicit denominators."""
import argparse, itertools, json, subprocess, sys, hashlib, shutil
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from stats import mean_ci, signed_rank_exact, holm, ORDER, NAMES, METRICS

ROOT=Path(__file__).resolve().parents[1]
BASELINE=ROOT/'artifacts/week2-completion-2026-10-08/run-01/baseline.csv'
KEY=['condition','scenario','scheduler','seed']
CONDITION_LABELS={'reference':'Default','early':'Event 0.75 s','late':'Event 3 s','rate_mild':'After 3 Mbps',
 'rate_severe':'After 0.5 Mbps','delay_mild':'After 80 ms','delay_severe':'After 180 ms',
 'loss01':'Packet loss 0.1%','loss1':'Packet loss 1%','queue100':'FqCoDel 100 packets','queue1000':'FqCoDel 1000 packets',
 'buffer1m':'QUIC buffers 1 MiB','buffer8m':'QUIC buffers 8 MiB','long':'50 MiB / 80 MB buffers','four_path':'4-path probe'}

def read_run(folder):
    df=pd.read_csv(folder/'results.csv')
    plan=json.loads((folder/'plan.json').read_text())
    expected={(x['condition'],x['scenario'],x['scheduler'],x['seed']) for x in plan}
    actual=set(df[KEY].itertuples(index=False,name=None))
    if actual!=expected or df[KEY].duplicated().any() or len(df)!=len(plan):
        raise ValueError(f'Plan/rows mismatch: {folder}')
    ok=df.status.eq('ok')
    if not np.isfinite(df.loc[ok,METRICS].to_numpy(dtype=float)).all(): raise ValueError('Invalid numeric result')
    if not df.loc[ok,'done'].eq(df.loc[ok,'rx_app'].ge(df.loc[ok,'size']-3000).astype(int)).all():
        raise ValueError('Done threshold mismatch')
    if (df.loc[ok,'rx_app']>df.loc[ok,'size']).any(): raise ValueError('Excess application bytes')
    if not df.loc[ok & df.done.eq(0),'fct_s'].eq(df.loc[ok & df.done.eq(0),'sim_end']).all():
        raise ValueError('Bad timeout sentinel')
    plan_by_id={x['run_id']:x for x in plan}
    if df.run_id.duplicated().any() or set(df.run_id)!=set(plan_by_id):raise ValueError('Run identifiers mismatch')
    numeric={'size':'Size','sim_end':'SimEnd','loss_rate':'LossRate','queue_packets':'QueueMaxPackets','buffer_bytes':'BufferBytes','path_count':'PathCount'}
    for row in df.itertuples():
        item=plan_by_id[row.run_id]
        if row.name!=item['name'] or any(getattr(row,k)!=item[k] for k in KEY):raise ValueError('Identity mismatch')
        for col,arg in numeric.items():
            if float(getattr(row,col))!=float(item['args'][arg]):raise ValueError(f'Setting mismatch: {col}')
        if row.loss_unit!=item['args']['LossUnit']:raise ValueError('Loss unit mismatch')
        log=(folder/'runs'/row.run_id/'stdout.log').read_text()
        if row.status=='ok' and item['args'].get('BenchMetrics'):
            cfg=[x for x in log.splitlines() if x.startswith('CONFIG4,')]
            if len(cfg)!=1 or not any(x.startswith('METRICS4,') for x in log.splitlines()):raise ValueError('Missing required counters')
            values=dict(x.split('=',1) for x in cfg[0].split(',')[1:])
            for key in ['BufferBytes','QueueMaxPackets','LossRate','PathCount','CompletionGraceMs','SimEnd']:
                if float(values[key])!=float(item['args'][key]):raise ValueError(f'CONFIG4 mismatch: {key}')
            if values['LossUnit']!=item['args']['LossUnit']:raise ValueError('CONFIG4 loss unit mismatch')
            required=['full_fct_s','queue_drops','error_drops','active_subflows']+[f'{d}_payload_p{i}' for i in range(4) for d in ['tx','rx']]
            if not all(np.isfinite(getattr(row,k)) for k in required):raise ValueError('Nonfinite required counters')
            if row.rx_app==row.size and row.full_fct_s<0:raise ValueError('Missing exact receipt time')
    df['source_run']=folder.name
    events={x['run_id']:x['args'].get('EventTime',-1) for x in plan}
    df['event_requested_s']=df.run_id.map(events)
    effective={}
    for run_id in df.run_id:
        lines=(folder/'runs'/run_id/'stdout.log').read_text().splitlines()
        es=[float(x.split(',')[2]) for x in lines if x.startswith('EVENT4,')]
        effective[run_id]=es[0] if es else np.nan
    df['event_planned_grid_s']=df.run_id.map(effective)
    df['event_before_completion']=df.event_planned_grid_s.notna() & ((df.done.eq(0)) | (df.fct_s>=df.event_planned_grid_s))
    return df

def summarize(df):
    rows=[]
    for (cond,sc,sid),g in df.groupby(['condition','scenario','scheduler'],sort=False):
        ok=g[g.status.eq('ok')];done=ok[ok.done.eq(1)];full=ok[ok.rx_app.eq(ok['size'])]
        reached=ok[ok.rx_app.ge(np.floor(ok['size']*.95))]
        mean,lo,hi,width=mean_ci(done.fct_s)
        rows.append(dict(condition=cond,condition_label=CONDITION_LABELS[cond],scenario=sc,scheduler=sid,name=g.name.iloc[0],
                         runs=len(g),process_ok=len(ok),process_failed=len(g)-len(ok),completed=len(done),full_received=len(full),
                         incomplete=int(ok.done.eq(0).sum()),completed_short=int((done.rx_app<done['size']).sum()),
                         completion_rate=len(done)/len(g),full_rate=len(full)/len(g),mean_s=mean,median_s=done.fct_s.median(),
                         p90_s=done.fct_s.quantile(.9),ci95_low_s=lo,ci95_high_s=hi,ci95_width_s=width,
                         fct95_reached=len(reached),mean_fct95_s=reached.fct95_s.mean(),mean_exact_full_s=full.full_fct_s.mean(),
                         mean_path1_ip_share=(done.rx_p1/(done.rx_p0+done.rx_p1)).mean(),
                         mean_received_fraction=(ok.rx_app/ok['size']).mean(),mean_queue_drops=ok.queue_drops.mean(),
                         mean_error_drops=ok.error_drops.mean(),size=int(g['size'].iloc[0]),sim_end=int(g.sim_end.iloc[0]),
                         buffer_bytes=int(g.buffer_bytes.iloc[0]),event_before_completion=int(g.event_before_completion.sum())))
    return pd.DataFrame(rows)

def pairs(df):
    rows=[]
    for (cond,sc),g in df.groupby(['condition','scenario'],sort=False):
        for a,b in itertools.combinations([s for s in ORDER if s in set(g.scheduler)],2):
            ga=g[g.scheduler.eq(a)].set_index('seed');gb=g[g.scheduler.eq(b)].set_index('seed')
            common=ga.index.intersection(gb.index)
            good=common[(ga.loc[common,'status'].eq('ok') & gb.loc[common,'status'].eq('ok') & ga.loc[common,'done'].eq(1) & gb.loc[common,'done'].eq(1)).to_numpy()]
            d=(ga.loc[good,'fct_s']-gb.loc[good,'fct_s']).round(4)
            mean,lo,hi,width=mean_ci(d);stat,p,n=signed_rank_exact(d)
            rows.append(dict(condition=cond,scenario=sc,scheduler_a=a,name_a=NAMES[a],scheduler_b=b,name_b=NAMES[b],
                             runs_a=len(ga),runs_b=len(gb),completed_a=int((ga.status.eq('ok')&ga.done.eq(1)).sum()),completed_b=int((gb.status.eq('ok')&gb.done.eq(1)).sum()),
                             paired_completed=len(good),paired_seeds=','.join(map(str,good)),mean_diff_a_minus_b_s=mean,
                             ci95_low_s=lo,ci95_high_s=hi,ci95_width_s=width,wilcoxon_statistic=stat,wilcoxon_p=p,
                             nonzero_pairs=n,a_faster=int((d<0).sum()),b_faster=int((d>0).sum()),ties=int((d==0).sum())))
    result=pd.DataFrame(rows)
    result['wilcoxon_p_holm_condition_scenario']=result.groupby(['condition','scenario']).wilcoxon_p.transform(holm)
    return result

def rank_changes(df):
    rows=[]
    for cond in df.condition.unique():
        if cond in ['reference','long','four_path']:continue
        for sc in df[df.condition.eq(cond)].scenario.unique():
            for a,b in itertools.combinations(ORDER,2):
                gs=[df[df.condition.eq(c)&df.scenario.eq(sc)&df.scheduler.eq(s)].set_index('seed')
                    for c,s in [('reference',a),('reference',b),(cond,a),(cond,b)]]
                common=set(gs[0].index)
                for g in gs:common &= set(g[g.status.eq('ok')&g.done.eq(1)].index)
                seeds=sorted(common)
                before_ticks=np.rint((gs[0].loc[seeds,'fct_s']-gs[1].loc[seeds,'fct_s'])*10000).astype(int)
                after_ticks=np.rint((gs[2].loc[seeds,'fct_s']-gs[3].loc[seeds,'fct_s'])*10000).astype(int)
                before=before_ticks.mean()/10000 if seeds else np.nan
                after=after_ticks.mean()/10000 if seeds else np.nan
                reversal=bool(before_ticks.sum()*after_ticks.sum()<0) if seeds else None
                rows.append(dict(condition=cond,scenario=sc,scheduler_a=a,name_a=NAMES[a],scheduler_b=b,name_b=NAMES[b],
                                 includes_primary_reference=6 in (a,b),common_completed_seeds=','.join(map(str,seeds)),n=len(seeds),
                                 before_diff_s=before,after_diff_s=after,observed_sign_reversal=reversal,
                                 comparison_status='observed' if seeds else 'no_common_completed_seeds',
                                 interpretation='exploratory same-seed observed mean; not significance claim'))
    return pd.DataFrame(rows)


def plots(df,summ,out):
    out.mkdir()
    for name,field,title in [('long_completion','completion_rate','50 MiB transfer: completion / exact receipt'),
                             ('long_path_share','mean_path1_ip_share','50 MiB transfer: path 1 fraction of received IP bytes')]:
        fig,axes=plt.subplots(1,3,figsize=(14,3.8))
        for ax,sc in zip(axes,['dominating','competing','degrade']):
            g=summ[summ.condition.eq('long')&summ.scenario.eq(sc)].set_index('scheduler').reindex(ORDER)
            x=np.arange(7)
            if field=='completion_rate':
                ax.bar(x-.18,g[field],.36,label='Completed');ax.bar(x+.18,g.full_rate,.36,label='Exact receipt')
                for i,row in enumerate(g.itertuples()):ax.text(i,.04,f'{row.completed}/{row.runs}\n{row.full_received}/{row.runs}',ha='center',fontsize=8)
            else:
                ax.bar(x,g[field]);
                for i,row in enumerate(g.itertuples()):ax.text(i,.04,f'{row.completed}/{row.runs}',ha='center',fontsize=8)
            ax.set_title(sc);ax.set_ylim(0,1.05);ax.set_xticks(x);ax.set_xticklabels([NAMES[s].replace('(new)','*') for s in ORDER],rotation=40,ha='right',fontsize=8)
            ax.grid(axis='y',alpha=.2)
        if field=='completion_rate':axes[0].legend(fontsize=8)
        fig.suptitle(title+(' (mean of completed-run shares)' if field!='completion_rate' else '')+'\nOLIA; loss=0; QUIC buffers=80 MB; grace=250 ms; seeds=1–10',fontsize=10)
        fig.tight_layout();fig.savefig(out/f'{name}.png',dpi=150);plt.close(fig)
    for name,conditions in [('degradation',['reference','early','late','rate_mild','rate_severe','delay_mild','delay_severe']),
                             ('robustness',['reference','loss01','loss1','queue100','queue1000','buffer1m','buffer8m'])]:
        scens=['degrade'] if name=='degradation' else ['dominating','competing','degrade']
        fig,axes=plt.subplots(1,len(scens),figsize=(8 if len(scens)==1 else 16,5),squeeze=False)
        color_max=summ[summ.scenario.isin(scens)&summ.condition.isin(conditions)].mean_s.max()
        for ax,sc in zip(axes[0],scens):
            g=summ[summ.scenario.eq(sc)&summ.condition.isin(conditions)]
            vals=g.pivot(index='condition',columns='scheduler',values='mean_s').reindex(index=conditions,columns=ORDER)
            im=ax.imshow(vals.to_numpy(),cmap='YlGnBu',aspect='auto',vmin=0,vmax=color_max)
            for y,c in enumerate(conditions):
                for x,s in enumerate(ORDER):
                    row=g[g.condition.eq(c)&g.scheduler.eq(s)].iloc[0]
                    val='—' if pd.isna(row.mean_s) else f'{row.mean_s:.2f}s'
                    text=f'{val}\n{row.completed}/{row.runs} · {row.full_received}/{row.runs}'
                    ax.text(x,y,text,ha='center',va='center',fontsize=7,color='white' if pd.notna(row.mean_s) and row.mean_s>color_max*.6 else '#17243b')
            ax.set_title(sc);ax.set_yticks(range(len(conditions)));ax.set_yticklabels([CONDITION_LABELS[c] for c in conditions],fontsize=8)
            ax.set_xticks(range(7));ax.set_xticklabels([NAMES[s].replace('(new)','*') for s in ORDER],rotation=40,ha='right',fontsize=8)
        fig.suptitle('5 MiB: mean completion time; completed/N · exact receipt/N\nOLIA; grace=250 ms; seeds=1–5; one factor per row; shared color scale 0–'+f'{color_max:.1f} s',fontsize=10)
        fig.tight_layout();fig.savefig(out/f'{name}.png',dpi=160);plt.close(fig)
    g=df[df.condition.eq('four_path')].sort_values('scheduler')
    fig,ax=plt.subplots(figsize=(10,3.8));bottom=np.zeros(len(g))
    total=g[[f'tx_payload_p{i}' for i in range(4)]].sum(axis=1).to_numpy()
    for i in range(4):
        v=np.divide(g[f'tx_payload_p{i}'].to_numpy(),total,out=np.zeros(len(g)),where=np.isfinite(total)&(total>0))
        ax.bar(np.arange(len(g)),v,bottom=bottom,label=f'path {i}');bottom+=v
    ax.set_xticks(range(len(g)));ax.set_xticklabels([r.name.replace('(new)','*')+f'\ndone {int(r.done) if pd.notna(r.done) else 0}/1 · full {int(r.rx_app==r.size)}/1\nactive {int(r.active_subflows) if pd.notna(r.active_subflows) else 0}' for r in g.itertuples()],rotation=25,ha='right',fontsize=8)
    for j,r in enumerate(g.itertuples()):
        if r.status!='ok' or not np.isfinite(total[j]) or total[j]<=0:ax.text(j,.3,'NO VALID TX',ha='center',rotation=90,color='red')
    ax.set_ylim(0,1.1);ax.legend(ncol=4,fontsize=9);ax.set_ylabel('Fraction of transmitted STREAM payload\n(retransmissions included)')
    ax.set_title('4-path operation probe — seed 1, 5 MiB, OLIA, loss=0\nAdditional paths: 8 Mbps, 20 ms each; no algorithm changes',fontsize=10)
    fig.tight_layout();fig.savefig(out/'four_path.png',dpi=150);plt.close(fig)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--runs',nargs='+',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source_dir=a.out/'source';source_dir.mkdir()
    hashes={}
    for name in ['week4_analyze.py','stats.py','analyze.py']:
        f=ROOT/'sched-lab'/name;shutil.copy2(f,source_dir/name)
        hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    meta=dict(generated_utc=datetime.now(timezone.utc).isoformat(),command=sys.argv,source_sha256=hashes,
              input_csv_sha256={str(p):hashlib.sha256((p/'results.csv').read_bytes()).hexdigest() for p in a.runs},
              baseline_sha256=hashlib.sha256(BASELINE.read_bytes()).hexdigest(),pandas=pd.__version__,numpy=np.__version__)
    (a.out/'analysis_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    df=pd.concat([read_run(p) for p in a.runs],ignore_index=True)
    if df[KEY].duplicated().any():raise ValueError('Duplicate cross-run keys')
    df.to_csv(a.out/'results.csv',index=False)
    summ=summarize(df);summ.to_csv(a.out/'summary.csv',index=False)
    pairs(df[df.condition.ne('four_path')]).to_csv(a.out/'paired_comparisons.csv',index=False)
    rank_changes(df).to_csv(a.out/'observed_rank_changes.csv',index=False)
    baseline=pd.read_csv(BASELINE);reference=df[df.condition.eq('reference')]
    merged=reference.merge(baseline,on=['scenario','scheduler','seed'],suffixes=('_current','_baseline'),validate='one_to_one')
    if len(merged)!=len(reference):raise ValueError('Unmatched reference keys')
    matches=np.ones(len(merged),dtype=bool)
    for col in METRICS: matches &= merged[f'{col}_current'].eq(merged[f'{col}_baseline']).to_numpy()
    merged['all_result_fields_equal']=matches;merged.to_csv(a.out/'baseline_comparison.csv',index=False)
    df[df.condition.eq('long')].to_csv(a.out/'baseline-long.csv',index=False)
    summ[summ.condition.eq('long')].to_csv(a.out/'summary-long.csv',index=False)
    df[df.condition.eq('four_path')].to_csv(a.out/'four_path.csv',index=False)
    plots(df,summ,a.out/'figures')
    # Use the supplied boxplot tool, retaining its completed/total labels.
    subprocess.run([sys.executable,str(ROOT/'sched-lab/analyze.py'),str(a.out/'baseline-long.csv')],check=True,stdout=(a.out/'provided-plot.log').open('w'))
    validation=dict(rows=len(df),process_ok=int(df.status.eq('ok').sum()),completed=int((df.status.eq('ok')&df.done.eq(1)).sum()),
                    exact_received=int((df.status.eq('ok')&df.rx_app.eq(df['size'])).sum()),reference_compared=len(merged),reference_equal=int(matches.sum()),
                    long_min_completed_fct_s=float(df[df.condition.eq('long')&df.done.eq(1)].fct_s.min()),
                    definitions={'fct':'size-3000B threshold, completed only','fct95':'95% target bytes, all reached runs',
                                 'path_share':'received IP byte share, completed runs; includes IP/UDP/QUIC headers',
                                 'four_path_share':'transmitted STREAM payload sum including retransmission',
                                 'missing_reference':'all new conditions have no supplied reference'},
                    incomplete=df[df.status.eq('ok')&df.done.eq(0)][KEY+['rx_app','size','sim_end']].to_dict('records'),
                    process_failures=df[df.status.ne('ok')][KEY+['status']].to_dict('records'))
    (a.out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k not in ['incomplete','process_failures','definitions']},indent=2))

if __name__=='__main__':main()
