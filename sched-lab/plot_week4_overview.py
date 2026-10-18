"""Draw the compact week4 completion overview from the frozen group summary."""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();s=pd.read_csv(a.summary)
    conds=['reference','loss01','loss1','queue100','queue1000','buffer1m','buffer8m']
    labels=['Default','Packet loss 0.1%','Packet loss 1%','FqCoDel 100 packets','FqCoDel 1000 packets','QUIC buffers 1 MiB','QUIC buffers 8 MiB']
    scens=['dominating','competing','degrade']
    agg=s[s.condition.isin(conds)].groupby(['condition','scenario'])[['runs','completed','full_received']].sum()
    vals=np.array([[agg.loc[(c,sc),'completed']/agg.loc[(c,sc),'runs'] for sc in scens] for c in conds])
    fig,ax=plt.subplots(figsize=(8.5,4.8));ax.imshow(vals,cmap='Blues',vmin=0,vmax=1,aspect='auto')
    for y,c in enumerate(conds):
        for x,sc in enumerate(scens):
            r=agg.loc[(c,sc)]
            ax.text(x,y,f'Completed {r.completed}/{r.runs}\nExact bytes {r.full_received}/{r.runs}',ha='center',va='center',color='white' if vals[y,x]>.55 else '#142840',fontsize=9)
    ax.set_xticks(range(3));ax.set_xticklabels(scens)
    ax.set_yticks(range(len(conds)));ax.set_yticklabels(labels,fontsize=10)
    ax.set_title('5 MiB: seven schedulers × five seeds per cell\nOLIA; grace=250 ms; one factor changed per row',fontsize=11)
    fig.tight_layout();a.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.output,dpi=160);plt.close(fig)

if __name__=='__main__':main()
