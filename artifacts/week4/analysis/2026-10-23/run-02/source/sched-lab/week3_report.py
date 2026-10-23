from pathlib import Path
import csv,json,statistics,shutil,hashlib,subprocess,argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

root=Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
run=root/'artifacts/week3-2026-10-12/run-03'
report=root/'reports/week3';fig=report/'figures';fig.mkdir(parents=True,exist_ok=True)
ap=argparse.ArgumentParser(description='Regenerate week 3 figures; optional document drafts never overwrite the edited report')
ap.add_argument('--write-record-drafts',action='store_true')
opts=ap.parse_args()
def write_draft(name,text):
    if opts.write_record_drafts:
        target=report/'records/drafts'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text)
def read(p):return list(csv.DictReader(p.open()))
rs=read(run/'results.csv');fixed=read(run/'analysis/fixed_ratio_summary.csv');conditions=read(run/'analysis/condition_summary.csv')
equiv=read(run/'trace-equivalence/summary.csv')
prop=font_manager.FontProperties(fname='/mnt/c/Windows/Fonts/malgun.ttf')
font_manager.fontManager.addfont(prop.get_file());plt.rcParams.update({'font.family':prop.get_name(),'axes.unicode_minus':False,'font.size':10,'figure.dpi':160,'svg.fonttype':'none'})
colors={'dominating':'#316a9d','competing':'#cd874b','degrade':'#559575'}
labels={'dominating':'dominating (경로 0이 느림)','competing':'competing (속도·지연 상충)','degrade':'degrade (경로 1 속도 열화)'}
f,axes=plt.subplots(1,3,figsize=(11.5,3.6),sharey=True)
for ax,sc in zip(axes,colors):
    for j,target in enumerate((.1,.3,.5)):
        ys=[float(x['error_percentage_points']) for x in fixed if x['scenario']==sc and float(x['share0'])==target]
        limit=.05*min(target,1-target)*100
        ax.fill_between([j-.3,j+.3],[-limit,-limit],[limit,limit],color='#dcece4',alpha=.9)
        ax.scatter([j-.07,j,j+.07],ys,color=colors[sc],s=32,zorder=3)
        ax.text(j,.22,f'{min(ys):.3f}~{max(ys):.3f}',ha='center',fontsize=8)
    ax.axhline(0,color='#64748b',lw=.8);ax.set_xticks(range(3),['10 / 90','30 / 70','50 / 50'])
    ax.set_xlabel('목표 경로 0 / 경로 1 분배 (%)');ax.set_title(labels[sc],fontsize=10);ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('실제 경로 0 비중 - 목표 비중 (%p)');axes[0].set_ylim(-2.7,2.7)
f.suptitle('고정 비율 27회: 모든 실행이 허용 분배 오차 이내',fontsize=14,fontweight='bold')
f.text(.5,.005,'녹색: 양 경로에 엄격 상대 오차 5%를 적용한 범위 · 점: seed 1~3 · cwnd 제약 결정만 제외',ha='center',fontsize=9)
f.tight_layout(rect=(0,.06,1,.91));f.savefig(fig/'fixed_ratio_validation.png',bbox_inches='tight');f.savefig(fig/'fixed_ratio_validation.svg',bbox_inches='tight');plt.close(f)

f,axes=plt.subplots(1,2,figsize=(10.7,3.8))
for seed in (1,2,3):
    data=sorted([x for x in fixed if x['scenario']=='dominating' and int(x['seed'])==seed],key=lambda x:float(x['share0']))
    axes[0].plot([float(x['share0'])*100 for x in data],[float(x['actual_gap_mean_s'])*1000 for x in data],marker='o',lw=1.2,label=f'seed {seed}')
    axes[1].plot([float(x['share0'])*100 for x in data],[int(x['reorder_waiting_max_bytes'])/1048576 for x in data],marker='o',lw=1.2,label=f'seed {seed}')
axes[0].set_title('두 경로 배치의 마지막 패킷이 도착한 시간 차이');axes[0].set_ylabel('실제 도착 시차 평균 (ms)');axes[0].legend(fontsize=8)
axes[1].set_title('먼저 도착해 전달 순서를 기다린 데이터');axes[1].set_ylabel('수신측 대기 데이터 최대량 (MiB)')
for ax in axes:ax.set_xlabel('느린 경로 0에 지정한 전송 비중 (%)');ax.set_xticks([10,30,50]);ax.grid(alpha=.18)
f.suptitle('dominating: 느린 경로 비중 10% → 30% → 50%에서 도착 시차 증가',fontsize=12,fontweight='bold')
f.text(.5,.005,'시차: 같은 결정에서 보낸 원본 패킷의 경로별 마지막 수신 시각 차이 · 유실·연결 불명확 배치는 별도 기록',ha='center',fontsize=8)
f.tight_layout(rect=(0,.06,1,.91));f.savefig(fig/'arrival_and_reordering.png',bbox_inches='tight');f.savefig(fig/'arrival_and_reordering.svg',bbox_inches='tight');plt.close(f)

