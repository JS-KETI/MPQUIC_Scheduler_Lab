"""Render a week-2 summary from preserved measurement CSVs.

Charts: Ubuntu Python with matplotlib. Documents: bundled Windows Python
with reportlab. Both commands take --repo; output is reports/week2/summary.
"""
import argparse
import base64
import csv
import html
import json
import statistics
import hashlib
import shutil
from pathlib import Path

BASE = 'artifacts/week2-2026-10-02/run-01/baseline.csv'
FIXED = 'artifacts/week2-incomplete-2026-10-07/14-fin-preservation-full-630/results.csv'
COMPLETED = 'artifacts/week2-completion-2026-10-08/run-01/results.csv'
ORDER = [0, 1, 2, 3, 4, 6, 5]
NAMES = ['RR', 'MinRTT', 'BLEST', 'ECF', 'Peekaboo', 'MinRTT-multi', 'EAT']
SCENARIOS = ['dominating', 'competing', 'degrade']
BRANCH = 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis'
BASIC = 'artifacts/week2-basic-visuals-2026-10-08'


def prepare_basic_figures(repo, out):
    """Run the supplied analyzer on a COPY; preserve the frozen baseline."""
    import contextlib
    import runpy
    import sys
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcdefaults()
    archive = repo/BASIC
    archive.mkdir(parents=True, exist_ok=True)
    source = repo/BASE
    copied = archive/'baseline.csv'
    if copied.exists():
        assert copied.read_bytes() == source.read_bytes()
    else:
        shutil.copy2(source, copied)
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(repo/'sched-lab/analyze.py'), str(copied)]
        with (archive/'analyze.log').open('w') as log, contextlib.redirect_stdout(log):
            runpy.run_path(str(repo/'sched-lab/analyze.py'), run_name='__main__')
        # Export the very same provided-tool figure as SVG for native Notion images.
        plt.gcf().savefig(archive/'baseline_fct.svg')
        plt.close('all')
    finally:
        sys.argv = old_argv
    for ext in ['png', 'svg']:
        shutil.copy2(archive/f'baseline_fct.{ext}', out/'figures'/f'baseline_fct.{ext}')
        for name in ['completion_rates', 'path_shares']:
            shutil.copy2(repo/'artifacts/week2-2026-10-02/run-01/figures'/f'{name}.{ext}', out/'figures'/f'{name}.{ext}')
    provenance = {
        'input': BASE, 'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'provided_analyzer': 'sched-lab/analyze.py',
        'analyzer_sha256': hashlib.sha256((repo/'sched-lab/analyze.py').read_bytes()).hexdigest(),
        'compatibility': 'Existing matplotlib compatibility patch: tick_labels -> labels; measurement and plotting logic retained',
        'command': f'python3 artifacts/report-tools/week2_compact_report.py --repo {repo} --charts',
        'provided_cli_equivalent': f'python3 sched-lab/analyze.py {BASIC}/baseline.csv',
        'execution_method': 'runpy.run_path with the supplied analyzer path and copied CSV in sys.argv',
        'svg_export': 'matplotlib.pyplot.gcf().savefig on the same figure after runpy execution',
        'copied_week2_figures': ['completion_rates', 'path_shares'],
        'additional_simulation_runs': 0,
    }
    (archive/'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2)+'\n')
    (archive/'README.md').write_text('# 2주차 기본 시각화 자료\n\n- 원본 동결 baseline.csv를 복사해 제공 analyze.py 실행. 630회 데이터 내용 동일\n- baseline_fct.png: 제공 도구의 시간 분포·완료 횟수 박스플롯\n- baseline_fct.svg: 동일 Figure의 SVG 출력, 노션 본문 표시\n- baseline_summary.csv·analyze.log·provenance.json: 제공 도구의 요약표·실행 출력·생성 근거\n- 완료율·경로 비율 그림은 기존 동결 run-01 그림을 보고서에 그대로 복사\n- 추가 시뮬레이션 없음. 원본 동결 폴더 수정 없음\n')


def read_rows(path):
    with path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 630
    assert len({(r['scenario'], r['scheduler'], r['seed']) for r in rows}) == 630
    return rows


def counts(rows):
    return sum(int(r['done']) for r in rows), sum(int(r['rx_app']) == int(r['size']) for r in rows)


def make_charts(repo, out, original, fixed):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font = FontProperties(fname='/mnt/c/Windows/Fonts/malgun.ttf')
    plt.rcParams.update({'font.family': font.get_name(), 'font.size': 10, 'axes.unicode_minus': False,
                         'svg.fonttype': 'path', 'savefig.facecolor': 'white'})
    # Register the font explicitly; WSL's default font cache need not contain it.
    from matplotlib import font_manager
    font_manager.fontManager.addfont('/mnt/c/Windows/Fonts/malgun.ttf')
    fig, axes = plt.subplots(1, 3, figsize=(10.8, 5.7), sharex=True)
    subtitle = ['빠른 경로의 지연도 짧음', '빠른 경로의 지연은 더 김', '전송 중 한 경로 속도·지연 악화']
    for ax, scenario, sub in zip(axes, SCENARIOS, subtitle):
        means, labels = [], []
        for sid, name in zip(ORDER, NAMES):
            group = [r for r in original if r['scenario'] == scenario and int(r['scheduler']) == sid]
            done, full = counts(group)
            means.append(statistics.mean(float(r['fct_s']) for r in group if int(r['done'])))
            labels.append(f'{name}\n완료 {done} · 전체 수신 {full}')
        bars = ax.barh(range(7), means, color=['#b9c9d6'] * 5 + ['#246b78', '#b9c9d6'], height=.6)
        for bar, value in zip(bars, means):
            ax.text(value + .12, bar.get_y() + bar.get_height()/2, f'{value:.4f}', va='center', fontsize=10)
        ax.set_yticks(range(7), labels, fontsize=9.3)
        ax.invert_yaxis()
        ax.set_xlim(0, 9.0)
        ax.set_xticks([0, 3, 6, 9])
        ax.set_xlabel('평균 전송 완료 시간 (초)', fontsize=10)
        ax.set_title(f'{scenario}\n{sub}', loc='left', fontsize=11, pad=12)
        ax.set_axisbelow(True)
        ax.grid(axis='x', alpha=.2)
        for side in ['top', 'right', 'left']:
            ax.spines[side].set_visible(False)
        ax.tick_params(axis='y', length=0)
    fig.subplots_adjust(left=.135, right=.98, wspace=.80, top=.87, bottom=.11)
    for ext in ['png', 'svg']:
        fig.savefig(out / 'figures' / f'baseline_performance.{ext}', dpi=220)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10.8, 2.05))
    before = counts(original)
    after = counts(fixed)
    for y, label, b, a in zip([1, 0], ['완료 처리', '목표 바이트 전체 수신'], before, after):
        ax.barh(y + .16, b, height=.27, color='#9eafbd', label='기존 측정' if y == 1 else None)
        ax.barh(y - .16, a, height=.27, color='#246b78', label='코드 수정 후' if y == 1 else None)
        ax.text(b - 8, y + .16, f'{b}/630', ha='right', va='center', color='white', fontweight='bold')
        ax.text(a - 8, y - .16, f'{a}/630', ha='right', va='center', color='white', fontweight='bold')
    ax.set_yticks([1, 0], ['완료 처리', '목표 바이트 전체 수신'])
    ax.set_xlim(0, 650)
    ax.set_xticks([0, 210, 420, 630])
    ax.set_xlabel('실행 횟수', labelpad=2)
    ax.legend(loc='lower right', bbox_to_anchor=(1, 1.02), frameon=False, ncol=2)
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    for side in ['top', 'right', 'left']:
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    fig.subplots_adjust(left=.22, right=.98, top=.77, bottom=.22)
    for ext in ['png', 'svg']:
        fig.savefig(out / 'figures' / f'recovery_counts.{ext}', dpi=220)
    plt.close(fig)


