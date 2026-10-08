#!/usr/bin/env python3
"""Generate the diagnosis tables and reports from preserved experiment outputs."""
import hashlib
import importlib.util
import json
import platform
import subprocess
from pathlib import Path
from urllib.parse import quote

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/week2-incomplete-2026-10-07'
REPORT = ROOT / 'reports/week2'
BRANCH = 'fix/#9-week2-incomplete-diagnosis'
URL = 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/'
def link(path, tree=False):
    return URL + ('tree/' if tree else 'blob/') + quote(BRANCH, safe='/') + '/' + quote(path, safe='/')
def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def read(folder):
    return pd.read_csv(ART / folder / 'results.csv').set_index(['scenario', 'scheduler', 'seed']).sort_index()

def main():
    analysis = ART / 'analysis'
    analysis.mkdir(exist_ok=True)
    frozen = ROOT / 'artifacts/week2-2026-10-02/run-01'
    before = pd.read_csv(frozen / 'baseline.csv').set_index(['scenario', 'scheduler', 'seed']).sort_index()
    after = read('14-fin-preservation-full-630')
    initial_fixed = read('08-combined-full-630')
    observed = read('13-final-observe-62')
    grace = read('09-completion-grace-250ms')
    metrics = ['size', 'fct_s', 'fct95_s', 'rx_app', 'rx_p0', 'rx_p1', 'delay_p0_ms', 'delay_p1_ms', 'done']
    assert len(before) == len(after) == 630 and before.index.equals(after.index)
    assert not before.index.duplicated().any() and not after.index.duplicated().any()
    assert after[metrics].equals(initial_fixed[metrics])
    assert observed[metrics].equals(after.loc[observed.index, metrics])
    assert len(observed) == 62 and observed.done.sum() == 62 and observed.rx_app.eq(observed['size']).all()
    assert len(grace) == 9 and grace.rx_app.eq(grace['size']).all()
    assert grace.fct_s.equals(after.loc[grace.index, 'fct_s'])
    hashes = []
    for line in (frozen / 'SHA256SUMS').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        actual = hashlib.sha256((frozen / relative).read_bytes()).hexdigest()
        hashes.append({'path': relative, 'expected': expected, 'actual': actual, 'unchanged': expected == actual})
    assert all(h['unchanged'] for h in hashes)
    dump(analysis / 'validation.json', {'rows': 630, 'keys_equal': True, 'duplicates': 0,
         'original_done': int(before.done.sum()), 'fixed_done': int(after.done.sum()),
         'original_full': int(before.rx_app.eq(before['size']).sum()), 'fixed_full': int(after.rx_app.eq(after['size']).sum()),
         'original_incomplete_recovered': 62, 'fin_final_full630_metric_differences': 0, 'observer_cases': 62, 'observer_metric_differences': 0,
         'grace_diagnostic_cases': 9, 'grace_full_received': 9, 'grace_fct_differences': 0,
         'frozen_hash_checks': hashes})
    comp = before[['name', 'done', 'rx_app', 'fct_s']].join(after[['done', 'rx_app', 'fct_s']], lsuffix='_original', rsuffix='_fixed')
    comp['provided_reference'] = np.where(comp.index.get_level_values('seed') <= 10, 'seed 1-10: original matches provided CSV', 'seed 11-30: no provided reference')
    comp['original_full'] = comp.rx_app_original.eq(5242880)
    comp['fixed_full'] = comp.rx_app_fixed.eq(5242880)
    comp['common_done_delta_s'] = (comp.fct_s_fixed - comp.fct_s_original).where(comp.done_original.eq(1) & comp.done_fixed.eq(1)).round(4)
    comp.to_csv(analysis / 'all630_before_after.csv')
    old_incomplete = comp[comp.done_original.eq(0)].copy()
    stream = read('05-stream-rx-only')
    old_incomplete['cause'] = np.where(stream.loc[old_incomplete.index, 'done'].eq(1), 'B: stale delivered stream data', 'C: loss detection skips ACK-only largest packet')
    old_incomplete.to_csv(analysis / 'incomplete62_causes.csv')
    shorts = comp[~comp.fixed_full].join(grace[['rx_app', 'fct_s']].rename(columns={'rx_app': 'rx_app_grace250ms', 'fct_s': 'fct_s_grace250ms'}))
    shorts.to_csv(analysis / 'remaining9_cutoff.csv')
    spec = importlib.util.spec_from_file_location('labstats', ROOT / 'sched-lab/stats.py')
    stats = importlib.util.module_from_spec(spec); spec.loader.exec_module(stats)
    summary = stats.summarize(after.reset_index()); summary.to_csv(analysis / 'fixed_summary21.csv', index=False)
    pairs, observations = stats.paired_comparisons(after.reset_index())
    pairs.to_csv(analysis / 'fixed_scheduler_pairs63.csv', index=False)
    observations.to_csv(analysis / 'fixed_scheduler_pair_observations.csv', index=False)
    summary[summary.scenario.eq('dominating')].to_csv(analysis / 'fixed_dominating_ci.csv', index=False)
    dump(analysis / 'environment.json', {'os': platform.platform(), 'python': platform.python_version(),
         'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
         'cpu': subprocess.check_output(['lscpu'], text=True), 'total_full630_wall_s': float(after.wall_s.sum()),
         'mean_run_wall_s': float(after.wall_s.mean()), 'max_run_wall_s': float(after.wall_s.max()),
         'stack': 'provided patches 01+02 plus candidates A/B/C', 'completion_grace_ms': 10,
         'reference_status': 'separate candidate; frozen baseline is preserved'})

    groups = []
    names = {0:'RR',1:'MinRTT',2:'BLEST',3:'ECF',4:'Peekaboo',5:'EAT',6:'MinRTT-multi'}
    for (sc, sid), g in comp.groupby(level=[0,1]):
        groups.append({'scenario':sc, 'scheduler':sid, 'name':names[sid], 'original_done':int(g.done_original.sum()),
                       'original_full':int(g.original_full.sum()), 'fixed_done':int(g.done_fixed.sum()), 'fixed_full':int(g.fixed_full.sum())})
    pd.DataFrame(groups).to_csv(analysis/'counts21.csv',index=False)
    affected = [g for g in groups if g['original_done'] < 30]
    fig, ax = plt.subplots(figsize=(10,5.2))
    y=np.arange(len(affected)); ax.barh(y+.16,[g['original_done'] for g in affected],height=.30,color='#8c9bb6',label='Original: completed')
    ax.barh(y-.16,[g['fixed_done'] for g in affected],height=.30,color='#24896c',label='Fixed: completed')
    for i,g in enumerate(affected):
        ax.text(g['original_done']+.3,i+.16,str(g['original_done'])+'/30',va='center',fontsize=10)
        ax.text(30.3,i-.16,'30/30',va='center',fontsize=10)
    ax.set_yticks(y,[g['scenario']+' / '+g['name'] for g in affected]);ax.invert_yaxis()
    ax.set_xlim(0,35);ax.set_xticks([0,10,20,30]);ax.set_xlabel('Runs (same scenario / scheduler / seeds 1-30)')
    ax.set_title('Recovery of 62 originally incomplete runs', pad=35);ax.legend(loc='lower left', bbox_to_anchor=(0, 1.02), ncol=2, frameon=False, fontsize=9);ax.grid(axis='x',alpha=.15)
    ax.spines[['top','right']].set_visible(False);fig.tight_layout()
    figures=REPORT/'figures'; figures.mkdir(exist_ok=True)
    fig.savefig(figures/'incomplete_recovery.png',dpi=170)
    fig.savefig(figures/'incomplete_recovery.svg');plt.close(fig)
    table='| 시나리오 | 스케줄러 | 원본 완료 | 원본 전체 수신 | 수정 완료 | 수정 전체 수신 |\n|---|---|---|---|---|---|\n'
    for g in groups:
        table+=f"| {g['scenario']} | {g['name']} | {g['original_done']}/30 | {g['original_full']}/30 | {g['fixed_done']}/30 | {g['fixed_full']}/30 |\n"
    detailed='''## 1. 2주차 미완료 원인 분석

### 1-1. 조사 대상·제공 기준 대조 (미완료 62회, 실행 오류 0회)

- 조사 대상: `mpquic-sched-lab.cc`의 3시나리오 × 7스케줄러 × seed 1~30, 총 630회 중 미완료 62회
- 원본 완료 처리 568/630, 목표 5,242,880B 전체 수신 533/630. 완료 처리는 목표보다 3,000B 부족해도 인정
- 제공 기준 seed 1~10의 210회: 완료 191회·전체 수신 181회, 미완료 19회의 조합·seed·수신량도 동일
- 추가 seed 11~30의 420회: 완료 377회·전체 수신 352회, 미완료 43회. 해당 범위의 제공 기준 없음
- 데이터 전송 시작: 시뮬레이션 시각 1초. 종료: 60초 또는 완료 처리 10ms 후. 미완료는 코드가 자동 기록
- 목표의 95%까지 받은 미완료 54회, 그 이전에 정체한 미완료 8회를 나눠 조사

## 2. 원인별 변경·대조 테스트

### 2-1. 통제 실험 (종료 시각 60초 → 300초 변경 후 테스트: 62회 수신량 동일)

- **최초 문제 상황: 종료 시각 60초까지 완료 기준 미충족**
  - 조사 대상: 원본 미완료 62회
- **문제 원인 추정: 전송을 끝내기 위한 시간이 부족**
  - 링크·스케줄러·seed·목표량·혼잡 제어를 유지하고 종료 시각만 연장
- **문제 원인 검증: 300초까지 대기해도 수신량 변화 없음**
  - 완료 0/62. 원본 60초의 애플리케이션 수신량과 62회 모두 동일
- **조치: 제한 시간 연장 대신 수신 버퍼·손실 복구 처리 조사**
  - 실제 데이터 위치와 패킷 송수신·ACK(수신 확인) 번호를 추적

### 2-2. 소켓 읽기 바이트 차감 수정 A (별도 결함 수정, 미완료 62회에는 효과 없음)

- **최초 문제 상황: 읽기 버퍼에서 지운 항목을 다시 참조**
  - `QuicSocketRxBuffer::Extract()`의 삭제 후 참조 및 남은 읽기 크기 계산 오류 확인
- **문제 원인 추정: 읽기 단계에서 실제 바이트가 누락**
  - 서로 다른 크기의 데이터 13B·7B·31B를 넣고 전체 읽기·제한된 읽기 검사
- **문제 원인 검증: 이 함수만 수정해도 원본 미완료 결과는 동일**
  - 62회 완료 0/62, 수신량 변화 0회. 별도 회귀 테스트의 바이트 수·순서 오류는 수정 후 통과
- **조치: 삭제 전 바이트 차감·부분 읽기 적용**
  - 수신 버퍼의 바이트 보존 결함을 함께 수정. 62회 정체의 직접 원인과 구분

### 2-3. 이미 전달한 스트림 데이터의 중복·겹침 처리 수정 B (54회 전체 수신 회복)

- **최초 문제 상황: 수신 위치는 진행했지만 애플리케이션에 전달한 바이트는 부족**
  - 마지막 구간에서 정체한 54회에 이미 전달한 위치의 중복 프레임 관찰
- **문제 원인 추정: 과거 중복 데이터가 순서 대기 버퍼 앞에 남음**
  - 새 연속 데이터를 계산해도 앞의 중복 데이터를 추출하거나 추출에 실패. 계산한 수신 위치만 증가
- **문제 원인 검증: 스트림 수신 처리만 수정 후 동일 62회 테스트**
  - 완료·전체 수신 54/62. 앞에서 정체한 8회는 그대로
- **조치: 이미 전달한 범위 제외·일부 겹친 프레임의 새 바이트만 처리**
  - `QuicStreamBase::Recv()`에서 실제 추출한 바이트 수만 수신 위치에 반영
- **조치 후 검증 결과: 54회 목표 5,242,880B 정확 수신**
  - 회귀 테스트: 과거 중복·부분 겹침·대기 중 동일 프레임·역순 수신의 실제 바이트 순서까지 확인

### 2-4. ACK 번호를 이용한 손실 감지 수정 C (나머지 8회 전체 수신 회복)

- **최초 문제 상황: 특정 바이트 위치의 데이터가 누락되고 재전송되지 않음**
  - dominating/BLEST 4회·ECF 2회, competing/BLEST 2회
- **문제 원인 추정: 네트워크에서 버린 데이터의 손실 판단이 생략**
  - 가장 큰 ACK 번호가 데이터 전송 목록에 없으면 이전 미확인 데이터의 손실 검사도 생략
- **문제 원인 검증: 패킷 폐기와 재전송 누락을 독립 추적**
  - 8회 모두 기본 FqCoDel 큐가 지연 목표 초과로 첫 IPv4 조각을 폐기. 나머지 조각만 도착해 패킷 재조립 실패
  - 설정 손실률 0은 별도 오류 모델의 값. 큐의 지연 제어 폐기는 실제 로그로 확인
  - 손실 감지만 수정해 8/8 완료·전체 수신. 7회는 누락 위치 재전송·수신 직접 확인
  - competing/BLEST/seed 12는 앞선 손실 처리 후 전송 시각이 바뀌어 후속 누락 회피
- **조치: 미확인 패킷과 가장 큰 ACK 번호의 차이로 직접 손실 판단**
  - `QuicSocketTxBuffer::OnAckUpdate()` 수정. 기존 패킷 번호 차이 임계값 3·혼잡 제어 유지
- **조치 후 검증 결과: 8회 목표량 전체 수신, 손실 감지 회귀 테스트 통과**
  - ACK 전용 패킷의 번호가 데이터 목록에 없을 때도 오래된 누락 데이터를 재전송

## 3. 수정 후 630회 전체 검증

### 3-1. 동일 seed·동일 링크 조건 테스트 (완료 630/630, 전체 수신 621/630)

![원본 미완료가 발생한 7개 조합의 완료 횟수 비교](figures/incomplete_recovery.png)

- A·B·C 결합 후 동일한 630회 재실행. 실행 오류·누락·중복 0건
- **기존 미완료 62회: 모두 완료 처리·목표량 전체 수신**
- **전체 완료 처리: 568/630 → 630/630**
- **전체 수신: 533/630 → 621/630**
- 목표량 5,242,880B·완료 임계량 5,239,880B·손실률 0·OLIA·60초 종료·완료 후 10ms 대기 유지

'''+table+'''
### 3-2. 완료 후 기록 종료 테스트 (대기 10ms → 250ms 변경: 부족 9회 모두 전체 수신)

- **10ms 기록 종료 시 목표량 미달 9회**
  - **원본에서도 부족한 실행: 5회**
  - **원본은 전체 수신이었지만 수정 후 부족한 실행: 4회**
- 동일 9회에서 완료 판정 후 대기만 250ms로 연장 → 9/9 전체 수신, 기록된 완료 시간은 모두 동일
- 기본 대기 10ms 유지. 630회 전체 결과와 별도 9회 대기 연장 결과를 구분해 보관
- 부족 조합: competing의 MinRTT/seed 8·BLEST/seed 16·ECF/seed 23, degrade의 RR/seed 4·6·19·MinRTT/seed 9·MinRTT-multi/seed 17·22

### 3-3. 원본에서도 완료한 seed의 시간 비교 (일부 전송 시간 증가)

- 같은 스케줄러·시나리오·seed에서 양쪽 모두 완료한 568회: 더 빠름 135회·동일 266회·더 느림 167회
- competing의 MinRTT-multi: 공통 완료 13회에서 평균 +0.3035초. 양쪽 모두 전체 수신한 11회에서도 평균 +0.3183초
- 양쪽 모두 전체 수신한 degrade/Peekaboo/seed 28: 7.0503초 → 10.8214초
- 완료율 회복과 함께 시간 증가 확인. 손실 복구에 따른 재전송·혼잡 제어 변화를 추가 추적할 대상
- 21개 조합의 공통 완료 수·평균 차이·95% 신뢰구간·부호 순위 검정·승패 seed 수를 별도 CSV에 보존

### 3-4. 비판 검토·관찰 도구 검증 (다른 에이전트의 독립 추적과 대조)

- 비판 검토 에이전트가 원인별 가설·폐기 패킷 번호·재전송·수신 위치와 시간 증가를 별도 확인
- 관찰 코드 켜기 전후 동일 62회의 9개 측정값 모두 일치
- 수신 바이트 수뿐 아니라 실제 바이트 순서를 확인하는 회귀 테스트: 원본 실패 → 수정 후 모두 통과
- 비판 검토에서 중복 데이터에 처음 붙은 FIN(스트림 종료 표식) 누락 위험 발견 → 종료 표식 먼저 처리하도록 보완
- FIN 포함 중복 데이터의 종료 상태·바이트 수·순서 검사 통과. 최종 코드로 630회 재실행해 앞선 수정 결과와 9개 측정값 모두 동일
- 동결 기준 폴더의 해시 목록 27개 모두 유지. 수정 결과는 별도 폴더·브랜치에 보관

## 4. 개선 방법·다음 조사 대상

- 채택한 수정: 이미 전달한 중복 데이터 제외, ACK 전용 번호에서도 손실 감지, 소켓 읽기의 바이트 보존
- 추가 방법: QUIC·UDP·IPv4 헤더까지 포함해 MTU(한 번에 전송하는 IP 패킷 크기) 이하로 송신 데이터 길이 제한. 조각 폐기 영향 줄이기 위한 별도 후보이며 미검증
- 추가 검증 범위: 대기 중인 서로 다른 프레임끼리의 부분 겹침, 선택형 시간 기반 손실 감지, 전송 시간이 증가한 실행의 재전송·혼잡 제어 경로
- 기존 01+02 패치의 동결 기준과 수정 A·B·C의 결과를 분리. 기준 데이터 교체·게이트 2 판정·3주차 진입은 별도 검토

## 5. 코드·측정 자료

'''
    for label,path,tree in [('수정 브랜치','',True),('630회 수정 결과','artifacts/week2-incomplete-2026-10-07/14-fin-preservation-full-630/results.csv',False),('62회 원인·제공 기준 범위','artifacts/week2-incomplete-2026-10-07/analysis/incomplete62_causes.csv',False),('공통 완료 seed의 시간 변화','artifacts/week2-incomplete-2026-10-07/critical-review-paired-times.csv',False),('독립 비판 검토','artifacts/week2-incomplete-2026-10-07/critical-review.md',False),('전체 실험·명령·로그·패치','artifacts/week2-incomplete-2026-10-07',True),('실행 도구','sched-lab/incomplete-investigate.py',False)]:
        detailed+='- '+label+' : '+link(path,tree)+'\n'
    for label, path in [('중복·겹침 수신 수정', 'src/quic/model/quic-stream-base.cc'), ('ACK 손실 감지 수정', 'src/quic/model/quic-socket-tx-buffer.cc'), ('소켓 읽기 수정', 'src/quic/model/quic-socket-rx-buffer.cc'), ('패킷 추적 연결', 'src/quic/model/quic-socket-base.cc'), ('실험·관찰 및 완료 후 대기 옵션', 'scratch/mpquic-sched-lab.cc'), ('수신 바이트 순서 회귀 테스트', 'scratch/quic-rx-regression.cc'), ('손실 재전송 회귀 테스트', 'scratch/quic-loss-regression.cc'), ('실험 표·그림 생성 코드', 'artifacts/week2-incomplete-2026-10-07/generate_analysis.py'), ('그림 SVG', 'reports/week2/figures/incomplete_recovery.svg'), ('수정 B 분리 패치', 'artifacts/week2-incomplete-2026-10-07/stream-rx-candidate.patch'), ('수정 C 분리 패치', 'artifacts/week2-incomplete-2026-10-07/loss-detection-candidate.patch'), ('수정 A 분리 패치', 'artifacts/week2-incomplete-2026-10-07/socket-rx-candidate.patch')]:
        detailed += '- ' + label + ' : ' + link(path) + '\n'
    (REPORT/'2주차 미완료 원인 분석.md').write_text(detailed,encoding='utf-8')
    section='''## 4. 미완료 원인 분석·수정 테스트 (기존 미완료 62회 전체 수신 회복)

![미완료가 발생한 7개 조합의 수정 전후 완료 횟수](figures/incomplete_recovery.png)

- **최초 문제 상황: seed 1~30의 미완료 62회**
  - 원본 완료 처리 568/630·전체 수신 533/630. 실행 오류는 0건
  - 제공 seed 1~10의 미완료 19회는 제공 기준과 동일. 추가 seed 11~30의 43회는 제공 기준 없음
- **문제 정의·식별: 중복 수신 처리 54회·손실 감지 누락 8회**
  - 54회: 이미 전달한 중복 데이터 때문에 순서 대기 버퍼와 실제 애플리케이션 수신량이 불일치
  - 8회: 기본 FqCoDel 큐에서 IP 조각 폐기 후 재조립 실패. ACK 전용 번호가 데이터 전송 목록에 없으면 손실 검사가 생략돼 재전송 정체
  - 종료 시각 60초 → 300초 변경 후에도 62회 수신량 동일
- **접근(수정) 방법: 수신 버퍼·ACK 손실 판단 수정 후 같은 조건 재실행**
  - 스트림 중복·겹침 처리만 수정 → 54/62 전체 수신. 손실 감지만 수정 → 나머지 8/8 전체 수신
  - 소켓 읽기 바이트 차감의 별도 결함 수정. 이 수정만으로는 미완료 결과 변화 없음
  - 목표량·링크·스케줄러·손실률·OLIA·완료 조건 유지. 관찰 코드 활성·비활성의 62회 측정값 동일
- **결과: 완료 처리 630/630·목표량 전체 수신 621/630**
  - 기존 미완료 62회 모두 완료·전체 수신. 완료된 원본 568회가 다시 미완료된 사례 0건
  - 바이트 부족 9회: 원본도 부족한 5회·수정 후 새로 부족한 4회. 완료 후 대기 10ms → 250ms 변경 테스트에서 9/9 전체 수신, 완료 시간 동일
  - 시간 증가도 확인: competing/MinRTT-multi의 공통 완료 13회 평균 +0.3035초. 양쪽 전체 수신 11회에서도 +0.3183초
  - 비판 검토 에이전트가 패킷 폐기·재전송·바이트 순서·시간 증가를 독립 확인. 중복 프레임의 FIN(종료 표식) 누락 위험도 보완해 최종 630회 결과 동일

- 상세 원인·조건별 결과 : '''+link('reports/week2/2주차 미완료 원인 분석.md')+'\n'
    reportpath=REPORT/'2주차 진행상황.md'
    old=reportpath.read_text().replace('- 수정 브랜치 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/docs/%238-provided-reference-comparison', '- 제공 기준 대조 브랜치 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/docs/%238-provided-reference-comparison')
    marker='## 4. 미완료 원인 분석·수정 테스트'
    if marker in old: old=old[:old.index(marker)] + old[old.index('## 5. 다음 작업'):]
    else: old=old.replace('## 4. 다음 작업','## 5. 다음 작업').replace('## 5. 코드·측정 자료','## 6. 코드·측정 자료')
    reportpath.write_text(old.replace('## 5. 다음 작업',section+'\n## 5. 다음 작업'),encoding='utf-8')
    for path in ['README.md','reports/README.md','reports/week2/README.md','artifacts/README.md']:
        f=ROOT/path; text=f.read_text(); new='- 2주차 미완료 원인 분석 : '+link('reports/week2/2주차 미완료 원인 분석.md')+'\n'
        if new not in text:
            head,tail=text.split('\n',1);text=head+'\n\n'+new+'- 수정 검증: 원본 미완료 62회 모두 전체 수신. 630회 완료·621회 전체 수신, 시간 증가와 종료 후 기록 범위 별도 확인\n'+tail
            f.write_text(text,encoding='utf-8')
    (ART/'README.md').write_text('''# 2주차 미완료 원인 분석 산출물

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

- 상세 분석 : '''+link('reports/week2/2주차 미완료 원인 분석.md')+'\n',encoding='utf-8')
    print(json.dumps({'completed':int(after.done.sum()),'full':int(after.rx_app.eq(after['size']).sum()),'frozen_files_verified':len(hashes),'report_created':True}))

if __name__ == '__main__':
    main()
