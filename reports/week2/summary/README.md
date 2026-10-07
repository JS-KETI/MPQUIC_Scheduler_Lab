# 2주차 진행상황

- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- 2주차 진행상황 HTML (그림 내장) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.html
- 이전 PDF (계층 정리 전) : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/summary/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.pdf

- 기존 측정 630회와 수정 후 630회를 구분한 진행상황. 각 항목을 상위 설명과 하위 조건·결과로 구분
- source.json: 사용한 원시 CSV 경로·수정 코드 버전·수신 횟수·현재 문서 형식
- figures/: 제공 analyze.py의 전송 시간 박스플롯, 요청서의 완료율·경로 비율 그림, 수정 전후 완료·전체 수신 비교
- 기본 시각화 생성 근거: artifacts/week2-basic-visuals-2026-10-08/ (원본 동결 CSV 복사본, 제공 도구 실행 출력·요약표·SVG)
- 유효한 수정의 원인·수정 결과만 요약. 전체 수정 시도 기록은 상위 상세 분석 문서에 보존
- 생성 도구: artifacts/report-tools/week2_compact_report.py (WSL --charts로 그림 생성, 기본 실행으로 Markdown·HTML 생성)
- PDF: 계층 정리 전 파일 보존. 현재 Markdown·HTML 확인 후 --pdf 옵션을 지정할 때만 별도 변환
