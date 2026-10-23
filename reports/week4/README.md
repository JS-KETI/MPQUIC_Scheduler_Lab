# 4주차 진행상황

- **최신 결과**
  - 완료 처리·전체 수신 각각 1,104/1,163회. 기존 미완료 225회 해소, 신규 미완료 7회, 최종 미완료 59회
  - 통합 수정본의 정식 적용 보류. 공식 2주차 기준값·4주차 최초 동결 자료 보존
- **자료 구성**
  - 진행상황은 실험별 핵심 결과·문제·수정·최종 결과 중심. 본문 그림 4개, HTML에는 이미지 내장
  - `data/`는 측정값·통계, `figures/`는 그림, `records/`는 상세 분석·검증 기록

## 현재 보고서

- **4주차 진행상황 Markdown (그림 4개 내장·파일 하나로 다운로드)**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/records/exports/4%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
  - 다운로드 후 이미지 내장 Markdown을 지원하는 편집기에서 열기

- **4주차 진행상황**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/4%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- **4주차 진행상황 HTML (이미지 내장)**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/4%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html

## 측정값·그림·상세 분석

- **최초 1,163회 시행의 측정값과 조건별 통계**
  - **각 실행의 완료·수신량·전송 시간**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/data/results.csv
  - **스케줄러·시나리오·설정별 평균·완료율·전체 수신율**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/data/summary.csv
- **최초 공통 코드 버전의 장시간 전송 기준값**
  - **50MiB 전체 210회 원본**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/data/baseline-long.csv
  - **50MiB 스케줄러별 통계**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/data/summary-long.csv
  - **같은 seed의 시간차·신뢰구간·승패 비교**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/data/paired_comparisons.csv
- **최초 측정의 시각화·재현 자료**
  - **장시간 전송 완료와 전체 수신 비율**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/long_completion.png
  - **장시간 전송의 경로 1 수신 IP 바이트 비중**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/long_path_share.png
  - **스케줄러별 손실률·큐·버퍼 비교 그림**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/robustness.png
  - **소스·설치·명령·데이터·그림 재현 패키지**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/artifacts/week4/package/2026-10-18/README.md
  - **예비 시도·전체 미완료 조합·재현 검증 상세 기록**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-validation-20261018/reports/week4/records/4%EC%A3%BC%EC%B0%A8%20%EC%83%81%EC%84%B8%20%EC%8B%A4%ED%97%98%20%EA%B8%B0%EB%A1%9D.md

- **미완료 277회 원인과 수정 후보 검증 결과**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/records/4%EC%A3%BC%EC%B0%A8%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%EC%9B%90%EC%9D%B8%20%EB%B6%84%EC%84%9D.md

- **통합 수정 후 최종 검증 산출물**
  - **전체 1,163회 최종 측정값**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-results.csv
  - **스케줄러·시나리오·설정별 최종 통계**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-summary.csv
  - **수정 전후 각 실행의 완료·수신량·시간 비교**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-before-after-executions.csv
  - **통합 수정·검증 결과·남은 실행 상세 기록**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/records/4%EC%A3%BC%EC%B0%A8%20%ED%86%B5%ED%95%A9%20%EC%88%98%EC%A0%95%20%EC%B5%9C%EC%A2%85%20%EA%B2%80%EC%A6%9D.md
  - **최종 미완료·전체 수신 미달 실행**
    - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-remaining.csv

## 추가 비교 자료

- **설정 변화에 따른 스케줄러 평균 전송 시간의 우열 변화 — 최초 측정**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/observed_rank_changes.csv
- **수정 전후 같은 seed의 전송 시간 비교**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-common-seed-times.csv
- **수정 후 50MiB 전송 210회 원본**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-long-results.csv
- **수정 후 50MiB 스케줄러별 통계**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/data/final-long-summary.csv
- **경로 성능 저하 시점·속도·지연별 상세 그림 — 최초 측정**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/degradation.png
- **50MiB 전송 시간 분포 — 최초 측정·제공 도구**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/long_fct_provided.png
- **수정 후 손실률·큐·버퍼별 완료·전체 수신 그림**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-final-validation-20261023/reports/week4/figures/final_robustness_overview.png
- **축약 전 전체 실험·검증 기록 (수치·표·설명 보존)**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/e5c5a79589dcd233893c9c8ae8aefd529b8a02eb/reports/week4/4%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
