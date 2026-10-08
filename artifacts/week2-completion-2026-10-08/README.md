# 2주차 종료 대기 250ms 전체 재검증

- 범위: 3시나리오 × 7스케줄러 × seed 1~30 = 630회
- 실행 구성: 기존 수신·재전송 수정 코드 유지, CompletionGraceMs=250을 실행 인자로 지정
- 유지 설정: 목표 5,242,880B, 완료 임계량 목표−3,000B, 손실률 0, OLIA, 동일 링크·seed, 종료 제한 60초
- 결과: 완료 처리 630/630, 목표 바이트 전체 수신 630/630, 누락·중복·실행 오류 0건
- 기존 수정 코드 10ms 결과: 완료 처리 630/630, 전체 수신 621/630. 부족 9회 모두 전체 수신으로 변경
- 시간 대조: 630회 모두 기록된 FCT·FCT95 동일
- 제공 기준: 기존 기준 스택의 seed 1~10만 존재. 수정 스택의 250ms 재검증은 별도 측정
- 기준 보존: 기존 동결 폴더 27개 해시 일치

## 산출물

- run-01/results.csv: 전체 630회 결과
- run-01/commands.json·provenance.json·source.patch: 실제 명령·실행 시각·HEAD·해시·실행 당시 변경
- run-01/effective-code.patch: 기존 기준 코드에서 현재 커밋까지의 실험 코드 변경
- run-01/environment.json: OS·컴파일러·Python·CPU·실행 시간
- run-01/validation.json·comparison.json: 조합·수신 결과·10ms 결과·명령·동결 해시 대조
- run-01/analysis/: 조합별 통계·같은 seed의 쌍비교·dominating 신뢰구간
- run-01/logs/·run-01-runner.log: 실행별 압축 출력·전체 실행 출력

## 재현 명령

```sh
python3 sched-lab/incomplete-investigate.py --baseline-dir artifacts/week2-2026-10-02/run-01 --out artifacts/week2-completion-2026-10-08/run-02 --selection all --extra=--CompletionGraceMs=250
```

- 새 실행 폴더를 사용하며 기존 CSV에 추가 기록하지 않음
- dominating 신뢰구간 폭: MinRTT-multi 0.0257초로 0.1초 기준 충족. MinRTT·ECF·Peekaboo는 기준 초과, 적용 대상 확인 필요
