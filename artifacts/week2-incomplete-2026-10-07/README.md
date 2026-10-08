# 2주차 미완료 원인 분석 산출물

- 원본 동결 기준: ../week2-2026-10-02/run-01. 제공 01+02 패치 결과 보존
- 수정 스택: 01+02+A(소켓 읽기)+B(스트림 중복)+C(ACK 손실 감지)
- 모든 실행의 실제 명령·소스 HEAD+패치·해시·RESULT·표준출력·관찰 로그는 각 폴더에 보관
- 원본 미완료 62회 중 제공 seed 1~10의 19회는 제공 CSV와 동일. 추가 seed 11~30의 43회는 제공 기준 없음

| 폴더 | 변경·목적 | 결과 |
|---|---|---|
| 01-extended-300s | 종료 시각만 300초 | 0/62 완료, 원본과 수신량 동일 |
| 02-observe-original | 첫 관찰 연결 시도 | 경로 오류로 62회 RESULT 없음, 도구 수정 후 03에 재실행 |
| 03-observe-original | 원본 62회 관찰 | 원본 9지표 모두 일치 |
| 04-socket-rx-only | 수정 A만 적용 | 완료 0/62, 원본 수신량 동일 |
| 05-stream-rx-only | 수정 B만 적용 | 완료·전체 수신 54/62 |
| 06-loss-detection-only | 수정 C만 적용 | 나머지 8/8 완료·전체 수신 |
| 07-original-queue-observe | 장치 큐·물리 계층 추적 | 8회 정체 유지. 이 계층 폐기는 없음 |
| 08-combined-full-630 | A+B+C, 기본 조건 630회 | 완료 630/630·전체 수신 621/630 |
| 09-completion-grace-250ms | 부족 9회만 완료 후 대기 연장 | 전체 수신 9/9, 완료 시간 동일 |
| 10-original-ip-observe | IPv4 폐기 추적 | 8회 재조립 시간 초과 |
| 11-original-fragment-observe | IP 조각별 송수신 추적 | 첫 조각 누락·마지막 조각 도착 |
| 12-original-qdisc-observe | FqCoDel 폐기 이유·QUIC 번호 | 8회 Target exceeded drop 직접 매핑 |
| 13-final-observe-62 | 관찰 옵션 검증 | 전체 수신 62/62, 08과 9지표 모두 동일 |
| 14-fin-preservation-full-630 | FIN 종료 표식 보존 후 최종 코드 | 630회 완료·621회 전체 수신, 08과 9지표 모두 동일 |

## 회귀 테스트와 도구 수정 기록

- regression-latest-original/before-fin/final.json: 최종 테스트 코드로 원본 실패·FIN 보완 전 실패·최종 수정 통과를 대조. 소스 해시 포함
- regression-fin-final.json: 종료 표식 FIN이 완전 중복 데이터에 처음 붙는 경우에도 종료 상태·바이트 수·순서 보존 검사 통과
- stream-rx-fin-preserved.patch: 비판 검토의 FIN 보완을 포함한 최종 B 패치
- regression-byte-order-original.json / fixed.json: 같은 최종 테스트 코드에서 원본 실패 → 수정 통과. 실제 바이트 순서 포함
- regression-stream-only.json: 초기 GetRxAvailable 호출을 수신 대기량으로 오인한 테스트 하네스. PendingBytes로 고친 후 원본/수정을 다시 대조
- regression-byte-order-*-launch-error.json: 공유 라이브러리 경로 미지정. argument-error.json: --Case 인자 오기. 프로토콜 테스트 결과와 구분
- 올바른 재실행: 각 명령에 LD_LIBRARY_PATH=build/lib 적용. build/scratch/quic-rx-regression --Layer=socket 또는 --Layer=stream; build/scratch/quic-loss-regression
- critical-review.md·evidence.csv: 비판 검토 에이전트의 독립 가설 검토·원인 증거
- analysis/: 630행 전후 대조·62회 원인 분류·9회 종료 대기 진단·21조합 통계·63쌍 비교·환경·동결 해시 검증
- 후보별 patch는 core 변경만 분리. 실행별 source.patch는 해당 실행의 소스 상태를 HEAD에 적용하기 위한 변경 기록
- generate_analysis.py: 보존 CSV로 표·그림·보고서 생성. root는 스크립트 위치에서 저장소로 계산

- 상세 분석 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/2%EC%A3%BC%EC%B0%A8%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%EC%9B%90%EC%9D%B8%20%EB%B6%84%EC%84%9D.md
