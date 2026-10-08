# 주차별 코드·산출물 인덱스

- 2주차 기본 시각화 생성 근거 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis/artifacts/week2-basic-visuals-2026-10-08

- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- 2주차 진행상황 HTML (그림 내장) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html
- 이전 PDF (250ms 전체 재검증 반영 전) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.pdf

- 2주차 미완료 원인 분석 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/2%EC%A3%BC%EC%B0%A8%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%EC%9B%90%EC%9D%B8%20%EB%B6%84%EC%84%9D.md
- 수정 검증: 원본 미완료 62회 모두 전체 수신. 630회 완료·621회 전체 수신, 시간 증가와 종료 후 기록 범위 별도 확인

## 2주차 630회 기준 데이터

- 제공 기준과 추가 seed의 대조 기록 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/artifacts/week2-reference-review-2026-10-02

- 원시 측정·통계·그림·실행 기록 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/artifacts/week2-2026-10-02/run-01
- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/week2/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- 통계 계산 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/sched-lab/stats.py
- 그림 생성 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/sched-lab/plot_baseline.py

- 초기 검증 기록과 단일 경로 조건별 비교 기록을 구분해 보관
- 원시 CSV·그림·로그·패치는 전달 산출물의 사본 / 원본 변경 없음
- GitHub에서 각 링크를 열어 확인 / CSV·로그·패치는 필요 시 Raw 또는 다운로드 사용

## 현재 보고·실행 코드

| 항목 | 보기 |
|---|---|
| 1주차 진행상황 | [1%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md](../reports/week1/1%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md) |
| 1주차 진행상황 HTML | [1%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html](../reports/week1/1%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html) |
| 보고서 HTML 생성 도구 | [render_weekly_report.py](report-tools/render_weekly_report.py) |
| 1주차 상세 실험 기록 | [1%EC%A3%BC%EC%B0%A8%20%EC%83%81%EC%84%B8%20%EC%8B%A4%ED%97%98%20%EA%B8%B0%EB%A1%9D.md](../reports/week1/1%EC%A3%BC%EC%B0%A8%20%EC%83%81%EC%84%B8%20%EC%8B%A4%ED%97%98%20%EA%B8%B0%EB%A1%9D.md) |
| 210회 반복 실행 | [run_sweep.py](../sched-lab/run_sweep.py) |
| 요약·그림 생성 | [analyze.py](../sched-lab/analyze.py) |
| 2경로 실험 소스 | [mpquic-sched-lab.cc](../scratch/mpquic-sched-lab.cc) |
| 단일 경로 소스·관찰 옵션 | [wns3-mpquic-one-path.cc](../scratch/wns3-mpquic-one-path.cc) |
| 단일 경로 원인 재현 도구 | [one-path-investigate.py](../sched-lab/one-path-investigate.py) |
| 스케줄러 구현·선언 | [mp-quic-scheduler.cc](../src/quic/model/mp-quic-scheduler.cc) / [mp-quic-scheduler.h](../src/quic/model/mp-quic-scheduler.h) |

## 최초 1주차 검증 (당시 원시 기록 보존)

| 항목 | 보기 |
|---|---|
| 최초 보고서·환경 | [최초 보고서](week1-2026-10-01/1주차_보고서.md) / [env.md](week1-2026-10-01/env.md) |
| 210회 결과·요약 | [w1.csv](week1-2026-10-01/w1.csv) / [w1_summary.csv](week1-2026-10-01/w1_summary.csv) |
| 그림·HTML | [PNG](week1-2026-10-01/w1_fct.png) / [SVG](week1-2026-10-01/w1_fct.svg) / [HTML](week1-2026-10-01/w1_plot.html) |
| 바이트 부족 기록 | [미완료 실행](week1-2026-10-01/stalled_runs.csv) / [완료 처리·바이트 부족](week1-2026-10-01/completed_below_target.csv) |
| 검증·명령·로그 | [validation.json](week1-2026-10-01/validation.json) / [provenance.json](week1-2026-10-01/provenance.json) / [명령](week1-2026-10-01/commands.json) / [실행 로그](week1-2026-10-01/sweep.log) |
| 초기 단일 경로 결과 | [single_path.csv](week1-2026-10-01/single-path/single_path.csv) / [초기 실행별 로그](week1-2026-10-01/single-path) / [초기 보조 실험](week1-2026-10-01/single-path/diagnostics.csv) |
| 당시 패치·재현 도구 | [patches](week1-2026-10-01/patches) / [재현_분석_도구](week1-2026-10-01/재현_분석_도구) |
| 전체 최초 검증 산출물 | [week1-2026-10-01](week1-2026-10-01) |

