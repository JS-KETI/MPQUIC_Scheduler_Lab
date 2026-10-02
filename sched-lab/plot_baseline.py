#!/usr/bin/env python3
"""Generate the three week-2 scientific figures directly from a validated CSV."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from stats import SCENARIOS, ORDER, NAMES, load_sweep, summarize


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--seeds', default=30, type=int)
    a = ap.parse_args()
    df = load_sweep(a.csv, a.seeds)
    summary = summarize(df)
    a.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size':10, 'svg.fonttype':'none', 'axes.spines.top':False,
                         'axes.spines.right':False, 'figure.facecolor':'white'})
    labels = [NAMES[s].replace('(new)','\n(new)').replace('MinRTT-multi','MinRTT-\nmulti') for s in ORDER]

    def save(fig, name):
        for ext in ['png','svg']:
            fig.savefig(a.out/f'{name}.{ext}',dpi=170,bbox_inches='tight')
        plt.close(fig)

    fig, axes = plt.subplots(1,3,figsize=(15,5))
    for ax, sc in zip(axes, SCENARIOS):
        groups = [df[(df.scenario==sc)&(df.scheduler==s)] for s in ORDER]
        values = [g.loc[g.done.eq(1),'fct_s'].to_numpy() for g in groups]
        ax.boxplot(values, showmeans=True, patch_artist=True,
                   boxprops={'facecolor':'#dbe7f2'}, medianprops={'color':'#c56925'},
                   meanprops={'marker':'^','markerfacecolor':'#267653','markeredgecolor':'#267653'})
        ax.set_xticks(range(1,8),[f'{label}\n{int(g.done.sum())}/{len(g)}' for label,g in zip(labels,groups)],fontsize=8)
        ax.set_title(sc)
        ax.set_ylabel('Completion time (s)')
        ax.grid(axis='y',alpha=.25)
    fig.suptitle('5 MiB transfer time by scheduler | seed 1-30', fontsize=15)
    fig.text(.5,.015,'Completed runs only; labels = completed / attempted. Triangle = mean. Box = middle 50%.',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.07,1,.95])
    save(fig,'fct_distributions')

    fig,axes=plt.subplots(1,3,figsize=(15,5))
    for ax,sc in zip(axes,SCENARIOS):
        g=summary[summary.scenario.eq(sc)].set_index('scheduler').loc[ORDER]
        full=g.full_received.to_numpy(); short=g.completed_short.to_numpy(); pending=g.incomplete.to_numpy()
        x=np.arange(7)
        ax.bar(x,full,color='#2d755a',label='Full target received')
        ax.bar(x,short,bottom=full,color='#e5b653',label='Completed, below target')
        ax.bar(x,pending,bottom=full+short,color='#d8dde4',label='Incomplete')
        for i,row in enumerate(g.itertuples()):
            ax.text(i,a.seeds+.6,f'{row.completed}/{row.runs}',ha='center',fontsize=9)
        ax.set_ylim(0,a.seeds+4);ax.set_yticks([0,10,20,30]); ax.set_title(sc)
        ax.set_xticks(x,labels,fontsize=8);ax.set_ylabel('Runs');ax.grid(axis='y',alpha=.2)
    handles,legend=axes[0].get_legend_handles_labels()
    fig.legend(handles,legend,loc='lower center',ncol=3,frameon=False)
    fig.suptitle('Completed runs and exact target reception | target = 5,242,880 bytes',fontsize=15)
    fig.tight_layout(rect=[0,.09,1,.95]);save(fig,'completion_rates')

    fig,axes=plt.subplots(1,3,figsize=(15,5))
    for ax,sc in zip(axes,SCENARIOS):
        g=summary[summary.scenario.eq(sc)].set_index('scheduler').loc[ORDER]
        p1=g.mean_path1_ip_share.to_numpy()*100;x=np.arange(7)
        ax.bar(x,100-p1,color='#517da0',label='Path 0')
        ax.bar(x,p1,bottom=100-p1,color='#8ebcad',label='Path 1')
        for i,share in enumerate(p1):
            ax.text(i,102,f'{share:.1f}%',ha='center',fontsize=8)
        ax.set_ylim(0,112);ax.set_yticks([0,25,50,75,100]);ax.set_ylabel('Received IP byte share (%)')
        ax.set_title(sc)
        ax.set_xticks(x,[f'{label}\n{row.completed}/{row.runs}' for label,row in zip(labels,g.itertuples())],fontsize=8)
    handles,legend=axes[0].get_legend_handles_labels()
    fig.legend(handles,legend,loc='lower center',ncol=2,frameon=False)
    fig.suptitle('Mean per-run path share | completed runs only',fontsize=15)
    fig.text(.5,.075,'Path 1 share = rx_p1 / (rx_p0 + rx_p1). FlowMonitor IP bytes; includes protocol overhead.',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.13,1,.95]);save(fig,'path_shares')
    print('Created 3 figures in PNG and SVG:',a.out)


if __name__=='__main__':
    main()
