## 1. 1주차 작업 내용 (환경 구성·기준 데이터 재현 완료)

- WSL 2·Ubuntu 작업 환경 구성 / 설치 스크립트 빌드·63회 빠른 검증 완료
- 3시나리오 × 7스케줄러 × 10seed = 210회 실행 / 요약표·그림 생성
- 제공 수정 스택 CSV와 9개 시뮬레이션 필드 일치 / 21개 그룹 완료율·평균 FCT 편차 0
- dominating/RR 평균 3.27331초 / 기준 3.27초 ±5% 충족
- **완료 처리 191/210회**: 목표보다 최대 3,000B 부족한 상태도 완료로 판정
- **전체 수신 181/210회**: 목표 5,242,880B 전체 수신
- **바이트 미달 29건**
  - **완료 처리됐지만 전체 수신 미달 10건**
  - **완료 기준 미충족 19건**
- 발생 조합·seed·수신량은 제공 기준 CSV와 동일. 210회 실행 오류·누락·중복 0건

## 2. 단일 경로 설정별 전송 시간 비교 (원본 조건 평균 8.6756초)

- **설정 근거**
  - 요청서: 목표 전송량 5 MB·시간 8.5~9.0초 제시, 링크 속도 범위 미기재
  - 제공 실행 스크립트: `exp-wns3-one-path.sh`에 5~6Mbps·50~55ms·RR 명시
  - 코드 기본값: 고정 5Mbps·50ms·Peekaboo. 최초 검증 도구에서도 동일한 값을 실행 인자로 지정
- **고정 5Mbps 측정**
  - 조건: 고정 5Mbps·50ms·Peekaboo·목표 5,242,880B·손실률 0·OLIA
  - 결과: seed 1~3 전체 수신 3/3, 전송 시간 9.4560초
- **원본 링크 조건 5~6Mbps 측정**
  - 조건: 5~6Mbps·50~55ms·RR. 목표 5,242,880B·손실률 0·OLIA 유지
  - 결과: seed 1~10 전체 수신 10/10, 평균 8.6756초, 범위 8.6050~8.7201초
  - 원본 링크 조건에서 요청 시간 범위 8.5~9.0초에 10회 모두 해당
- **통제 실험 (스케줄러·지연·속도 변경 후 테스트)**
  - 고정 5Mbps에서 스케줄러만 RR로 변경: 9.4560초, 전체 수신 3/3
  - RR·고정 5Mbps에서 지연만 50~55ms로 변경: 평균 9.4742초, 전체 수신 3/3
  - RR·50ms에서 속도만 5~6Mbps로 변경: 평균 8.6532초, 전체 수신 10/10
  - 속도 5~5.5Mbps: 9.0262~9.0568초, 전체 수신 3/3
  - 고정 5Mbps·목표량 5,000,000B: 9.0382초, 전체 수신 1/1
  - 원본 인자·목표량 5,242,800B: 평균 8.6754초, 전체 수신 10/10
- **실행 조건 지정·수신 시각 기록 및 패킷 추적 비교**
  - `one-path-investigate.py`로 조건별 실행 인자 지정·명령·CSV·로그 기록
  - 기본 비활성 관찰 옵션으로 수신 시각·링크 조건 기록
  - 원본 코드의 실행 인자 적용 기능 사용. 전송·스케줄러 알고리즘 유지, 관찰 전후 IP 추적 일치
- **환경 문제 조치**
  - Matplotlib 인자 호환 패치 적용 후 재설치 종료 코드 0
  - 수신 시각 출력에 수동 계측 추가

## 3. 측정 기록 (조건별 실행 39회·관찰 비활성 비교 1회)

- 고정 속도·속도 범위별 측정 CSV·로그·당시 검증 기록 보존
- 다른 조건을 유지하며 설정을 한 항목씩 바꾼 반복 실험 39회 + 수신 기록을 끈 비교 실행 1회. 조건·seed 39개 조합의 중복·누락 0, 전체 수신 39/39
- 코드 분석 브랜치: `lab/w1-one-path-diagnosis-20261001`
- 2주차 30-seed 실험 미시작

## 4. 테스트 결과 그래프

- FCT 분포: 완료 처리(`done=1`) 실행만 표시 / 각 스케줄러의 완료 수·전체 수 함께 확인

![3시나리오 × 7스케줄러 FCT 분포](figures/w1_fct.png)

- 전체 수신 / 완료 처리 횟수: 181/210과 191/210 구분 / 각 칸은 전체 수신 수 / 완료 처리 수

![시나리오·스케줄러별 전체 수신과 완료 처리](figures/completion_counts.png)

- 단일 경로: 고정 5Mbps와 원본 링크 조건 5~6Mbps의 전송 시간 비교 / 모든 표시 실행은 5,242,880B 전체 수신

![단일 경로 링크 속도 조건별 전송 시간 비교](figures/one_path_comparison.png)

- 그래프는 측정 CSV를 집계해 생성

## 5. 관련 자료

- 코드·산출물 인덱스 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/README.md
- 최초 검증 보고서 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/week1-2026-10-01/1%EC%A3%BC%EC%B0%A8_%EB%B3%B4%EA%B3%A0%EC%84%9C.md / 210회 CSV : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/week1-2026-10-01/w1.csv / 요약표 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/week1-2026-10-01/w1_summary.csv / 그림 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/week1-2026-10-01/w1_fct.png
- 원인 분석 보고서 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/one-path-analysis-2026-10-01/REPORT.md / 39회 통합 CSV : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/one-path-analysis-2026-10-01/all_experiments.csv / 검증 JSON : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/one-path-analysis-2026-10-01/validation.json
- 1주차 노션 보고서 : https://app.notion.com/p/3eb5698e257e815f9031ccc630fe0864 / 시도별 분석 : https://app.notion.com/p/3ec5698e257e815bb1a9e362b6d6d262
