import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
out = root / 'sched-lab/w1-2026-10-01'
v = json.loads((out/'validation.json').read_text())
with (out/'reference_comparison.csv').open(newline='') as f:
    comparison = list(csv.DictReader(f))
with (out/'w1.csv').open(newline='') as f:
    rows = list(csv.DictReader(f))
partial = [r for r in rows if r['done']=='1' and r['rx_app']!=r['size']]
with (out/'completed_below_target.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(partial)
trace1=out/'single-path/seed-1/scheduler4-rx.txt'
trace2=out/'single-path/pristine-crosscheck/scheduler4-rx.txt'
assert trace1.read_bytes()==trace2.read_bytes()
cross=dict(identical=True,sha256=hashlib.sha256(trace1.read_bytes()).hexdigest(),meaning='Original and instrumented single-path binaries produce identical IP receive traces for seed 1.')
(out/'single-path/instrumentation-crosscheck.json').write_text(json.dumps(cross,indent=2)+'\n')
v['partial_completed']=len(partial)
v['instrumentation_crosscheck']=cross
v['csv_completed_at']=datetime.fromtimestamp((out/'w1.csv').stat().st_mtime,ZoneInfo('Asia/Seoul')).isoformat()
(out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

environment='''# 1주차 실행 환경

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
'''
(out/'env.md').write_text(environment)

lines=['# 1주차 결과 보고','',f'- 기록일: 2026-10-01 / CSV 생성 완료: {v["csv_completed_at"]}', '- 판정: 실행·분석·보고 완료 / 게이트 1 미달', '', '## 수행한 작업', '', '- D1: WSL 2·Ubuntu 24.04 환경 구성, 빌드·3-seed 검증 완료', '- D2: 버전·커밋·패치·명령·결과 보관 정보 기록', '- D3–D4: 3시나리오 × 7스케줄러 × 10seed = 210회 실행', '- D5: 기준 데이터 대조·단일 경로 검증·게이트 판정', '', '## 재현 결과', '', '- 210행 / 고유 조합 210개 / 누락·중복·실행 실패 0개', '- 제공된 수정 스택의 210행과 시뮬레이션 지표 동일 / 평균 FCT 편차 0%', '- 완료 기준 충족 191/210 / 목표 바이트 정확 수신 181/210', '- done=1이지만 목표보다 적게 수신한 실행 10개 / done=0 19개', '- 실제 PC 처리 시간 합계 70.6초 / 제공 데이터 154.8초', '', '| 시나리오 | 완료 | 전체 | 완료율 |','|---|---:|---:|---:|','| dominating | 68 | 70 | 97.14% |','| competing | 53 | 70 | 75.71% |','| degrade | 70 | 70 | 100% |','', '## 게이트 1', '', '| 항목 | 기준 | 결과 | 판정 |','|---|---|---|---|','| 7개 스케줄러 | 정상 종료·RESULT | 210회 정상 종료·결과 기록 | 통과 |',f'| dominating / RR | 3.27초 ±5% | {v["gate"]["dominating_rr_mean_s"]:.5f}초 / +0.101% | 통과 |','| 단일 경로 | 8.5~9.0초 | 9.456032406초 | 미달 |','', '## 단일 경로 확인', '', '- 기본 조건: 5Mbps 고정 / 편도 지연 50ms / OLIA / 손실률 0 / SchedulerType=4', '- 전송량 5,242,880B / seed 1·2·3 모두 정확히 전체 수신', '- 앱 시작 1초 이후부터 전체 목표 수신까지 9.456032406초', '- 느슨한 size-3000 완료 기준도 9.452427366초로 범위 초과', '- 9.0초 상한 대비 +0.456032406초 / +5.067%', '- 관찰용 Rx 계측 전·후 IP 수신 추적 파일 동일 / SHA-256 교차 확인', '- 속도 범위 5~5.5Mbps 보조 실험: 9.056787214·9.035944879·9.026155822초', '- 전송량 5,000,000B 보조 실험: 9.038191526초', '', '## 원인 추정·남은 확인', '', '- 요청서에 단일 경로 참고값을 만든 정확한 명령·패치 구성·완료 판정 근거가 없음', '- 코드 기본 조건에서 참고 범위를 재현하지 못함 / 원인 확정 불가', '- 전송량·속도 범위 변경 시 시간이 달라짐 / 두 보조 조건도 범위 초과', '- 제공된 210개 결과 전체 일치: 다중 경로 환경 재현 자체의 차이는 관측되지 않음', '- 단일 경로 참고 실행 명령·원본 측정 근거 확인 후 동일 조건 재검증 필요', '- 게이트 미달 상태에서 2주차 30-seed 데이터 구축은 진행하지 않음', '', '## 결과 해석 시 주의', '', '- 평균·중앙값·p90 FCT는 done=1 실행 기준', '- done=1은 목표-3000B 도달 후 10ms 뒤 시뮬레이션 종료 / 정확 수신 여부는 rx_app 별도 확인', '- FCT95는 완료 실행 평균과 전체 실행 평균을 구분해 reference_comparison.csv에 기록', '- 경로별 rx_p0·rx_p1은 IP 계층 수신 바이트 / 재전송·헤더 포함, 앱 고유 바이트 분배와 다름', '- competing의 tail stall은 제공된 데이터에도 존재 / 이번 주에는 원인·스택 수정 미수행', '', '## 다음 작업에 참고할 파일', '', '- w1.csv / w1_summary.csv / w1_fct.png·svg / w1_plot.html', '- reference_comparison.csv / reference_differences.csv / validation.json', '- stalled_runs.csv / completed_below_target.csv', '- single-path/single_path.csv / diagnostics.csv / 실행별 command.json·로그·IP 수신 추적', '- env.md / commands.json / provenance.json / patches/01~04', '- README_산출물.md / 재현_분석_도구/', '', '## 스케줄러별 결과', '', '| 시나리오 | 스케줄러 | 완료/10 | 평균 FCT[s] | 기준 평균[s] | 편차 |','|---|---|---:|---:|---:|---:|']
reference_lines = [
    '## 요청서 참고값 대조', '',
    '| 항목 | 요청서 참고값 | 측정값 | 차이·확인 |',
    '|---|---|---|---|',
    '| dominating / RR | 3.27초 | 3.27331초 | +0.101% |',
    '| dominating / MinRTT | 4.16초 | 4.16323초 | +0.078% |',
    '| degrade / MinRTT-multi | 6.33초 | 6.32864초 | -0.021% |',
    '| competing / 다중충진 완료율 | 30~60% | RR 60%, MinRTT-multi 40%, EAT 40% | 범위 내 |',
    '| 전송 완료 바이트 | 5,242,880B | 정확 수신 181/210 | 10개는 허용 오차 안에서 종료, 19개는 done=0 |', '',
    '- 위 반올림 참고값과 별도로 제공 CSV의 같은 210개 조합은 9개 시뮬레이션 필드 전부 일치', ''
]
reference_position = lines.index('## 단일 경로 확인')
lines[reference_position:reference_position] = reference_lines
for r in comparison:
    lines.append(f'| {r["scenario"]} | {r["scheduler"]} | {r["completed"]}/10 | {float(r["fct_mean"]):.5f} | {float(r["reference_fct_mean"]):.5f} | {float(r["fct_diff_pct"]):.2f}% |')
(out/'1주차_보고서.md').write_text('\n'.join(lines)+'\n')
(out/'README_산출물.md').write_text('''# 1주차 산출물 안내

- 먼저 읽기: 1주차_보고서.md
- 환경·명령: env.md, commands.json
- 코드·패치 식별: provenance.json, patches/
- 원시 실험 결과: w1.csv (210행)
- 제공 데이터 비교: reference_comparison.csv (21개 그룹), reference_differences.csv (헤더만 존재: 차이 0개)
- 완료 기준별 구분: stalled_runs.csv (19행), completed_below_target.csv (10행)
- 그림: w1_fct.png, w1_fct.svg, w1_plot.html
- 실행·분석 로그: sweep.log, analysis.log
- 검증·게이트 판정: validation.json
- 단일 경로: single-path/ (기본 3회, 보조 4회, 계측 전 교차 확인 1회)
- 계측 원본 보존: patches/04-week1-one-path-measurement.patch
- 재현·분석 도구: 재현_분석_도구/ (실행 경로는 이 PC의 Linux 프로젝트 경로를 사용)
- Windows 본 파일은 Linux 결과의 인계 사본 / 실제 코드 위치는 env.md 참고
- 날짜별 보관 / 재실행 시 새 파일명·폴더 사용 / 이번 결과 원본 덮어쓰기 금지
''')
print(json.dumps({'matched':v['matched_reference_rows'],'gate':v['gate'],'partial_completed':len(partial),'csv_completed_at':v['csv_completed_at']},ensure_ascii=False))
