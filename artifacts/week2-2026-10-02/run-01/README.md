# 2주차 630회 측정 기록 — run-01

- 측정 상태: 630회 정상 실행·결과 출력. 완료 처리 568회, 정확한 목표량 수신 533회
- 판정 상태: 게이트 2 보류. dominating의 7개 중 3개 신뢰구간 폭이 0.1초 초과하며, 요청서의 적용 스케줄러 확인 필요
- 측정 소스 커밋: `598f162e74e0e25bbbf702f2db3151223fefc9b2`
- 통계·그림 도구 커밋: `ba3315794d2987c08e82a257fe79a25e51b9c513`
- 데이터·분석 결과는 이 폴더에 동결. 추가 실험은 새 run 폴더에 저장하며 기존 CSV에 이어 붙이지 않음
- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/reports/week2
- 노션 기록 : https://app.notion.com/p/3ed5698e257e819ea1a7f85d9a1a12c0

## 파일과 재현 방법

- `baseline.csv`: 실행 순서 그대로 630행. `command.txt`: 전체 반복 실행 명령
- `commands.json`: 변경하지 않은 run_sweep.py의 순서·조건으로 복원한 개별 630회 실행 인자
- `provenance.json`: 시작·종료 시각, 실행 시간, 소스·실행 파일·공유 라이브러리 SHA-256, OS·CPU·컴파일러·Python·분석 패키지 버전, 실험 전 분석 계획
- `source-working-tree.patch`: 측정 시작 당시 추적 소스의 미커밋 차이(0바이트)
- `simulation-source-vs-upstream.patch`: 원본 기준 커밋에서 측정 소스 커밋까지 적용된 실제 소스 변경
- `analysis/summary.csv`: 완료율·정확 수신·FCT 평균·중앙값·p90·95% 수신 시간·평균의 신뢰구간·경로 비율
- `analysis/paired_comparisons.csv`: 시나리오별 21쌍, 총 63쌍의 같은 seed 비교
- `analysis/paired_observations.csv`: 각 비교에 실제로 포함된 seed·두 시간·차이
- `analysis/below_target_runs.csv`: 목표 바이트 미달 97회 원시 행
- `analysis/dominating_ci_gate.csv`: 7개 스케줄러별 0.1초 기준 대조
- `analysis/week1_comparison_cells.csv`: 210행 × 9개 항목의 차이 여부. 전부 False
- `figures/`: 전송 시간 분포·완료율·경로 비율 각 PNG·SVG
- `statistics-tests.log`: 분석 도구의 통계·입력 검사 6개 테스트
- `package-validation.json`: 원본 보존·실행 로그·문서·환경 검증
- `FROZEN.json`·`SHA256SUMS`: 동결 시점의 상태와 파일 해시 목록
- 무결성 확인: 이 폴더에서 `sha256sum -c SHA256SUMS` 실행
- 재측정: `command.txt`의 출력 경로를 새 폴더로 변경. 중단된 CSV에 이어 쓰지 않고 630회 처음부터 실행
- 분석 재현: `analysis-commands.txt`의 출력 폴더를 별도로 지정. 동결 파일 덮어쓰기 금지

## 측정·통계 정의

- 전송 시작은 시뮬레이션 시각 1초, 절대 종료 시각은 60초. 미완료 CSV의 FCT=60은 실제 완료 시간이 아닌 미완료 표시값
- 완료 처리(`done=1`): 수신량이 목표−3,000B 이상. 정확 수신은 `rx_app==size`로 별도 집계
- FCT 평균·분위수·신뢰구간은 완료 처리 실행만 사용. 미완료 실행을 제외한 시간 분포이므로 완료율을 반드시 함께 해석
- 평균의 95% 신뢰구간: 평균 ± t(0.975, n−1) × 표본표준편차/√n. 폭은 상한−하한. n<2는 계산하지 않음
- seed를 독립 반복으로 취급한 Student t 평균 추정. 신뢰구간은 개별 실행의 95% 시간 범위와 다름
- 쌍비교는 동일 시나리오·seed에서 양쪽이 모두 완료한 경우만 포함. 평균 차이의 신뢰구간은 개별 차이 표본에서 계산
- CSV의 시간 출력 정밀도 0.0001초에 맞춰 차이를 반올림. 양수인 A−B는 A가 더 느림. 승패는 같은 정밀도 기준
- Wilcoxon 검정은 0 차이를 제외하고 동률의 평균 순위를 사용. 각 차이의 부호를 뒤집는 모든 조합의 순위합 분포를 동적 계획법으로 정확히 계산
- 양측 p값은 작은 쪽 꼬리확률의 2배(최대 1). 모든 차이가 0이면 p=1, 공통 완료 표본이 없으면 계산하지 않음
- 검정은 차이 분포가 0을 중심으로 대칭이라는 귀무가설을 검토. 쌍별 평균 신뢰구간과 같은 통계량을 검정하는 것은 아님
- 시나리오당 21개 검정의 p값은 Holm 방식으로 추가 보정. 평균 차이의 95% 신뢰구간은 개별 구간이며 동시 신뢰구간은 아님
- 경로 1 비율은 완료 실행마다 rx_p1/(rx_p0+rx_p1)을 계산한 평균. FlowMonitor 수신 IP 바이트로 헤더 등을 포함하며 정확한 애플리케이션 데이터 분배율과 구분

## 게이트 판정 근거

- 실험 전 분석 계획에 7개 스케줄러의 신뢰구간 폭을 모두 공개하고, 적용 대상이 불명확하면 다음 주차 진행을 보류하도록 기록
- 기준 0.1초 충족: RR 0.0143, BLEST 0.0759, MinRTT-multi 0.0130, EAT 0.0242초
- 기준 초과: MinRTT 0.1648, ECF 0.1754, Peekaboo 0.1683초
- 계산상 직접 원인: 완료 표본의 시간 변동(표준편차 약 0.22~0.23초)과 표본 수. 이 변동을 만드는 전송 내부 동작의 원인은 미조사
- 보존·그림·완료율 표 작성과 전체 게이트 통과를 구분. 현재 동결은 측정 기록 보존이며 게이트 승인 전 상태

## 방법 참고

- SciPy Student t 분포 : https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html
- SciPy Wilcoxon 검정의 가정·동률·0 차이 주의사항 : https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html
