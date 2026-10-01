# 1주차 보고용 시각화 (2026-10-01)

- 기존 CSV 재분석 / 시뮬레이션 추가 실행 없음 / 원본 CSV·당시 검증 기록 보존
- [전체 수신·완료 처리 횟수](completion_counts.svg) / [PNG](completion_counts.png): 3시나리오 × 7스케줄러, 각 10회
- 각 칸은 전체 수신 / 완료 처리. 전체 수신은 `rx_app == size`, 완료 처리는 `done == 1`로 구분
- 전체 수신 181/210 / 완료 처리 191/210 / 부족 29회는 제공 기준 데이터에도 존재
- [단일 경로 비교](one_path_comparison.svg) / [PNG](one_path_comparison.png): 고정 5Mbps·속도 범위·지연·스케줄러별 통제 실험
- FCT는 앱 전송 시작부터 전체 수신까지의 `fct_full_s` / 점은 평균·개별 seed, 선은 최솟값~최댓값 / 음영은 8.5~9.0초
- 모든 표시 실행은 목표 5,242,880B 전체 수신. 80B 작은 원본 정확 재현 그룹은 이 그림에서 제외
- 각 속도 조건의 측정값·전체 수신 횟수 표시. 원본 스크립트의 링크 조건은 5~6Mbps·50~55ms·RR
- [그림의 집계 수치·입력 해시](figure_data.json) / [생성 코드](generate_figures.py)
- 기존 [FCT 분포 그림](../week1-2026-10-01/w1_fct.svg)은 수정 없이 재사용 / `done=1` 실행만 표시하며 완료율과 함께 해석

재생성: `python3 artifacts/report-visuals-2026-10-01/generate_figures.py --artifacts-root artifacts`

- Python·pandas·Matplotlib 필요 / 한글 폰트는 Windows 맑은 고딕을 우선 사용
- SVG는 한글 텍스트를 보존 / PNG는 폰트 환경에 영향받지 않는 배포용 사본

단일 경로 그림만 갱신: `python3 artifacts/report-visuals-2026-10-01/generate_figures.py --artifacts-root artifacts --one-path-only`
