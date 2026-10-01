#!/usr/bin/env bash
# MPQUIC ns-3 sched-lab 설치/빌드/빠른 검증 스크립트
#   사용: bash setup.sh              (01 + 02 패치 적용: 권장)
#         bash setup.sh --paper      (01 패치만: 논문 원 스택 동작 유지)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
# 필요 패키지 (Ubuntu 22.04/24.04):
#   sudo apt-get install -y build-essential python3 git libeigen3-dev python3-pandas python3-matplotlib
git clone https://github.com/ssjShirley/mpquic.git mpquic
cd mpquic
git checkout -q 99df419d0bb49e81b9afa1f4747769ab3f9e53ae   # 검증에 사용한 커밋
git apply "$HERE/patches/01-sched-lab.patch"
if [ "$1" != "--paper" ]; then
  git apply "$HERE/patches/02-stack-fixes.patch"
fi
./waf configure --build-profile=optimized --disable-python --disable-werror \
  --enable-modules=quic,point-to-point,applications,internet,flow-monitor
./waf build
python3 sched-lab/run_sweep.py --seeds 3 --out sched-lab/quick.csv
python3 sched-lab/analyze.py sched-lab/quick.csv
