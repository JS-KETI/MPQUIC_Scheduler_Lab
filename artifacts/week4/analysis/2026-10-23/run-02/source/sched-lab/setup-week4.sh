#!/usr/bin/env bash
# Ubuntu 24.04 / WSL2; source archive already includes all accepted patches.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import numpy,pandas,scipy,matplotlib' || {
  printf '%s\n' 'Install: sudo apt-get install build-essential python3 git libeigen3-dev python3-numpy python3-pandas python3-scipy python3-matplotlib'
  exit 1
}
./waf configure --build-profile=optimized --disable-python --disable-werror --enable-tests \
  --enable-modules=quic,point-to-point,applications,internet,flow-monitor
./waf build -j "${JOBS:-4}"
./waf --run 'test-runner --suite=mp-quic-scheduler --verbose'
