#!/usr/bin/env python3
"""Summarise sched-lab results:  python3 sched-lab/analyze.py sched-lab/results.csv"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv = sys.argv[1] if len(sys.argv) > 1 else "sched-lab/results.csv"
out_png = csv.rsplit(".", 1)[0] + "_fct.png"
df = pd.read_csv(csv)
order = ["RR", "MinRTT", "BLEST", "ECF", "Peekaboo", "MinRTT-multi(new)", "EAT(new)"]
order = [o for o in order if o in set(df.name)] + sorted(set(df.name) - set(order))

rows = []
for (sc, name), g in df.groupby(["scenario", "name"]):
    ok = g[g.done == 1]
    rows.append(dict(scenario=sc, scheduler=name, runs=len(g), completed=len(ok),
                     fct_mean=ok.fct_s.mean(), fct_std=ok.fct_s.std(), fct_median=ok.fct_s.median(),
                     fct_p90=ok.fct_s.quantile(0.9), fct95_mean=ok.fct95_s.mean(),
                     share_p1=(ok.rx_p1 / (ok.rx_p0 + ok.rx_p1)).mean()))
summ = pd.DataFrame(rows)
summ["scheduler"] = pd.Categorical(summ.scheduler, order, ordered=True)
summ = summ.sort_values(["scenario", "scheduler"])
pd.set_option("display.width", 160)
print(summ.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
summ.to_csv(csv.rsplit(".", 1)[0] + "_summary.csv", index=False)

scens = list(dict.fromkeys(df.scenario))
fig, axes = plt.subplots(1, len(scens), figsize=(5.2 * len(scens), 4.2), squeeze=False)
for ax, sc in zip(axes[0], scens):
    d = df[(df.scenario == sc) & (df.done == 1)]
    data = [d[d.name == n].fct_s.values for n in order]
    tot = df[df.scenario == sc]
    labels = [f"{n.replace('(new)', '*')}\n{len(d[d.name == n])}/{len(tot[tot.name == n])}" for n in order]
    ax.boxplot(data, labels=labels, showmeans=True)
    ax.set_title(sc)
    ax.set_ylabel("flow completion time [s]")
    ax.tick_params(axis="x", rotation=40)
    ax.grid(axis="y", ls="--", alpha=0.5)
fig.suptitle("MPQUIC ns-3, 5 MB bulk transfer (* = added; n/N = completed/total runs, stalled runs not plotted)")
fig.tight_layout()
fig.savefig(out_png, dpi=130)
print("saved", out_png)
