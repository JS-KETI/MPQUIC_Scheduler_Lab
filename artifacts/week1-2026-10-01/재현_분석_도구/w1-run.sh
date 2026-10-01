#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/projects/keti/mpquic-sched-lab/mpquic
out=sched-lab/w1-2026-10-01
test ! -e "$out/w1.csv"
mkdir -p "$out"
python3 -u sched-lab/run_sweep.py --seeds 10 --out "$out/w1.csv" 2>&1 | tee "$out/sweep.log"
python3 sched-lab/analyze.py "$out/w1.csv" 2>&1 | tee "$out/analysis.log"
