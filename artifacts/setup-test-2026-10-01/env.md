# MP-QUIC 작업환경 설치 및 빠른 검증 결과

기록일: 2026-10-01 (Asia/Seoul)

## 완료 범위

- WSL 2 / Ubuntu 설치, 일반 사용자 설정, 필수 패키지 설치, 작업본 복사 및 해시 검증 완료.
- setup.sh 기본 모드: 지정 커밋 복제, 01+02 패치, optimized 빌드, 3-seed 빠른 검증, 요약 CSV 및 그림 생성 완료.
- Ubuntu 기본 Matplotlib 호환 패치 추가. 수정된 setup.sh를 새 폴더에서 전체 실행하여 종료 코드 0 확인.
- 별도 10-seed 재현 실험 및 이후 주차 작업은 수행하지 않음. 이번 검증은 환경 준비 완료를 확인하는 스모크 테스트이며, 1주차 전체 게이트 판정은 아님.

## 환경

| 항목 | 확인한 값 |
|---|---|
| Windows | Windows 11 Home, 10.0.26200.9457 |
| CPU / Windows 메모리 | Intel Core Ultra 7 265F, 20코어 / 약 32GB |
| WSL 프로그램 | 3.0.1.0 |
| WSL 등록 버전 | 2 |
| Linux | Ubuntu 24.04.5 LTS |
| Linux 커널 | 6.18.40.1-microsoft-standard-WSL2 |
| 기본 사용자 | ubuntu (UID 1000, sudo 그룹) |
| WSL에서 확인한 CPU / 메모리 | 20 논리 CPU / 약 15GiB, swap 4GiB |
| Git | 2.43.0 |
| Python | 3.12.3 |
| g++ | 13.3.0 |
| Eigen 패키지 | libeigen3-dev 3.4.0-4build0.1 |
| pandas | 2.1.4 |
| Matplotlib | 3.6.3 |
| 원본 커밋 | 99df419d0bb49e81b9afa1f4747769ab3f9e53ae |
| 주 작업 브랜치 | lab/setup-ubuntu-20261001 |

설치 패키지: `build-essential python3 git libeigen3-dev python3-pandas python3-matplotlib`.

## 작업 경로

- 전달 원본: `C:\Users\okqkf\OneDrive\Desktop\keti`
- Windows 보존 사본: `C:\Users\okqkf\Documents\Codex\2026-10-01\c-users-okqkf-onedrive-desktop-keti\work\keti-source`
- Linux 패키지: `/home/ubuntu/projects/keti/mpquic-sched-lab`
- 실제 코드 및 빌드: `/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic`
- 새 설치 전체 검증용 폴더: `/home/ubuntu/work/keti-setup-check`
- 주 결과: `/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic/sched-lab/quick.csv`

원본 23개 파일과 Windows 보존 사본의 해시 불일치 0개. Linux 복사 직후에도 23개 해시를 대조하여 불일치 0개 확인. 빌드와 실험은 Linux 파일 시스템에서 수행했다.

## 설치 중 확인한 오류와 해결

1. Windows 기능 활성화 후 재부팅 완료. 재부팅 전 WSL 2 가상화 오류는 재부팅 후 사라졌으며 Ubuntu가 버전 2로 실행됨.
2. 온라인 WSL 설치 명령은 등록이 진행되지 않아 중단. Microsoft WSL DistributionInfo.json에 명시된 공식 Ubuntu 이미지를 직접 다운로드하고 SHA-256 검증 후 로컬 이미지로 설치함.
   - 이미지: https://releases.ubuntu.com/24.04.5/ubuntu-24.04.5-wsl-amd64.wsl
   - SHA-256: `bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e`
   - 설치: `wsl --install --from-file <검증된 이미지> --name Ubuntu-24.04 --no-launch`
3. 원본 setup.sh는 빌드와 63회 실행 후 `analyze.py`의 `tick_labels` 인자가 지원되지 않아 종료 코드 1로 끝남.
4. Linux 작업본에 `patches/03-matplotlib-compat.patch`를 추가하여 `tick_labels=labels`를 `labels=labels`로 변경함. 시뮬레이터와 결과 값은 변경하지 않음.
5. Linux 작업본 setup.sh에 03 호환 패치 적용 단계를 추가함. 원본 스크립트는 `setup.original.sh`로 보존.
6. 수정된 setup.sh를 새 테스트 폴더에서 전체 실행하여 종료 코드 0, 결과 63행, 요약·PNG 생성 확인. 주 작업 폴더의 기존 결과는 분석만 다시 실행함.

## 빠른 검증 결과

