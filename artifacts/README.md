# 1주차 코드·산출물 인덱스

- 최초 미통과 당시 파일과 원인 분석 이후 파일을 구분해 보관
- 원시 CSV·그림·로그·패치는 전달 산출물의 사본 / 원본 변경 없음
- GitHub에서 각 링크를 열어 확인 / CSV·로그·패치는 필요 시 Raw 또는 다운로드 사용

## 현재 보고·실행 코드

| 항목 | 보기 |
|---|---|
| 제출용 주간 보고서 | [WEEK1_WEEKLY_REPORT.md](WEEK1_WEEKLY_REPORT.md) |
| 그림 내장 열람용 보고서 | [WEEK1_WEEKLY_REPORT.html](WEEK1_WEEKLY_REPORT.html) |
| 열람용 보고 생성 도구 | [render_weekly_report.py](report-tools/render_weekly_report.py) |
| 상세 1주차 보고서 | [WEEK1_REPORT.md](WEEK1_REPORT.md) |
| 210회 반복 실행 | [run_sweep.py](../sched-lab/run_sweep.py) |
| 요약·그림 생성 | [analyze.py](../sched-lab/analyze.py) |
| 2경로 실험 소스 | [mpquic-sched-lab.cc](../scratch/mpquic-sched-lab.cc) |
| 단일 경로 소스·관찰 옵션 | [wns3-mpquic-one-path.cc](../scratch/wns3-mpquic-one-path.cc) |
| 단일 경로 원인 재현 도구 | [one-path-investigate.py](../sched-lab/one-path-investigate.py) |
| 스케줄러 구현·선언 | [mp-quic-scheduler.cc](../src/quic/model/mp-quic-scheduler.cc) / [mp-quic-scheduler.h](../src/quic/model/mp-quic-scheduler.h) |

## 최초 1주차 검증 (미통과 기록 보존)

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

## 원인 분석·원본 조건 재검증

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
| 단일 경로 최초 미통과·원본 조건 재검증 | [SVG](report-visuals-2026-10-01/one_path_comparison.svg) / [PNG](report-visuals-2026-10-01/one_path_comparison.png) |
| 집계 수치·그림 생성 코드·설명 | [figure_data.json](report-visuals-2026-10-01/figure_data.json) / [generate_figures.py](report-visuals-2026-10-01/generate_figures.py) / [README](report-visuals-2026-10-01/README.md) |

## 설치·파일 무결성

- [설치 확인 산출물](setup-test-2026-10-01)
- 파일별 SHA-256 목록: `manifest.json`
- 최초 분석 코드 버전: `f2ed7be4e9e87325aaee82ce75351b5f08c0aab8` / 파일별 검증 이력은 각 날짜 폴더의 provenance·validation JSON 참고
