# 4주차 재현 패키지

- 소스·설치 도구·원시 측정·명령·통계·그림을 포함한 패키지
- GitHub 파일 크기 한도에 맞춰 분할. 아래 모든 파일을 같은 폴더에 저장한 뒤 결합
- 원시 로그·최초 미완료·새 조건의 미완료 기록을 포함

## 파일 받기

- **분할 파일 01 (64.0MiB)**
  - https://raw.githubusercontent.com/JS-KETI/MPQUIC_Scheduler_Lab/lab/week4-validation-20261018/artifacts/week4/package/2026-10-18/week4-reproduction.tar.xz.part-01
- **분할 파일 02 (47.8MiB)**
  - https://raw.githubusercontent.com/JS-KETI/MPQUIC_Scheduler_Lab/lab/week4-validation-20261018/artifacts/week4/package/2026-10-18/week4-reproduction.tar.xz.part-02
- **SHA256SUMS 검증 파일**
  - https://raw.githubusercontent.com/JS-KETI/MPQUIC_Scheduler_Lab/lab/week4-validation-20261018/artifacts/week4/package/2026-10-18/SHA256SUMS
- **ARCHIVE_SHA256 검증 파일**
  - https://raw.githubusercontent.com/JS-KETI/MPQUIC_Scheduler_Lab/lab/week4-validation-20261018/artifacts/week4/package/2026-10-18/ARCHIVE_SHA256

## Ubuntu에서 결합·검증·압축 해제

```bash
sha256sum -c SHA256SUMS
cat week4-reproduction.tar.xz.part-* > week4-reproduction.tar.xz
sha256sum -c ARCHIVE_SHA256
tar -xJf week4-reproduction.tar.xz
cd week4-reproduction
sha256sum -c SHA256SUMS
```

- 이후 압축 내부 README.md의 설치·분석·재측정 명령 사용
- 새 소스 빌드·13회 재현·전체 데이터 표/그림 대조 결과는 records/reproduction-validation.json에 보관