## 단일 경로 조건별 비교·원본 조건 측정

| 항목 | 보기 |
|---|---|
| 시도별 분석 보고 | [REPORT.md](one-path-analysis-2026-10-01/REPORT.md) |
| 39회 통합 결과 | [all_experiments.csv](one-path-analysis-2026-10-01/all_experiments.csv) |
| 가설별 29회 결과·요약 | [experiments.csv](one-path-analysis-2026-10-01/experiments/experiments.csv) / [summary.json](one-path-analysis-2026-10-01/experiments/summary.json) |
| 정확 목표량 재검증 10회 | [experiments.csv](one-path-analysis-2026-10-01/reference-full-size/experiments.csv) / [summary.json](one-path-analysis-2026-10-01/reference-full-size/summary.json) |
| 최종 검증 기록 | [validation.json](one-path-analysis-2026-10-01/validation.json) |
| 변경 패치 | [05-one-path-diagnosis.patch](one-path-analysis-2026-10-01/05-one-path-diagnosis.patch) |
| 빌드·실행 로그 | [build.log](one-path-analysis-2026-10-01/build.log) / [experiment-run.log](one-path-analysis-2026-10-01/experiment-run.log) / [reference-run.log](one-path-analysis-2026-10-01/reference-run.log) |
| 실행별 Rx·링크 조건·IP 추적 | [초기 통제 실험](one-path-analysis-2026-10-01/experiments) / [정확 목표량 재검증](one-path-analysis-2026-10-01/reference-full-size) / [관찰 비활성 대조](one-path-analysis-2026-10-01/observer-disabled) |
| 인계 도구·소스 사본 | [reproduction-tools](one-path-analysis-2026-10-01/reproduction-tools) |
| 전체 분석 산출물 | [one-path-analysis-2026-10-01](one-path-analysis-2026-10-01) |

## 보고서 본문용 시각화

| 항목 | 보기 |
|---|---|
| 전체 수신 / 완료 처리 횟수 | [SVG](report-visuals-2026-10-01/completion_counts.svg) / [PNG](report-visuals-2026-10-01/completion_counts.png) |
| 단일 경로 링크 조건별 전송 시간 비교 | [SVG](report-visuals-2026-10-01/one_path_comparison.svg) / [PNG](report-visuals-2026-10-01/one_path_comparison.png) |
| 집계 수치·그림 생성 코드·설명 | [figure_data.json](report-visuals-2026-10-01/figure_data.json) / [generate_figures.py](report-visuals-2026-10-01/generate_figures.py) / [README](report-visuals-2026-10-01/README.md) |

## 설치·파일 무결성

- [설치 확인 산출물](setup-test-2026-10-01)
- 파일별 SHA-256 목록: `manifest.json`
- 원시 분석 기록의 코드 SHA: `f2ed7be4e9e87325aaee82ce75351b5f08c0aab8` / 명의 정정 후 같은 코드의 SHA: `40542b8dde3120ad206f7c5ae9bf969f5babb48b`
- 이전·새 SHA는 위 명의 정정 대응표 참고. 파일별 검증 이력은 각 날짜 폴더의 provenance·validation JSON에 보존
