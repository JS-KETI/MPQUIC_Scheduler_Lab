"""Compare one integrated week4 run against the preserved original 1163 trials."""
from pathlib import Path
import argparse,json,csv,hashlib,subprocess
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from week4_analyze import KEY,read_run,CONDITION_LABELS
from stats import mean_ci,signed_rank_exact,holm
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plot_comparison(s,output,language='en'):
 if language=='ko':
  from report_plot_korean import configure_font,localize
  configure_font()
 fig,ax=plt.subplots(figsize=(12,9) if language=='ko' else (10,6));y=np.arange(len(s));
 ax.barh(y-.18,s.completed_before,.36,label='Before: completed');ax.barh(y+.18,s.completed_after,.36,label='Integrated: completed')
 for i,r in enumerate(s.itertuples()):ax.text(max(r.completed_before,r.completed_after)+1,i,f'{r.completed_before}/{r.runs} -> {r.completed_after}/{r.runs}',va='center',fontsize=8)
 ax.set_yticks(y);ax.set_yticklabels([CONDITION_LABELS[x] for x in s.condition],fontsize=8);ax.invert_yaxis();ax.set_xlim(0,max(s.runs)*1.35);ax.set_xlabel('Completed executions');ax.legend();ax.set_title('Week 4: original settings replayed on one integrated QUIC version\nSame seeds, buffers, loss, queue and simulation end time')
 if language=='ko':localize(fig,'comparison')
 fig.tight_layout();fig.savefig(output,dpi=160);plt.close(fig)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--analysis',type=Path,required=True);a=ap.parse_args()
 out=a.analysis;assert out.is_dir() and not (out/'before_after_run.csv').exists()
 now=read_run(a.run);old=pd.read_csv(ROOT/'artifacts/week4/analysis/2026-10-18/run-01/results.csv')
 assert len(now)==len(old)==1163 and not now[KEY].duplicated().any()
 plan=json.loads((a.run/'plan.json').read_text())
 for item in plan:
  original=json.loads((ROOT/item['source_command']).read_text())
  assert item['args']==original['args'],item['run_id']
 m=old.merge(now,on=KEY,suffixes=('_before','_after'),validate='one_to_one');assert len(m)==1163
 m['completed_before']=m.status_before.eq('ok')&m.done_before.eq(1)
 m['completed_after']=m.status_after.eq('ok')&m.done_after.eq(1)
 m['full_before']=m.status_before.eq('ok')&m.rx_app_before.eq(m['size_before'])
 m['full_after']=m.status_after.eq('ok')&m.rx_app_after.eq(m['size_after'])
 m['process_error_after']=m.status_after.ne('ok')
 m['normal_incomplete_after']=m.status_after.eq('ok')&m.done_after.eq(0)
 m['rx_delta_bytes']=m.rx_app_after-m.rx_app_before
 m['completion_transition']=np.select([m.process_error_after,m.completed_before&m.completed_after,m.completed_before&m.normal_incomplete_after,~m.completed_before&m.completed_after],['process_error','retained_complete','new_incomplete','new_complete'],default='still_incomplete')
 classification=pd.read_csv(ROOT/'artifacts/week4/analysis/2026-10-18/diagnosis-01/classification.csv')[['run_id','group']].rename(columns={'run_id':'run_id_before','group':'original_cause_group'})
 m=m.merge(classification,on='run_id_before',how='left',validate='one_to_one')
 m['original_cause_group']=m.original_cause_group.fillna('previously_complete')
 m.to_csv(out/'before_after_run.csv',index=False)
 rows=[]
 for cond,g in m.groupby('condition',sort=False):
  rows.append(dict(condition=cond,runs=len(g),completed_before=int(g.completed_before.sum()),completed_after=int(g.completed_after.sum()),full_before=int(g.full_before.sum()),full_after=int(g.full_after.sum()),new_complete=int((~g.completed_before&g.completed_after).sum()),new_incomplete=int((g.completed_before&g.normal_incomplete_after).sum()),completion_regressions=int((g.completed_before&~g.completed_after).sum()),process_error_after=int(g.process_error_after.sum()),normal_incomplete_after=int(g.normal_incomplete_after.sum()),completed_short_after=int((g.completed_after&~g.full_after).sum())))
 pd.DataFrame(rows).to_csv(out/'before_after_condition.csv',index=False)
 groups=[]
 for group,g in m.groupby('original_cause_group',sort=False):
  groups.append(dict(original_group=group,runs=len(g),completed_after=int(g.completed_after.sum()),full_after=int(g.full_after.sum()),incomplete_after=int(g.normal_incomplete_after.sum()),process_error_after=int(g.process_error_after.sum()),rx_increased=int(g.rx_delta_bytes.gt(0).sum()),rx_decreased=int(g.rx_delta_bytes.lt(0).sum()),rx_equal=int(g.rx_delta_bytes.eq(0).sum())))
 pd.DataFrame(groups).to_csv(out/'before_after_original_group.csv',index=False)
 common=m[m.completed_before&m.completed_after]
 times=[]
 for keys,g in m.groupby(['condition','scenario','scheduler'],sort=False):
  c=g[g.completed_before&g.completed_after];delta=(c.fct_s_after-c.fct_s_before).round(4);mean,lo,hi,width=mean_ci(delta);stat,p,n=signed_rank_exact(delta)
  times.append(dict(condition=keys[0],scenario=keys[1],scheduler=keys[2],runs=len(g),completed_before=int(g.completed_before.sum()),completed_after=int(g.completed_after.sum()),common_completed=len(c),paired_seeds=','.join(map(str,c.seed)),mean_before_s=c.fct_s_before.mean(),mean_after_s=c.fct_s_after.mean(),mean_delta_s=mean,ci95_low_s=lo,ci95_high_s=hi,wilcoxon_statistic=stat,wilcoxon_p=p,nonzero_pairs=n,faster=int(delta.lt(0).sum()),slower=int(delta.gt(0).sum()),ties=int(delta.eq(0).sum())))
 time_table=pd.DataFrame(times);time_table['wilcoxon_p_holm_all_groups']=holm(time_table.wilcoxon_p)
 time_table.to_csv(out/'before_after_common_fct.csv',index=False)
 plot_comparison(pd.DataFrame(rows),out/'figures/final_validation.png')
 preserved=0
 for line in (ROOT/'artifacts/week4/SHA256SUMS').read_text().splitlines():
  h,rel=line.split('  ',1);assert sha(ROOT/'artifacts/week4'/rel)==h,rel;preserved+=1
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only','1fe68f1','--','artifacts/week2-completion-2026-10-08/run-01/','artifacts/BASELINE.json'],cwd=ROOT,text=True).splitlines()
 for rel in paths:assert (ROOT/rel).read_bytes()==subprocess.check_output(['git','show',f'1fe68f1:{rel}'],cwd=ROOT),rel
 record=dict(rows=len(m),identical_original_command_arguments=len(plan),process_ok=int(now.status.eq('ok').sum()),process_error_after=int(m.process_error_after.sum()),completed_before=int(m.completed_before.sum()),completed_after=int(m.completed_after.sum()),full_before=int(m.full_before.sum()),full_after=int(m.full_after.sum()),new_complete=int((~m.completed_before&m.completed_after).sum()),new_incomplete=int((m.completed_before&m.normal_incomplete_after).sum()),completion_regressions=int((m.completed_before&~m.completed_after).sum()),still_incomplete=int((~m.completed_before&m.normal_incomplete_after).sum()),completed_short=int((m.completed_after&~m.full_after).sum()),previously_full_lost=int((m.full_before&~m.full_after).sum()),frozen_week4_files_preserved=preserved,approved_baseline_files_preserved=len(paths),new_incomplete_ids=m.loc[m.completed_before&~m.completed_after,'run_id_after'].tolist())
 (out/'final_validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(record,ensure_ascii=False,indent=2));print(pd.DataFrame(rows).to_string(index=False));print(pd.DataFrame(groups).to_string(index=False))
if __name__=='__main__':main()