| 항목 | 결과 |
|---|---|
| 계획한 조합 | 3 시나리오 × 7 스케줄러 × seed 1~3 = 63 |
| 실제 결과 / 고유 조합 | 63행 / 63개 |
| 누락 / 중복 / 실행 실패 | 0 / 0 / 0 |
| dominating 전송 완료 | 21/21 |
| competing 전송 완료 | 19/21 |
| degrade 전송 완료 | 21/21 |
| 전체 전송 완료 | 61/63 |
| 목표 5,242,880B를 정확히 수신한 실행 | 61개 |
| 최초 빌드 시간 | 약 29.1초 |
| 주 검증 63회 실행 시간 합계 | 약 23.5초 (CSV wall_s 합계) |
| dominating / RR 평균 FCT | 3.286초 (참고 3.27초 대비 약 +0.5%) |
| degrade / MinRTT-multi 평균 FCT | 6.331초 (참고 6.33초) |

FCT는 전체 데이터를 수신할 때까지의 시간이다. 3-seed 빠른 검증 수치와 제공된 10-seed 평균은 표본 수가 달라 일부 항목에 차이가 날 수 있으며, 전체 재현 판정은 이번 범위에 포함하지 않았다.

### 사전 제공 데이터와 직접 대조

추가 대조 결과, 제공된 `results_fixed_stack.csv`의 동일 시나리오·스케줄러·seed 1~3에 대응하는 63행과 새 결과의 63행은 CSV에 기록된 정밀도에서 모두 일치했다. 확인한 열은 size, fct_s, fct95_s, rx_app, rx_p0, rx_p1, delay_p0_ms, delay_p1_ms, done이다. 전송 미완료 2개의 조합과 수신 바이트도 같다.

실제 컴퓨터의 실행 시간 wall_s는 다르다. 같은 63개 조합에서 새 PC 합계 23.5초, 제공 데이터 합계 49.2초였다. 시뮬레이션 FCT와 실제 컴퓨터 처리 시간은 별개이다.

새 3-seed 평균을 제공된 10-seed 평균과 직접 비교하면 차이가 있다. 예를 들어 competing/BLEST는 5.0166초 대 5.9052초(-15.05%), competing/MinRTT는 5.3880초 대 5.7806초(-6.79%)이다. 비교에 포함된 seed가 다르기 때문이며, 새 결과의 동일 seed 대조에서는 차이가 없었다. 전체 10-seed의 새 PC 재현은 아직 실행하지 않았다.

대조 기록: `reference-comparison.json`, 전체 평균 대조 표: `reference-mean-comparison.csv`.

전송 미완료 2개는 competing의 EAT와 MinRTT-multi에서 각각 seed=2였다. 두 실행 모두 정상 프로세스 종료 및 RESULT 출력이 있었지만, 제한된 시뮬레이션 시간까지 5,237,104B만 수신했다. 이는 README에 기록된 tail stall(마지막 일부 데이터가 도착하지 않는 현상)과 같은 유형이며 원인 분석·수정은 수행하지 않았다. 평균 FCT에는 완료 실행만 포함된다.

## 패치 식별

| 파일 | SHA-256 |
|---|---|
| 01-sched-lab.patch | 2c2930aef76d3c4fe00915e142e17ffdb8bcbad7cec548e71a164e37fa19beb6 |
| 02-stack-fixes.patch | 99cad1585faeff652114579c362d748c7523be7e282c2abb7e9c04842b19e334 |
| 03-matplotlib-compat.patch | 208d4ebc4f07719dbfb14bab01fb78add03e7c35a4c67132c991d5df2bf39415 |

패키지 기본 패치와 호환 수정은 주 작업 브랜치의 작업 파일에 적용되어 있으며 아직 커밋하지 않았다. 앞으로 실제 수정할 위치는 Linux의 mpquic 저장소이다.

## 다음 접속

PowerShell에서 바로 실제 코드 폴더로 접속:

```powershell
wsl -d Ubuntu-24.04 --cd /home/ubuntu/projects/keti/mpquic-sched-lab/mpquic
```

이후 Ubuntu에서 증분 빌드는 `./waf build`로 실행한다. setup.sh는 새 저장소 설치용이므로 이미 mpquic가 있는 폴더에서 반복 실행하면 clone 단계가 실패한다.

계정 비밀번호는 사용자가 직접 정한다. 아직 설정하지 않았다면 PowerShell에서 아래 명령을 실행하고 두 번 입력한다. 비밀번호를 채팅에 보내지 않는다.

```powershell
wsl -d Ubuntu-24.04 -u root -- passwd ubuntu
```

## 보관한 산출물

- `quick.csv`: 주 작업 폴더의 63회 결과.
- `quick_summary.csv`, `quick_fct.png`: 요약과 그림.
- `quick-validation.json`: 행·조합·출력 검증 기록.
- `setup-original.log`: 원본 setup.sh의 빌드·실험 및 최종 분석 오류.
- `analysis-fixed.log`: 호환 수정 후 주 결과 분석 성공 로그.
- `setup-fixed-full.log`: 새 폴더에서 수정 setup.sh 전체 성공 로그.
- `setup.sh`, `setup.original.sh`, `03-matplotlib-compat.patch`: 실행 스크립트와 호환 수정.
