## 1. 미완료 원인 분석 자료

- 기존 1,163회 중 미완료 277회에 대한 후속 분석. 원래 기준 결과·동결 파일은 변경하지 않음
- `classification.csv`: 최초 중단 지점별 277회 분류. `evidence_run`은 직접 근거를 가진 관찰 실행
- `classification-initial.csv`: run-08 직후 잠정 분류. 당시 수신 소켓의 진단 속성 복사가 빠져 있어 RX 중단은 run-10에서 재확인
- `experiment-results.csv`: 추가 954회 전체 결과. 수정 후보마다 별도 실행·패치 보존
- `candidate-by-original-group.csv`: 최초 원인 그룹별 후보 결과. 서로 다른 후보의 완료 수를 합산하지 않음
- `classification-validation.json`: 원본 대조 21항목·동결 자료 보존 검사
- `observational-source/`: 후보 적용 전 정확한 소스 사본. `observation.patch`: 기본 비활성 관찰 추가분
- `candidate-*.patch`: 원인 확인용 후보 전체 차이. 공식 채택 상태 아님
- `reproduction-tools/`: 실제 분석에 사용한 보조 스크립트 원본. 기존 작업 폴더에 묶인 조사 기록이며 그대로 실행하지 않음

## 2. 코드와 원시 실행의 대응

- 기준 소스 커밋: `47e82c0c7f7efb477ae6179bc6e490370ce137a3`
- 원시 결과: `artifacts/week4/runs/2026-10-18/run-07`부터 `run-20`
- 각 실행의 `metadata.json`에 코드·바이너리·패치 해시, `working.patch`에 당시 차이 보존
- 각 실행 하위 `command.json`에 인자 전체, `stdout.log`에 RESULT·종료·중단·크기 기록, `diag-state.csv`에 앱·소켓·스트림·경로 상태
- `DiagnosticPrefix`는 상태 기록 위치. 빈 값이 기본값. `DiagnosticPackets`는 추가 프레임 추적 여부. 실험 진행을 바꾸는 옵션 아님
- `STREAM.available_bytes`는 송신 여유 공간. 수신 여유 공간으로 해석하지 않음
- `DIAG_WIRE_SUMMARY`는 송신/수신 QUIC 프레임 묶음 최대 크기와 65,507B 초과 횟수. QUIC·UDP·IP 헤더까지 포함한 전체 패킷 크기가 아님
- 제한 시각 직전 상태로 원인을 판정. 시뮬레이션 종료 시 앱 정리로 호출된 Close는 조기 종료 근거에서 제외
- run-18·run-19는 수신 스트림 버퍼만 8,388,608B로 덮어쓴 소스 후보. 공통 CONFIG4 BufferBytes=1,048,576은 나머지 세 버퍼 값이며, 네 버퍼 모두 1MiB인 실험과 구분

## 3. 재현 방법

- 기존 결과 폴더에 덧붙이지 않고 새 폴더 사용. `sched-lab/week4_diagnose.py --mode all --out artifacts/week4/runs/새날짜/run-01`은 현재 코드로 원래 277회 실행
- 원래 조사 환경은 Ubuntu 24.04·저장소의 주차 설치 스크립트와 metadata 기록 사용
- 후보를 재현할 때 별도 깨끗한 체크아웃을 기준 커밋에 맞춘 뒤, 해당 run의 `working.patch`를 한 번만 적용하고 빌드
- 패치는 관찰 변경까지 포함하므로 현재 관찰 코드 위에 중복 적용하지 않음. 기존 수정이 있는 작업 폴더에서 실험용 복원을 실행하지 않음
- 각 `plan.json`의 인자를 그대로 사용. 실행 경로인 DiagnosticPrefix만 새 결과 폴더로 바꿈
- `sched-lab/week4_diagnose_analyze.py`는 보존된 실행으로 분류·집계·원본 보존 검사를 다시 수행. 새 시뮬레이션은 실행하지 않음
- 결과 해시: 이 폴더의 `SHA256SUMS`는 후속 진단 자료만 포함. 원래 `artifacts/week4/SHA256SUMS`와 공식 baseline 포인터는 그대로 유지

## 4. 수정 후보의 제한

- `candidate-close.patch`: 소켓 대기량 확인. 스트림 대기량까지 포괄하는 일반 종료 설계는 추가 검토 필요
- `candidate-stream.patch`: ACK 후 스트림 잔량 전달 + 종료 조건 후보
- `candidate-rx.patch`: 수신 스트림 버퍼만 8MiB. 설정 완화 실험
- `candidate-stream_rx.patch`: 위 두 원인 후보와 수신 스트림 버퍼 변경 결합
- `candidate-queue.patch`: 크기 분할만 적용한 실패 후보. 0/87 전체 수신
- `candidate-queue_frames.patch`: 프레임별 재구성과 분할을 함께 적용. 해당 87/87 전체 수신; 비STREAM 제어 프레임·빈 FIN·파싱 실패·분할 헤더의 바이트 예산은 정식 적용 전 보완 대상

## 5. 분석 기록

- 원인별 측정·수정 후보·결과
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week4-incomplete-diagnosis-20261018/reports/week4/records/4%EC%A3%BC%EC%B0%A8%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%EC%9B%90%EC%9D%B8%20%EB%B6%84%EC%84%9D.md