def make_completion_chart(out, original, fixed, completed):
    """Preserve prior figures and add the three measured receipt states."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.font_manager import FontProperties
    font_manager.fontManager.addfont('/mnt/c/Windows/Fonts/malgun.ttf')
    font = FontProperties(fname='/mnt/c/Windows/Fonts/malgun.ttf')
    plt.rcParams.update({'font.family': font.get_name(), 'font.size': 11,
                         'axes.unicode_minus': False, 'svg.fonttype': 'path'})
    fig, ax = plt.subplots(figsize=(10.8, 3.15))
    labels = ['기존 측정 · 종료 대기 10ms', '수신·재전송 수정 · 종료 대기 10ms', '수정 코드 · 종료 대기 250ms']
    for y, label, rows in zip([2, 1, 0], labels, [original, fixed, completed]):
        done, full = counts(rows)
        left = 0
        for n, color in [(full, '#246b78'), (done-full, '#e6b84d'), (630-done, '#a7b4be')]:
            ax.barh(y, n, left=left, height=.57, color=color)
            if n >= 20:
                ax.text(left+n/2, y, str(n), va='center', ha='center', color='white', fontweight='bold')
            left += n
        ax.text(642, y, f'완료 {done}/630 · 전체 수신 {full}/630', va='center', fontsize=10)
    ax.set_yticks([2, 1, 0], labels)
    ax.set_xlim(0, 1040)
    ax.set_xticks([0, 210, 420, 630])
    ax.set_xlabel('실행 횟수')
    ax.set_title('초록: 목표량 전체 수신 · 노랑: 완료 후 부족 · 회색: 미완료', loc='left', fontsize=11, pad=15)
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    for side in ['top', 'right', 'left']:
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    fig.subplots_adjust(left=.34, right=.985, top=.8, bottom=.2)
    for ext in ['png', 'svg']:
        fig.savefig(out/'figures'/f'completion_grace_counts.{ext}', dpi=220)
    plt.close(fig)


def blocks(original, fixed, completed):
    assert counts(original) == (568, 533)
    assert counts(fixed) == (630, 621)
    assert counts(completed) == (630, 630)
    return [
        ('h2', '1. 2주차 작업 내용'),
        ('h3', '1-1. 기존 기준 스택의 멀티 경로 630회 측정 (제공 seed 1~10 결과와 모두 일치)'),
        ('bullet', '**반복 측정 (시나리오·스케줄러별 전송 성능 확인)**'),
        ('sub', '사용 도구: run_sweep.py·mpquic-sched-lab.cc'),
        ('sub', '실행 규모: 3시나리오 × 7스케줄러 × 30seed = 630회. 누락·중복·실행 오류 0건'),
        ('sub', '측정 구성: 제공 01+02 패치를 적용한 기준 스택'),
        ('bullet', '**측정 조건 (스케줄러 비교에서 동일하게 유지한 설정)**'),
        ('sub', '목표 전송량: 5,242,880B. 혼잡 제어 OLIA, 설정 손실률 0, 시뮬레이션 종료 시각 60초'),
        ('sub', 'seed: 링크 속도·지연의 변화를 재현하는 난수 번호. 같은 번호끼리 비교'),
        ('image', 'baseline_fct.png', '그림 1. 제공 analyze.py의 전송 시간 분포·완료 횟수 (기존 기준 스택 630회)'),
        ('bullet', '**그림 읽는 방법 (완료한 실행의 전송 시간 분포)**'),
        ('sub', '세모: 평균. 상자: 가운데 50% 구간. 이름 아래 숫자: 완료/전체 실행 수'),
        ('bullet', '**시나리오 (두 경로의 속도·지연 설정)**'),
        ('sub', 'dominating: 빠른 경로의 지연도 짧음'),
        ('sub', 'competing: 빠른 경로의 지연은 더 김'),
        ('sub', 'degrade: 전송 중 한 경로의 속도·지연 악화'),
        ('table', ['측정 범위', '완료 처리', '목표 전체 수신', '제공 기준 대조'], [
            ['seed 1~10 · 210회', '191/210', '181/210', '기준도 191·181회, 미달 조합·수신량 동일'],
            ['seed 11~30 · 420회', '377/420', '352/420', '제공 기준 없음 · 추가 측정'],
            ['seed 1~30 · 630회', '568/630', '533/630', '전체 바이트 미달 97회'],
        ], [1.18, .76, .90, 2.66]),
        ('h3', '1-2. 기존 기준 스택의 완료율·목표 바이트 수신 테스트 (완료 568회·전체 수신 533회)'),
        ('image', 'completion_rates.png', '그림 2. 요청서에서 요구한 완료율 분석 · 추가 작성한 plot_baseline.py로 생성'),
        ('bullet', '**수신 판정 (완료 처리와 목표량 전체 수신 구분)**'),
        ('sub', '완료 처리: 목표보다 최대 3,000B 부족해도 코드 기준 충족'),
        ('sub', '전체 수신: 목표 5,242,880B 정확 수신'),
        ('bullet', '**기존 측정 결과 (그림 색상별 수신 상태)**'),
        ('sub', '**초록: 전체 수신 533회**'),
        ('sub', '**노랑: 완료 처리됐지만 목표량 미달 35회**'),
        ('sub', '**회색: 완료 기준 미충족 62회**'),
        ('sub', 'seed 1~10의 바이트 미달 29회는 제공 기준과 동일. 추가 seed 11~30에는 제공 기준 없음'),
        ('break',),
        ('h3', '1-3. 기존 기준 스택의 전송 분배 테스트 (시나리오별 경로 사용 비율 확인)'),
        ('image', 'path_shares.png', '그림 3. 요청서에서 요구한 경로별 전송 비율 분석 · 추가 작성한 plot_baseline.py로 생성'),
        ('bullet', '**경로별 전송 비율 (완료한 실행에서 두 경로를 사용한 비중)**'),
        ('sub', 'IP 계층 수신 바이트 기준. 헤더·재전송 포함'),
        ('sub', 'MinRTT-multi의 경로 1 비율: dominating 67.5%, competing 60.9%, degrade 37.7%'),
        ('bullet', '**통계·자료 보존 (이후 스케줄러 비교에 사용할 측정 기록)**'),
        ('sub', 'stats.py로 평균·중앙값·p90(상위 10% 경계)·95% 수신 시간 집계'),
        ('sub', '같은 seed끼리의 시간 차이·신뢰구간 계산. baseline.csv·명령·그림 동결 완료'),
        ('h2', '2. 문제 상황 - 미완료 62회 원인 분석·수정'),
        ('h3', '2-1. 원인별 유효 수정 결과 (미완료 62회 모두 전체 수신)'),
        ('bullet', '**중복 수신 처리 수정 (이미 전달한 데이터의 중복 반영 방지)**'),
        ('sub', '원인'),
        ('detail', '전달이 끝난 중복 데이터로 수신 위치 계산과 실제 전달량 불일치. 미완료 54회 발생'),
        ('sub', '수정'),
        ('detail', '이미 전달한 범위 제외·실제 추출량만 수신 위치에 반영'),
        ('sub', '**결과**'),
        ('detail', '**해당 54회 모두 완료 처리·목표량 전체 수신**'),
        ('bullet', '**재전송 판단 수정 (유실된 데이터의 재전송 누락 방지)**'),
        ('sub', '원인'),
        ('detail', '네트워크 큐(FqCoDel)의 지연 목표 초과로 IPv4 조각 폐기. 재전송 판단이 누락돼 8회 미완료'),
        ('sub', '수정'),
        ('detail', 'ACK(수신 확인) 번호가 송신 목록에 없어도 번호 차이로 손실 검사 수행'),
        ('sub', '**결과**'),
        ('detail', '**해당 8회 모두 완료 처리·목표량 전체 수신**'),
        ('image', 'recovery_counts.png', '그림 4. 동일 조건 630회 수정 전후 결과 (완료 후 10ms 종료 유지)'),
        ('bullet', '**수정 통합 결과 (종료 대기 10ms로 630회 재실험)**'),
        ('sub', '**완료 처리 630/630회. 목표량 전체 수신 621/630회**'),
        ('sub', '기존 미완료 62회: 제공 seed 1~10의 19회는 기준과 동일. 추가 seed 11~30의 43회는 제공 기준 없음'),
        ('h3', '2-2. 종료 대기 250ms 적용 테스트 (630회 모두 완료·목표량 전체 수신)'),
        ('image', 'completion_grace_counts.png', '그림 5. 기존 측정·수신 및 재전송 수정·종료 대기 250ms 적용 결과 (각 630회)'),
        ('bullet', '**종료 대기 검증 (미달 9회 원인 확인·전체 630회 검증 완료)**'),
        ('sub', '원인: 완료 후 10ms에 종료해 후속 바이트 수신 전에 측정 종료. 기존 10ms 결과에서 목표량 미달 9회 발생'),
        ('sub', '별도 실험: 대기 10ms → 250ms 변경 후 9/9회 전체 수신. 기록된 완료 시각 동일'),
        ('sub', '기본 10ms 결과의 미달 9회: 기존 미달 5회 + 수정 후 신규 미달 4회'),
        ('sub', '전체 재검증: CompletionGraceMs=250 적용, 3시나리오 × 7스케줄러 × 30seed = 630회'),
        ('sub', '**결과: 완료 처리 630/630회·목표 5,242,880B 전체 수신 630/630회. 누락·중복·실행 오류 0건**'),
        ('sub', '조합별 결과: 21개 스케줄러–시나리오 조합 각각 30/30회 완료 처리·전체 수신'),
        ('sub', '대조: 기존 10ms 결과와 630회 모두 기록된 완료 시각 동일. 종료 대기만 변경'),
        ('bullet', '**전송 시간 변화 (수정 전후 모두 완료한 같은 seed끼리 비교)**'),
        ('sub', '대상: competing·MinRTT-multi의 공통 완료 seed 13개'),
        ('sub', '평균 시간: 3.4185초 → 3.7220초. **0.3035초 증가**'),
        ('sub', '비교 조건: 수정 전후 모두 완료 처리 후 10ms 종료. 종료 대기 250ms 검증에서도 기록된 완료 시각 동일'),
        ('bullet', '**게이트 2 (2주차 기준 데이터 확정 조건)**'),
        ('sub', '통과 기준: dominating 평균 전송 완료 시간의 95% 신뢰구간 폭 0.1초 이하'),
        ('sub', '신뢰구간 폭: 반복 측정으로 추정한 평균의 불확실성 범위. 상한에서 하한을 뺀 값'),
        ('sub', 'MinRTT-multi: 기존 0.0130초 → 수정 0.0257초. 기준 충족'),
        ('sub', 'MinRTT·ECF·Peekaboo: 수정 후 0.1647~0.1751초. 기준 초과'),
        ('sub', '공식 기준값: 수정 코드·종료 대기 250ms의 630회 자료로 확정·동결. 신뢰구간 기준 적용 대상은 확인 필요'),
        ('h2', '3. 다음 작업 - 3주차 스케줄러 연결·고정 비율 검증'),
        ('bullet', '**스케줄러 연결 (ID 7에 신규 실험 슬롯 추가)**'),
        ('sub', 'MinRTT-multi와 같은 초기 동작을 연결하고 호출·결정 로그 확인'),
        ('bullet', '**고정 비율 검증 (두 경로에 지정한 전송량 비율 확인)**'),
        ('sub', 'BytesToRatio 유틸과 선택형 계측 추가. 분배 비율 0.3/0.7·0.1/0.9·0.5/0.5 테스트'),
        ('sub', '검증 항목: 경로 제약 구간 제외 실제 분배 오차 ±5%, 결정 로그·두 경로 도착 시차 확인'),
        ('link', '수정 코드·측정 자료', 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/pull/10'),
        ('link', '종료 대기 250ms 전체 재검증 자료', BRANCH+'/artifacts/week2-completion-2026-10-08/run-01'),
        ('link', '기존 630회 기준 자료', 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/artifacts/week2-2026-10-02/run-01'),
        ('bullet', '**630개 시행 테스트 결과**'),
        ('sub', '**각 시행 원본 (시나리오·스케줄러·seed별 측정값 630개)**'),
        ('detail', '원본 측정 CSV : '+BRANCH.replace('/tree/', '/blob/')+'/artifacts/week2-completion-2026-10-08/run-01/results.csv'),
        ('sub', '**이후 작업에 사용할 기준값 SET (완료 처리·전체 수신 각각 630/630회)**'),
        ('detail', '기준값 SET (측정값·통계·그림 묶음) : '+BRANCH+'/artifacts/week2-completion-2026-10-08/run-01'),
        ('detail', '기준값 통계 CSV (21개 조합별 평균·중앙값·p90·완료율·신뢰구간) : '+BRANCH.replace('/tree/', '/blob/')+'/artifacts/week2-completion-2026-10-08/run-01/analysis/summary.csv'),
        ('detail', '기준값 시각화 3종 (전송 시간 분포·완료율·경로 비율) : '+BRANCH+'/artifacts/week2-completion-2026-10-08/run-01/figures'),
    ]


def inline(text, kind='html'):
    import re
    text = html.escape(text)
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)


def documents(out, data):
    md, parts = [], []
    depth = -1

    def close_list():
        nonlocal depth
        while depth >= 0:
            parts.append('</li></ul>')
            depth -= 1

    for b in data:
        kind = b[0]
        if kind not in ('bullet', 'sub', 'detail'):
            close_list()
        if kind in ('h2', 'h3'):
            md += ['', ('#' * int(kind[1])) + ' ' + b[1], '']
            parts += [f'<{kind}>{html.escape(b[1])}</{kind}>']
        elif kind in ('bullet', 'sub', 'detail'):
            target = {'bullet': 0, 'sub': 1, 'detail': 2}[kind]
            md += ['  '*target + '- ' + b[1]]
            if target > depth:
                assert target == depth + 1, 'A child item must belong to an immediate parent'
                cls = 'items' if target == 0 else 'details'
                parts.append('<ul class="'+cls+'"><li>'+inline(b[1]))
            else:
                while depth > target:
                    parts.append('</li></ul>')
                    depth -= 1
                parts.append('</li><li>'+inline(b[1]))
            depth = target
        elif kind == 'note':
            md += ['', b[1], '']
            parts += [f'<p class="note">{inline(b[1])}</p>']
        elif kind == 'image':
            md += ['', f'![{b[2]}](figures/{b[1]})', '']
            raw = base64.b64encode((out/'figures'/b[1]).read_bytes()).decode('ascii')
            parts += [f'<figure><img src="data:image/png;base64,{raw}"><figcaption>{html.escape(b[2])}</figcaption></figure>']
        elif kind == 'table':
            md += ['', '| ' + ' | '.join(b[1]) + ' |', '| ' + ' | '.join(['---']*len(b[1])) + ' |']
            md += ['| ' + ' | '.join(row) + ' |' for row in b[2]] + ['']
            parts += ['<table><thead><tr>' + ''.join(f'<th>{inline(x)}</th>' for x in b[1]) + '</tr></thead><tbody>' +
                      ''.join('<tr>' + ''.join(f'<td>{inline(x)}</td>' for x in row) + '</tr>' for row in b[2]) + '</tbody></table>']
        elif kind == 'break':
            md += ['', '---', '']
            parts += ['<div class="pagebreak"></div>']
        elif kind == 'link':
            md += ['- ' + b[1] + ' : ' + b[2]]
            parts += [f'<p class="link">• {html.escape(b[1])} : {html.escape(b[2])}</p>']
    close_list()
    # Keep headings and list groups separated, without redundant blank lines.
    formatted = []
    for line in md:
        if line.startswith('- ') and formatted and formatted[-1] and not formatted[-1].lstrip().startswith('- '):
            formatted.append('')
        if line or (formatted and formatted[-1]):
            formatted.append(line)
    (out/'2주차 진행상황.md').write_text('\n'.join(formatted).strip()+'\n', encoding='utf-8', newline='\n')
    css = '''body{font-family:"Malgun Gothic",sans-serif;color:#203446;max-width:1040px;margin:32px auto;padding:0 24px;line-height:1.7;font-size:16px}h2{font-size:24px;background:#e2eee8;padding:12px 16px;margin:24px 0 16px}h3{font-size:19px;background:#e9eff6;padding:10px 14px;margin:22px 0 14px}figure{margin:22px 0}img{width:100%;display:block}figcaption,.note{font-size:14px;color:#526576;margin-top:8px}.items{padding-left:24px;margin:14px 0 22px}.items>li{margin:14px 0}.details{padding-left:26px;margin:6px 0;list-style-type:circle}.details>li{margin:5px 0}table{width:100%;border-collapse:collapse;margin:20px 0}th{background:#edf2f6}th,td{border-bottom:1px solid #d8e0e5;padding:9px;text-align:left;font-size:15px}.link{font-size:14px;overflow-wrap:anywhere;margin:6px 0}.pagebreak{height:20px}@media print{@page{size:A4;margin:13mm}body{margin:0;padding:0;max-width:none}figure,table{break-inside:avoid}}'''
    (out/'2주차 진행상황.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>2주차 진행상황</title><style>'+css+'</style></head><body>'+''.join(parts)+'</body></html>', encoding='utf-8', newline='\n')


def pdf(out, data):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    pdfmetrics.registerFont(TTFont('Korean', 'C:/Windows/Fonts/malgun.ttf'))
    pdfmetrics.registerFont(TTFont('KoreanBold', 'C:/Windows/Fonts/malgunbd.ttf'))
    pdfmetrics.registerFontFamily('Korean', normal='Korean', bold='KoreanBold')
    normal = ParagraphStyle('body', fontName='Korean', fontSize=9.3, leading=13.2, textColor=colors.HexColor('#203446'), spaceAfter=3)
    h2 = ParagraphStyle('h2', parent=normal, fontName='KoreanBold', fontSize=15, leading=22, backColor=colors.HexColor('#e2eee8'), borderPadding=5, spaceBefore=2, spaceAfter=10)
    h3 = ParagraphStyle('h3', parent=normal, fontName='KoreanBold', fontSize=10.5, leading=15, backColor=colors.HexColor('#e9eff6'), borderPadding=4, spaceBefore=5, spaceAfter=8)
    sub = ParagraphStyle('sub', parent=normal, leftIndent=10, fontSize=9.1, leading=12.4, spaceAfter=2)
    note = ParagraphStyle('note', parent=normal, fontSize=8, leading=11, textColor=colors.HexColor('#526576'), spaceAfter=5)
    cell = ParagraphStyle('cell', parent=normal, fontSize=8, leading=10.5, spaceAfter=0)
    link = ParagraphStyle('link', parent=normal, fontSize=6.9, leading=9, wordWrap='CJK', spaceAfter=2)
    story = []
    width = A4[0] - 28*mm
    for b in data:
        kind = b[0]
        if kind in ('h2', 'h3'):
            story.append(Paragraph(inline(b[1]), h2 if kind == 'h2' else h3))
        elif kind in ('bullet', 'sub'):
            story.append(Paragraph('• ' + inline(b[1]), sub if kind == 'sub' else normal))
        elif kind == 'note':
            story.append(Paragraph(inline(b[1]), note))
        elif kind == 'image':
            from PIL import Image as PILImage
            im = PILImage.open(out/'figures'/b[1])
            story.append(Spacer(1, 2))
            story.append(Image(str(out/'figures'/b[1]), width=width, height=width*im.height/im.width))
            story.append(Paragraph(inline(b[2]), note))
        elif kind == 'table':
            vals = [[Paragraph('<b>'+inline(x)+'</b>', cell) for x in b[1]]] + [[Paragraph(inline(x), cell) for x in row] for row in b[2]]
            total = sum(b[3])
            table = Table(vals, colWidths=[width*x/total for x in b[3]], hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor('#d8e0e5')),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            story += [Spacer(1,3), table, Spacer(1,5)]
        elif kind == 'break':
            story.append(PageBreak())
        elif kind == 'link':
            story.append(Paragraph('• '+inline(b[1])+' : '+inline(b[2]), link))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Korean', 8)
        canvas.setFillColor(colors.HexColor('#647785'))
        canvas.drawRightString(A4[0]-14*mm, 9*mm, str(doc.page))
        canvas.restoreState()
    doc = SimpleDocTemplate(str(out/'2주차 진행상황.pdf'), pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=13*mm, bottomMargin=14*mm, title='2주차 진행상황', author='jinwoosong')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--charts', action='store_true')
    parser.add_argument('--completion-chart', action='store_true')
    parser.add_argument('--pdf', action='store_true', help='Export PDF only when explicitly requested after reviewing Markdown/HTML')
    args = parser.parse_args()
    out = args.repo/'reports/week2/summary'
    (out/'figures').mkdir(parents=True, exist_ok=True)
    original, fixed = read_rows(args.repo/BASE), read_rows(args.repo/FIXED)
    completed = read_rows(args.repo/COMPLETED)
    if args.completion_chart:
        make_completion_chart(out, original, fixed, completed)
        print(out)
        return
    if args.charts:
        make_charts(args.repo, out, original, fixed)
        prepare_basic_figures(args.repo, out)
    else:
        data = blocks(original, fixed, completed)
        documents(out, data)
        if args.pdf:
            pdf(out, data)
        provenance = json.loads((args.repo/COMPLETED).with_name('provenance.json').read_text())
        source = {
            'original': BASE, 'modified': FIXED, 'completion_grace_recheck': COMPLETED,
            'original_counts': counts(original), 'modified_counts': counts(fixed),
            'completion_grace_recheck_counts': counts(completed),
            'modified_source_commit': '856af610bc34cf3aeefe57bc6843c5480658fbe7',
            'recheck_execution_head': provenance['head'],
            'recheck_completion_grace_ms': 250,
            'recheck_runner_command': provenance['runner_command'],
            'basic_visuals': BASIC, 'provided_analyzer': 'sched-lab/analyze.py',
            'report_figures': ['baseline_fct', 'completion_rates', 'path_shares', 'recovery_counts', 'completion_grace_counts'],
            'current_formats': ['md', 'html'],
            'pdf_status': 'previous version retained; not regenerated' if not args.pdf else 'explicitly exported',
            'report_scope': '2주차 기본 시각화·유효 수정 결과·종료 대기 250ms 전체 재검증·공식 기준값 확정·3주차 계획',
            'active_baseline': 'artifacts/BASELINE.json',
            'accepted_baseline_summary': 'artifacts/week2-completion-2026-10-08/run-01/analysis/summary.csv',
        }
        (out/'source.json').write_text(json.dumps(source, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(out)


if __name__ == '__main__':
    main()
