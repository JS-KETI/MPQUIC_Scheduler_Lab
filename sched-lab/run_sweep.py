#!/usr/bin/env python3
"""
Scheduler sweep for mpquic-sched-lab.

usage (from the ns-3 root, after ./waf build):
    python3 sched-lab/run_sweep.py --seeds 10 --out sched-lab/results.csv
    python3 sched-lab/run_sweep.py --schedulers 1,3,5 --scenarios dominating --seeds 20

Add your own scenario to SCENARIOS and your own scheduler id to NAMES.
"""
import argparse, csv, glob, os, subprocess, sys, time

NAMES = {0: "RR", 1: "MinRTT", 2: "BLEST", 3: "ECF", 4: "Peekaboo", 5: "EAT(new)", 6: "MinRTT-multi(new)"}

# rates in Mbps, delays = one-way ms, [min, max] redrawn every 100 ms (as in the paper)
SCENARIOS = {
    # WNS3'23 Fig.9: one path better in both bandwidth and delay
    "dominating": dict(Rate0a=5, Rate0b=5.5, Delay0a=50, Delay0b=55,
                       Rate1a=10, Rate1b=11, Delay1a=10, Delay1b=11),
    # WNS3'23 Fig.10: bandwidth and delay conflict
    "competing":  dict(Rate0a=5, Rate0b=5.5, Delay0a=10, Delay0b=11,
                       Rate1a=10, Rate1b=11, Delay1a=50, Delay1b=55),
    # dominating, but the fast path collapses 1.5 s after start (UAV link degradation-like)
    "degrade":    dict(Rate0a=5, Rate0b=5.5, Delay0a=50, Delay0b=55,
                       Rate1a=10, Rate1b=11, Delay1a=10, Delay1b=11,
                       EventTime=1.5, Rate1After=1.0, Delay1After=120),
}


def find_binary(root):
    cands = glob.glob(os.path.join(root, "build", "scratch", "*mpquic-sched-lab*"))
    cands = [c for c in cands if os.access(c, os.X_OK) and not c.endswith(".o")]
    if not cands:
        sys.exit("binary not found - run ./waf build first")
    return cands[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--schedulers", default="0,1,2,3,4,5,6")
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--size", type=int, default=5242880)
    ap.add_argument("--extra", default="", help='extra args, e.g. "--EatMargin=0.2 --LossRate=0.001"')
    ap.add_argument("--out", default="sched-lab/results.csv")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    binary = find_binary(root)
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = os.path.join(root, "build", "lib") + ":" + env.get("LD_LIBRARY_PATH", "")

    scheds = [int(s) for s in a.schedulers.split(",")]
    scens = a.scenarios.split(",")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    new = not os.path.exists(a.out)
    with open(a.out, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "scheduler", "name", "seed", "size", "fct_s", "fct95_s", "rx_app",
                        "rx_p0", "rx_p1", "delay_p0_ms", "delay_p1_ms", "done", "wall_s"])
        total = len(scheds) * len(scens) * a.seeds
        k = 0
        for sc in scens:
            for s in scheds:
                for seed in range(1, a.seeds + 1):
                    k += 1
                    args = [binary, f"--SchedulerType={s}", f"--Seed={seed}", f"--Size={a.size}"]
                    args += [f"--{kk}={vv}" for kk, vv in SCENARIOS[sc].items()]
                    args += a.extra.split()
                    t0 = time.time()
                    p = subprocess.run(args, env=env, capture_output=True, text=True, cwd=root)
                    wall = time.time() - t0
                    line = [l for l in p.stdout.splitlines() if l.startswith("RESULT,")]
                    if p.returncode != 0 or not line:
                        print(f"[{k}/{total}] {sc} {NAMES.get(s, s)} seed={seed} FAILED rc={p.returncode}",
                              p.stderr[-300:], file=sys.stderr)
                        continue
                    v = line[-1].split(",")[1:]
                    w.writerow([sc, s, NAMES.get(s, str(s)), seed] + v[2:] + [f"{wall:.1f}"])
                    f.flush()
                    print(f"[{k}/{total}] {sc:10s} {NAMES.get(s, s):17s} seed={seed:2d} "
                          f"FCT={float(v[3]):7.3f}s FCT95={float(v[4]):7.3f}s done={v[10]} "
                          f"p0={int(v[6])/1e6:.2f}MB p1={int(v[7])/1e6:.2f}MB ({wall:.1f}s)")


if __name__ == "__main__":
    main()
