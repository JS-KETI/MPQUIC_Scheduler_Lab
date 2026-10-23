## 1. 4주차 통합 수정 최종 검증

- **결과**
  - 정상 실행 1163/1,163회, 완료 1104회, 목표 바이트 전체 수신 1104회
  - 기존 완료 886회 중 879회 유지, 새 미완료 7회
  - 기존 미완료 277회 중 225회 완료 전환
- **원래 조건 유지**
  - 1,163개 원래 명령 인자와 seed를 그대로 재실행
  - 5MiB 제한 시각 60초, 50MiB 제한 시각 180초, 종료 대기 250ms
  - 시간 연장·버퍼 확대 없이 실행. 별도 시간 연장 2회는 최종 집계에서 제외
- **코드 버전**
  - 45189f80b8b67be8d0206cf8f7297175057511b5
  - source/는 실행 당시 소스 사본, integrated-source.patch는 이전 분석 브랜치 대비 통합 변경
  - 런타임 공유 라이브러리 해시는 실행 시작 전에 기록하고 종료 후 다시 대조
- **자료 보존**
  - 원래 4주차 동결 4803파일, 공식 2주차 기준 관련 660파일 보존
  - 기존 BASELINE.json·동결 데이터는 변경하지 않음

## 2. 재현 명령

새 출력 폴더에서 차례로 실행합니다.

```bash
python3 sched-lab/week4_final_run.py --out artifacts/week4/runs/YYYY-MM-DD/run-NN
python3 sched-lab/week4_analyze.py --runs artifacts/week4/runs/YYYY-MM-DD/run-NN --out artifacts/week4/analysis/YYYY-MM-DD/run-NN
python3 sched-lab/week4_final_compare.py --run artifacts/week4/runs/YYYY-MM-DD/run-NN --analysis artifacts/week4/analysis/YYYY-MM-DD/run-NN
python3 sched-lab/plot_week4_overview.py artifacts/week4/analysis/YYYY-MM-DD/run-NN/summary.csv artifacts/week4/analysis/YYYY-MM-DD/run-NN/figures/final_robustness_overview.png
```

실제 최종 원시 폴더: artifacts/week4/runs/2026-10-23/run-05/

## 3. 파일 구성

- results.csv: 1,163회 상태·수신량·전송 시간·설정
- summary.csv: 조건·시나리오·스케줄러별 완료율·수신율·시간 통계
- before_after_run.csv: 같은 실행의 수정 전후 결과
- before_after_common_fct.csv: 수정 전후 모두 완료한 같은 seed의 시간 비교·95% 신뢰구간·Wilcoxon 검정
- before_after_original_group.csv: 최초 관찰 원인 그룹별 변화. 수정 후 현재 원인 분류와 구분
- remaining.csv: 최종 미완료·전체 수신 미달 실행
- baseline_comparison.csv: 기존 조건 105회와 공식 2주차 기준의 대조
- baseline-long_fct.png: 제공 analyze.py로 만든 장시간 전송 분포
- figures/: 수정 전후 완료 횟수와 최종 조건별 그림
- logs/: 빌드·단위 검증 기록
- FROZEN.json·SHA256SUMS: 코드·라이브러리·새 원시 실행·분석 결과의 동결 기록

## 4. 별도 확인 실험

- run-01: 통합 전 대표 51회
- run-02: 1차 전체 1,163회. 완료 1,109회·기존 완료 회귀 7회
- run-03: ACK 후 중복 송신 호출 제거 13회. 장시간 5회 회복·정상 대조 5회 유지
- run-04: 손실률 1% 두 실행의 제한 시각만 60초→300초. 2회 전체 수신, 최종 집계에 합산하지 않음
- run-05: 중복 호출을 제거한 하나의 코드 버전으로 원래 1,163회 전체 재실행
