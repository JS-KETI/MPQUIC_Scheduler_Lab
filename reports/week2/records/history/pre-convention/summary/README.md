# 2주차 진행상황
## 현재 2주차 공식 기준값 (630회 완료·전체 수신)

- 기준값 SET (측정값·통계·그림) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis/artifacts/week2-completion-2026-10-08/run-01
- 기준값 통계 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/artifacts/week2-completion-2026-10-08/run-01/analysis/summary.csv
- 각 시행 원본 측정값 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/artifacts/week2-completion-2026-10-08/run-01/results.csv
- 시각화 자료 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis/artifacts/week2-completion-2026-10-08/run-01/figures
- 현재 기준선 지정: artifacts/BASELINE.json. 원본 동결 자료는 최초 측정 이력으로 보존


- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- 2주차 진행상황 HTML (그림 내장) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html
- 2주차 진행상황 PDF (현재 Markdown 구성 유지) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/raw/fix/%239-week2-incomplete-diagnosis/reports/week2/pdf/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.pdf
- 이전 PDF (250ms 전체 재검증 반영 전) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.pdf

- 기존 측정·코드 수정 후 10ms·종료 대기 250ms의 630회 결과를 구분한 진행상황
- source.json: 사용한 원시 CSV 경로·수정 코드 버전·수신 횟수·현재 문서 형식
- figures/: 제공 analyze.py의 전송 시간 박스플롯, 요청서의 완료율·경로 비율 그림, 코드 수정 및 종료 대기 적용 전후 비교
- 기본 시각화 생성 근거: artifacts/week2-basic-visuals-2026-10-08/ (원본 동결 CSV 복사본, 제공 도구 실행 출력·요약표·SVG)
- 유효한 수정의 원인·수정 결과만 요약. 전체 수정 시도 기록은 상위 상세 분석 문서에 보존
- 그림 생성 도구: artifacts/report-tools/week2_compact_report.py (--charts·--completion-chart). 문서 변환 원문은 현재 Markdown
- PDF: 현재 Markdown의 제목·3단계 목록·표·그림·참고 자료를 유지해 변환. 이전 PDF는 보존

- 종료 대기 250ms 전체 재검증 자료 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis/artifacts/week2-completion-2026-10-08/run-01