rows=[]
for c in conditions:
    p=float(c['target_share0']);actual=f"{float(c['actual_share0_min'])*100:.3f}~{float(c['actual_share0_max'])*100:.3f}%"
    rows.append(f"| {c['scenario']} | {p*100:.0f}/{(1-p)*100:.0f}% | {actual} | 약 {float(c['eligible_byte_fraction_min'])*100:.1f}% | {c['allocation_pass']}/{c['runs']} | {c['completed']}/{c['runs']} |")
table='\n'.join(rows)
max_err=max(max(float(x['relative_error_p0']),float(x['relative_error_p1'])) for x in fixed)*100
min_cover=min(float(x['eligible_byte_fraction']) for x in fixed)*100
rx_rows=sum(int(x['receiver_rx_frame_rows']) for x in read(run/'analysis/run_metrics.csv'))
obs_rows=sum(int(x['obs_rows_disabled']) for x in equiv)
arrivals=sum(int(x['arrival_valid_batches']) for x in fixed)
censored=sum(int(x['arrival_censored_batches']) for x in fixed)
unmatched=sum(int(x['arrival_unmatched_batches'])+int(x['arrival_ambiguous_batches']) for x in fixed)
gaps=[float(c['mean_actual_batch_gap_s'])*1000 for c in conditions if c['scenario']=='dominating']
gaps_str=' → '.join(f'{v:.2f}ms' for v in gaps)
text=f'''## 1. 3주차 작업 내용

### 1-1. 신규 스케줄러 연결·바이트 분배 변환 테스트 (기본 동작 유지·단위 검증 통과)

| 확인 항목 | 검증 내용 | 결과 |
|---|---|---|
| 스케줄러 ID 7 연결 | 명령 인자 → 속성 → 선택 분기 → MinRTT-multi 호출 | 기본 9회가 공식 기준값과 일치 |
| 분배 변환 `BytesToRatio` | 경로별 바이트 요청을 순차 잔량 기준 비율로 변환 | 실제 버퍼 분할 30/70·10/90·50/50 확인 |
| 경계값·관찰 정확성 | 빈 버퍼·MSS(패킷 단위) 미만·초과 요청·중복·순서 밖 FIN | 단위 검증 4개 모두 통과 |

- **구현 범위**
  - 실행 옵션
    - `SchedulerType=7` 연결, 이후 알고리즘에 사용할 `NewKappa`·`NewBeta`·`NewSmax` 인자와 설정 로그 추가
  - **결과**
    - **ID 7의 기본 동작은 MinRTT-multi와 동일. 고정 비율은 별도 옵션으로 실행**

### 1-2. 기존 스케줄러·옵션형 계측 비교 테스트 (공식 기준값과 모두 일치)

| 테스트 | 측정 범위 | 결과 |
|---|---|---|
| 기존 스케줄러 보존 | ID 0~6·3시나리오·seed 1, ID 6의 추가 seed 2~3 | 27/27회 공식 기준값과 일치 |
| ID 7 초기 동작 | 계측 비활성·활성 각각 3시나리오·seed 1~3 | 각각 9/9회 ID 6 기준값과 일치 |
| 계측 활성화 전후 송수신 이벤트 | 기본 3시나리오, 고정 비율 3개, 열화·회복 구간 | 7쌍·14회 실행, 이벤트 {obs_rows:,}행 일치 |

- **수행 조건**
  - 유지 설정
    - 목표 5,242,880B, OLIA 혼잡 제어, 설정 손실률 0, 완료 후 대기 250ms, 제한 시뮬레이션 시각 60초
  - 비교 기준
    - 2주차 공식 동결 데이터에서 같은 시나리오·스케줄러·seed의 수신량·전송 시간 대조
  - **결과**
    - **기준 대조 45/45건 일치. 관찰 옵션을 껐을 때와 켰을 때 송수신·손실·상태 이벤트 동일**

### 1-3. 고정 비율 송신 테스트 (27/27회 분배 오차 범위 충족)

![고정 비율의 실제 데이터 분배 오차](figures/fixed_ratio_validation.png)

| 시나리오 | 목표 경로 0/1 비중 | 실제 경로 0 비중 | 최소 포함 바이트 비중(반올림) | 분배 통과 | 완료·전체 수신 |
|---|---|---|---|---|---|
{table}

- **실제 분배 확인**
  - 방법
    - `week3_validate.py`와 고정 비율 ID 7로 3시나리오 × 3비율 × seed 1~3 = 27회 실행
    - cwnd(수신 확인 없이 보낼 수 있는 양) 부족 결정만 제외하고, 나머지 송신 결정의 실제 STREAM 프레임 바이트를 경로별 합산
  - **결과**
    - **양 경로 상대 오차 최대 {max_err:.3f}%로 허용 5% 이내. 27/27회 목표 데이터 전체 수신**
    - **제외 후 최소 포함 비중 약 {min_cover:.1f}%. 열화·50/50에서는 창 축소 구간이 많아 포함 비중 감소**

### 1-4. 도착 시차·수신 대기량 기록 테스트 (느린 경로 비중에 따른 변화 확인)

![느린 경로 비중별 도착 시차와 수신 대기량](figures/arrival_and_reordering.png)

- **두 경로 도착 시간 차이 확인**
  - 측정 대상
    - `dominating`의 느린 경로 0: 5~5.5Mbps·50~55ms, 빠른 경로 1: 10~11Mbps·10~11ms
    - 같은 결정에서 보낸 패킷을 송신·수신 기록으로 연결해 경로별 마지막 패킷 수신 시각 대조
  - **결과**
    - **느린 경로 비중 10% → 30% → 50%에서 평균 시차 {gaps_str}. 같은 seed 3개에서도 증가**
    - **고정 비율의 실제 도착 시차 배치 {arrivals:,}개 기록. 원본 패킷 미수신 배치 {censored}개·송신 연결 불명확 배치 {unmatched}개 별도 보존**
- **옵션형 계측**
  - 기록 내용
    - 결정 시각·분배 비율·전송 한도·RTT(왕복 시간)·미확인 송신량·버퍼 잔량
    - 도착 예상·실제 시차·누적 시차, 수신측 순서 대기량·대기 시간, 경로별 송신·재전송·누적 사용량
  - **결과**
    - **수신 프레임 {rx_rows:,}행이 재정렬 관찰 기록과 일치. 계측은 기본 비활성, 실행별 CSV 3종 분리**

## 2. 문제 상황 - 고정 비율 진단에서 전송 창 부족 구간 처리

- **고정 배치 송신 (지정한 경로별 분배량을 함께 보낼 수 있을 때 송신)**
  - 최초 문제 상황
    - ACK(수신 확인)마다 경로별 여유만큼 보내면 대부분이 전송 한도 제약 구간. 최초 27회 중 25회 분배 오차 초과
  - 수정
    - 고정 비율 옵션에서만 경로별 바이트를 미리 확정하고 양 경로의 여유 확보 후 송신
    - 초기 전송 한도가 목표 배치보다 작을 때는 부분 송신으로 전송 창 확대
  - **결과**
    - **3개 고정 비율·3시나리오·seed 1~3 모두 분배 기준 충족**
- **창 축소 시 부분 송신 허용 (막힌 경로가 정상 경로까지 멈추는 현상 방지)**
  - 최초 문제 상황
    - 대기 방식 적용 후 `degrade`·50/50의 3회 미완료. 한 경로의 전송 창이 줄어 기존 미확인 데이터가 한도를 초과
  - 수정
    - 미확인 송신량이 줄어든 전송 창보다 클 때는 정상 경로의 제한된 부분 송신 허용
  - **결과**
    - **해당 3회 모두 완료·전체 수신. 최종 기본 검증 72/72회와 계측 대조 14/14회 완료·전체 수신**
    - **기존 ID 0~6·공통 QUIC 재전송 로직·2주차 동결 데이터 유지**

## 3. 게이트 3 검증 결과

- **게이트 3 (고정 비율대로 송신하고 두 경로의 도착 시차를 확인)**
  - 분배 기준
    - cwnd 제약 구간 제외 후 30/70·10/90·50/50의 양 경로 상대 오차 5% 이내
  - 확인 자료
    - 실제 송신·결정 로그·도착 시차·수신 대기량 CSV와 단위 검증 기록 보존
  - **결과**
    - **분배·로그·도착 시차 항목 충족. 단계별 독립 검토와 원시 데이터 재계산 일치**

## 4. 다음 작업

- **4주차 계획 (확장 시나리오와 재현·인계 자료 준비)**
  - 테스트 대상
    - 경로 열화·긴 전송·4경로 동작 한계와 반복 실행 안정성
  - 산출물
    - 재현 패키지·3~4쪽 중간 보고서

## 5. 참고 자료

- **3주차 구현 브랜치**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/lab/week3-scheduler-20261012

- 작업 브랜치 `lab/week3-scheduler-20261012`의 코드·측정 데이터·보고 자료

- **최종 72회 실행의 완료·수신량·전송 시간**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/artifacts/week3-2026-10-12/run-03/results.csv
- **고정 비율 27회 실제 분배·완료·도착 시차·수신 대기량**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/artifacts/week3-2026-10-12/run-03/analysis/fixed_ratio_summary.csv
- **도착 시차의 배치별 원시 연결·누적값**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/artifacts/week3-2026-10-12/run-03/analysis/decision_metrics.csv
- **계측 활성화 전후 송수신 이벤트 대조**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/artifacts/week3-2026-10-12/run-03/trace-equivalence/summary.csv
- **계측 로그의 항목·단위·계산 방법**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/reports/week3/records/%EA%B3%84%EC%B8%A1%20%EB%A1%9C%EA%B7%B8%20%ED%98%95%EC%8B%9D.md
- **조건별 실행 명령·미통과 시도·수정 검증 기록**
  - https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/lab/week3-scheduler-20261012/reports/week3/records/3%EC%A3%BC%EC%B0%A8%20%EC%83%81%EC%84%B8%20%EC%8B%A4%ED%97%98%20%EA%B8%B0%EB%A1%9D.md
'''
write_draft('3주차 진행상황.md',text)
log='''## 계측 로그 형식

- **활성화·생성 위치**
  - 실행 옵션
    - `--LabLogPrefix=<실행 폴더>/trace`. 생략하면 새 계측 비활성
  - 결과 파일
    - `trace-decisions.csv`·`trace-packets.csv`·`trace-reorder.csv`, 실행별 분리

| 파일 | 주요 항목 | 의미·단위 |
|---|---|---|
| decisions | decision_id, time_s, node, connection, path, ratio | 결정 ID는 연결 내 번호. 비교 키는 node·connection·decision_id, 시각은 시뮬레이션 초 |
| decisions | backlog, nominal requested/quota/demand, requested, actual | STREAM 헤더 포함 프레임 B. 명목 요청·MSS 내림 계획·실제 송신 구분, tail만 1패킷 예외. ACK·QUIC·IP 헤더 제외 |
| decisions | cwnd, inflight, cwnd_room, flow_room, available_window | 전송 한도·미확인 전송량·cwnd 여유·흐름 제어 여유 B. available_window는 둘의 제한을 함께 반영 |
| decisions | last_rtt_s, rtt_valid, predicted_requested_end_s | 마지막 왕복 시간 s. 예상 도착은 RTT/2 + 요청 B×RTT/cwnd. 유효 RTT가 없으면 −1 |
| decisions | cwnd_limited, flow_limited, fixed_diagnostic_mode, stop_reason | 명목 demand가 송신 전 여유를 넘는지 기록. 모드는 off/bootstrap/wait/batch/recovery |
| packets | time_s, node, direction, path, packet_number, stream, offset, payload_bytes, fin | 애플리케이션 STREAM payload B만 관찰. stream 0 핸드셰이크 제외, FIN은 종료 표시 |
| reorder | expected_offset_before/after, frame_offset, frame_payload_bytes | 현재 프레임 처리 전후 연속 전달 위치와 받은 프레임 구간 B |
| reorder | stored_payload_bytes, waiting_payload_bytes | 물리 저장 합계와 전달 위치 뒤 고유 미전달 구간의 합집합 B. 중복·이미 전달한 구간을 대기량에서 제외 |
| reorder | episode_id, episode_state, episode_elapsed_s, frame_status | 대기 구간의 start/open/end/idle·지속 s. 종료되지 않은 구간은 검열로 남김. processed는 처리 시도, duplicate는 중복 |

- **분배·도착 시차·재전송 계산**
  - 분배
    - 한 결정에서 어느 경로라도 명목 demand가 cwnd 여유를 넘으면 결정 전체 제외. 그 밖의 tail·흐름 제어·송신 실패는 추가 제외하지 않음
    - 실행별 경로 actual B 합계로 비중 계산. 허용 오차는 양 경로 각각 상대 5%, %p와 포함 바이트 비중도 보존
    - 게이트는 SendPendingData의 비제약 송신 결정만 대상으로 함. 창 축소의 부분 송신·직접 재전송을 포함한 전체 연결 payload 비율은 path_usage에 따로 보존
  - 실제 도착 시차
    - 송신·첫 수신을 path·packet_number·stream·offset·payload_bytes로 연결. 시각은 ns 정규화
    - 동일 결정 배치의 경로별 마지막 원본 패킷 수신 시각 차이. 원본 유실·같은 시각 다른 결정·송신 수 불일치는 따로 기록
    - 결정별 예상 시차·실제 signed/absolute 시차·유효 absolute 시차 표본 합계를 `analysis/decision_metrics.csv`에 저장. 피드백 제어에 사용하지 않음
    - 초기 RTT가 없는 유효 실제 배치 27개는 예상값에서 제외. 예상 평균 비교에는 predicted_valid_batches와 같은 배치의 실제 평균을 함께 사용
  - 경로 사용량
    - 송신 STREAM offset 구간을 경로 간 합집합으로 대조해 최초 송신과 중복 송신 B 구분
    - `analysis/path_usage.csv`에 경로별 최초·재전송·총 송신 B 누적. 프레임 분배 B와 payload B를 혼합하지 않음

- **재현 파일**
  - `protocol.json`·`execution-manifest.json`·각 실행 `command.json`에 설정·명령·커밋·소스/바이너리 SHA-256 보존
  - 실험 소스는 각 실행 묶음의 `source/`, 집계에 사용한 소스는 `analysis/source/`에 별도 보존
'''
write_draft('계측 로그 형식.md',log)
detail='''## 1. 3주차 요구사항·실험 범위

- 원본 요청서 D11~D15: ID 7 초기 MinRTT-multi 동작·파라미터·BytesToRatio·옵션형 계측·3개 고정 비율 검증
- 주차 범위에서 자동 분배 판단·피드백 제어는 구현하지 않음. 고정 비율의 배치 송신은 슬롯 진단 옵션
- 비교 기준은 2주차 공식 630회 동결 데이터. 신규 ID 7 고정 모드에는 제공 기준값 없음
- 기본 프로토콜은 72회: 기존 ID 0~6 21회 + ID 6 추가 6회 + ID 7 기본 9회 + 기본 계측 9회 + 고정 27회
- 3시나리오·seed 1~3, Size=5242880·OLIA·LossRate=0·CompletionGraceMs=250·SimEnd=60
- 양 경로에 엄격 상대오차 5% 적용. 제외는 한 결정의 명목 demand > cwnd room뿐. 실제 바이트를 가중 합산

## 2. 변경 전후 실행 기록

| 실행 묶음 | 고정 분배 동작 | 완료·전체 수신 | 기준 대조 | 고정 분배 |
|---|---|---|---|---|
| run-01 | 매 ACK의 경로별 여유만큼 부분 송신 | 72/72 | 45/45 일치 | 2/27 수치 충족, 포함 B 0.04~1.56%로 불충분 |
| run-02 | 절대 목표량 snapshot·양 경로 여유 대기·초기 probe | 69/72 | 45/45 일치 | 27/27 충족, degrade50/50 3회 미완료 |
| run-03 | run-02 + 창 축소 중 정상 경로 부분 송신 허용 | 72/72 | 45/45 일치 | 27/27 충족 |

- **run-01 분배 미통과 원인·수정**
  - 원인
    - 매 ACK마다 일부만 채워 송신해 거의 모든 배치가 cwnd 제약. tail 등 소량의 비제약 구간으로 집계
  - 수정
    - 고정 옵션에만 10MSS 목표 바이트 snapshot·대기. 초기 total cwnd < 목표량일 때만 부분 송신으로 창 성장
  - **결과**
    - **run-02 분배 27/27 충족. 원시 run-01과 당시 source/·protocol.json 보존**
- **run-02 진행 정체 원인·수정**
  - 원인
    - degrade50/50 seed1~3에서 path1 cwnd2920B보다 inflight139~169KB가 커 room0. path0는 비어 있지만 양 경로 WAIT
  - 수정
    - 수요 있는 경로의 inflight > total cwnd일 때 고정 진단만 recovery 부분 송신. 명목 목표 비율과 cwnd 제외 표시 유지
  - **결과**
    - **run-03 해당 3회 전체 수신, 완료 시간 7.1481~7.8798초. 분배·기존 기준 대조 유지**
- run-02 protocol의 fixed_mode 문구는 이전 설명이 남아 있음. 원본을 변경하지 않고 `PROTOCOL_AMENDMENT.json`에 실제 WAIT/bootstrap/절대 quota 적용을 정정. run-03은 사전 protocol에 recovery까지 기록

## 3. 계측 검증·집계 정의

- 기본 ID 7 계측 전후 9회 각각 ID 6과 RESULT 일치. 예약 인자 변경 한 실행도 동일
- 별도 7쌍·14회는 기존 Observe를 양쪽에 유지하고 LabLogPrefix만 변경. 전체 OBS 이벤트와 RESULT 문자열 일치
- Tx/Rx → LabReorder 연결은 시각 ns·stream·offset·길이 Counter로 대조. 누락·초과 0
- 도착 배치는 unique 결정 시각 및 실제 Tx 패킷 수 확인 후 연결. 같은 시각 직접 재전송이 섞여 송신 수가 다르면 연결 불명확으로 보존
- 물리 저장량/고유 미전달량을 구분, FIN·중복·부분 prefix 단위 검증. episode end는 이후 idle에 덮이지 않도록 집계
- 전체 Tx payload 비중과 게이트의 비제약 SendPendingData 프레임 비중을 구분. degrade50/50에서 전체 Tx payload의 path0는62.191~63.597%, 최초 송신 payload는68.158~68.434%지만 비제약 프레임 비중은50.054~50.055%
- 실제 시차는 원본 패킷 모두 수신된 배치에서 계산. degrade50/50 유효86/87/88배치, 미수신45/45/43배치, 연결 불명확1/2/2배치. 유효64.93~66.17%의 조건부 평균·p95로 보존
- 경로별 재전송은 payload offset 구간 중복, 전체 송신은 payload 합산. 실제 분배는 serialized STREAM frame 단위
- 도착 예상 모델과 실제 수신 시각을 구분. same-state 예상 시차 검산은 보조 수식 확인이며 실제 도착 방향 검증을 대체하지 않음
- dominating: path0가 속도·지연 모두 불리. seed별 10→30→50%에서 실제 평균 absolute gap 증가
- 조건별 시차 평균은 각 seed의 유효 배치 평균을 먼저 구한 뒤 seed3개 평균. 초기 RTT 없는 실제 배치는 예상 평균과 직접 비교하지 않고 대응 배치 통계를 별도 기록
- competing: 속도·지연 상충, degrade: 도중 path1 열화. 이들의 비단조 시차도 그대로 보존

## 4. 보존·재현

- 코드 변경: mp-quic-scheduler.h/.cc·quic-socket-base.h/.cc·quic-stream-base.h/.cc·quic-stream-rx-buffer.h/.cc·quic-l5-protocol.cc·scratch/mpquic-sched-lab.cc·src/quic/wscript·mp-quic-scheduler-test.cc
- 도구: run_sweep.py ID7 이름 추가·week3_validate.py·week3_analyze.py·week3_trace_equivalence.py·week3_report.py
- 실험 데이터: artifacts/week3-2026-10-12/run-01~03. 각 명령·소스·해시·결과·로그 보존
- 구현 패치: artifacts/week3-2026-10-12/patches/week3-implementation.patch·week3-instrumentation.patch
- 보고 자료: reports/week3/3주차 진행상황.md·계측 로그 형식.md·figures/
- 공식 기준값 artifacts/week2-completion-2026-10-08/run-01/은 변경하지 않음
'''
write_draft('3주차 상세 실험 기록.md',detail)
amend=dict(purpose='Correct stale run-02 fixed_mode prose without overwriting the original protocol',
    actual='ID7 opt-in absolute quota snapshot; bootstrap when any total cwnd is below raw demand; otherwise both quotas must fit available windows; no recovery bypass in run-02',
    evidence='run-02/source/src/quic/model/quic-socket-base.cc and source hashes',created_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat())
write_draft('run-02-PROTOCOL_AMENDMENT.json',json.dumps(amend,indent=2))
# Edited documents are exported only by render_weekly_report.py --handoff.
print(json.dumps(dict(max_relative_error_percent=max_err,min_coverage_percent=min_cover,receiver_rows=rx_rows,obs_rows=obs_rows,arrival_batches=arrivals,censored=censored,unmatched=unmatched,report=str(report)),indent=2))
