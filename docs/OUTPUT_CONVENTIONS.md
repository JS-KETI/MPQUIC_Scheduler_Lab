# 주차별 보고서·산출물 컨벤션

- **고정 진입점**
  - 저장소: `reports/weekN/`
  - Windows 인계본: `outputs/weekN/`
  - `weekN-날짜`, `summary`, `final`, `final2` 등 별도 최신 폴더를 만들지 않음

```text
weekN/
├─ README.md                 현재 상태·파일별 설명·원본 위치
├─ N주차 진행상황.md          사용자가 편집하는 보고서 원문
├─ N주차 진행상황.html        같은 원문·그림 내장 단일 파일
├─ N주차 진행상황.pdf         요청해 생성·확인한 경우에만 배치
├─ data/                     최종 시행 CSV·최종 집계 CSV
├─ figures/                  현재 보고서의 그림
└─ records/
   ├─ README.md              상세 기록과 이전 이력 구분
   ├─ N주차 상세 실험 기록.md
   ├─ 계측 로그 형식.md        해당 주차에 필요한 참조 문서
   ├─ provenance.json        최종 원본·해시·보고서 대응 기록
   └─ history/               이전 보고·실행·변환·검증 이력
```

- **최신 산출물 갱신**
  - 최신본은 승인된 측정과 사용자 편집 원문으로 선택. 파일 수정 시각만으로 선택하지 않음
  - 같은 이름·같은 경로를 갱신하고 이전 상태는 records/history/ 아래에서 날짜·실행 번호로 구분
  - 기존 실행·미통과 기록·원시 데이터 삭제 금지
  - 기록 문서는 records/에, 세부 송수신 원본·전체 로그는 원본 artifacts/에서 보존
  - data/는 최종 원본과 SHA256이 같은 열람용 사본. 파일별 원본 경로와 해시를 records/provenance.json에 기록
  - 공식 기준선은 artifacts/BASELINE.json 유지. 동결 폴더의 위치·내용·해시 변경 금지

- **보고서와 그림**
  - Markdown에는 figures/의 상대 경로 사용. 개인 PC 절대 경로 금지
  - 원격 열람·파일 하나 전달에는 그림 내장 HTML 우선 사용
  - HTML은 최신 Markdown에서 변환. 제목·목록 계층·표·문장·수치를 템플릿으로 다시 작성하지 않음
  - PDF는 별도 요청 시 생성하고 원문 SHA·검증 결과를 records/에 기록. 기존 PDF를 현재 원문 대응본으로 임의 단정하지 않음
  - 사용자 편집 직전 원문 해시 확인. 문서 초안·수정 제안은 records/drafts/에 두고 최신 원문을 덮어쓰지 않음

- **새 실행**
  - 원시 실험은 artifacts/weekN/runs/YYYY-MM-DD/run-NN/에 생성
  - 기존 날짜별 artifacts 원본은 이동하지 않음. 새 실험부터 적용
  - Windows 실행·변환 로그는 outputs/weekN/records/runs/YYYY-MM-DD/run-NN/에 생성
  - 임시 실행 파일도 outputs/ 최상위에 날짜별 주차 폴더를 만들지 않음

- **표기·검증**
  - 보고서 이름은 한글 N주차 진행상황. 첫 본문·3단계 불릿·그림·자료 주소의 기존 작성 규칙 유지
  - README는 현재 상태·현재 자료만 안내. 과거 수치는 records/의 이력에서 확인
  - 파일을 이동하면 현재 README·보고서 MD/HTML·생성 도구·노션을 함께 갱신
  - 이동 전후 파일 수·상대 경로·바이트·SHA256 대조. 과거 문서 원문은 그대로 보존
  - 내부 AGENTS·STATUS·.codex·.agents·개인용 보조 도구는 게시하지 않음
