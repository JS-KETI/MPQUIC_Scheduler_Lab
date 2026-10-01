# 1주차 실행 환경

- 날짜: 2026-10-01 / Asia/Seoul
- Windows 11 Home 10.0.26200.9457 / Core Ultra 7 265F / RAM 약 32GB
- WSL 3.0.1.0 / Ubuntu-24.04 / WSL 2 / Ubuntu 24.04.5 LTS
- 기본 계정: ubuntu / WSL에서 확인한 CPU 20개·메모리 약 15GiB
- Linux 커널: 6.18.40.1-microsoft-standard-WSL2
- Git 2.43.0 / Python 3.12.3 / g++ 13.3.0
- Eigen 3.4.0 / pandas 2.1.4 / Matplotlib 3.6.3
- 패키지: build-essential python3 git libeigen3-dev python3-pandas python3-matplotlib
- 커밋: 99df419d0bb49e81b9afa1f4747769ab3f9e53ae
- 브랜치: lab/setup-ubuntu-20261001 / 추가 변경은 미커밋 상태
- 코드: /home/ubuntu/projects/keti/mpquic-sched-lab/mpquic
- 결과: /home/ubuntu/projects/keti/mpquic-sched-lab/mpquic/sched-lab/w1-2026-10-01/
- 01: 스케줄러·실험 추가 / 02: 스택 수정
- 03: Matplotlib 라벨 호환 수정 / 04: 단일 경로 수신 시간 계측
- 다중 경로 210회는 01+02 기준 / 03은 그래프 전용 / 04는 단일 경로 파일만 변경
- 실행 명령: commands.json / 패치 SHA-256: provenance.json
- 다중 경로 1회 처리 시간: 평균 0.336초 / CSV 기록 범위 0.3~0.8초 / 210회 합계 70.6초
- 최초 설치 로그: 이전 outputs/setup-test-2026-10-01/ 기록

## 실행 명령

```bash
cd /home/ubuntu/projects/keti/mpquic-sched-lab/mpquic
python3 -u sched-lab/run_sweep.py --seeds 10 --out sched-lab/w1-2026-10-01/w1.csv
python3 sched-lab/analyze.py sched-lab/w1-2026-10-01/w1.csv
./waf build --targets=wns3-mpquic-one-path
LD_LIBRARY_PATH=$PWD/build/lib ./build/scratch/wns3-mpquic-one-path --SchedulerType=4 --Seed=1 --Size=5242880 --Rate0a=5 --Rate0b=5 --Delay0a=50 --Delay0b=50 --LossRate=0 --CcType=1
```

- 단일 경로 실행은 seed별 별도 폴더에서 수행 / 실제 명령은 각 command.json 참고
- 동일 CSV에 다시 실행하면 중복 추가됨 / 새 날짜·실행 번호 폴더 사용
- 제공 results/ 및 이번 검증 결과는 재실행 시 보존
- 환경·날짜·커밋·패치·명령·생성 시각을 결과와 함께 기록
