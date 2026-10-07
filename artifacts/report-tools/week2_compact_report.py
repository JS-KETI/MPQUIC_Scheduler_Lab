"""Render a two-page week-2 summary from preserved measurement CSVs.

Charts: Ubuntu Python with matplotlib. Documents: bundled Windows Python
with reportlab. Both commands take --repo; output is reports/week2/summary.
"""
import argparse
import base64
import csv
import html
import json
import statistics
from pathlib import Path

BASE = 'artifacts/week2-2026-10-02/run-01/baseline.csv'
FIXED = 'artifacts/week2-incomplete-2026-10-07/14-fin-preservation-full-630/results.csv'
ORDER = [0, 1, 2, 3, 4, 6, 5]
NAMES = ['RR', 'MinRTT', 'BLEST', 'ECF', 'Peekaboo', 'MinRTT-multi', 'EAT']
SCENARIOS = ['dominating', 'competing', 'degrade']
BRANCH = 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/fix/%239-week2-incomplete-diagnosis'


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


def blocks(original, fixed):
    assert counts(original) == (568, 533)
    assert counts(fixed) == (630, 621)
    return [
        ('h2', '1. 2주차 작업 내용'),
        ('h3', '1-1. 멀티 경로 스케줄러 630회 측정 (제공 seed 1~10 결과와 모두 일치)'),
        ('bullet', '**수행:** run_sweep.py·mpquic-sched-lab.cc 사용 → 3시나리오 × 7스케줄러 × 30seed = 630회. 누락·중복·실행 오류 0건.'),
        ('bullet', '**조건:** 목표 5,242,880B, 혼잡 제어 OLIA, 설정 손실률 0, 시뮬레이션 종료 시각 60초. seed는 링크 변동을 재현하는 난수 번호.'),
        ('image', 'baseline_performance.png', '그림 1. 기존 측정의 평균 전송 완료 시간과 수신 횟수 (스케줄러·시나리오별 각 30회)'),
        ('note', '평균 시간은 완료 처리된 실행만 집계. 그림의 “완료”는 목표보다 최대 3,000B 부족해도 충족하는 코드 기준, “전체 수신”은 목표 5,242,880B 정확 수신.'),
        ('table', ['측정 범위', '완료 처리', '목표 전체 수신', '제공 기준 대조'], [
            ['seed 1~10 · 210회', '191/210', '181/210', '기준도 191·181회, 미달 조합·수신량 동일'],
            ['seed 11~30 · 420회', '377/420', '352/420', '제공 기준 없음 · 추가 측정'],
            ['seed 1~30 · 630회', '568/630', '533/630', '전체 바이트 미달 97회'],
        ], [1.18, .76, .90, 2.66]),
        ('bullet', '**바이트 미달 97회:** 완료 처리됐지만 전체 수신 미달 **35회**, 완료 기준 미충족 **62회**. seed 1~10의 29회는 제공 기준에도 존재.'),
        ('h3', '1-2. 통계·경로 분배 분석 (측정 자료·명령·그림 동결 완료)'),
        ('bullet', '**산출물:** 완료율·평균·중앙값·p90(상위 10% 경계)·목표 95% 수신 시간, 같은 seed끼리의 시간 차이·95% 신뢰구간·유의확률 집계. 그림 3종과 baseline.csv 보존.'),
        ('bullet', '**주 비교 대상 MinRTT-multi:** dominating 평균 3.2678초, 빠른 경로 전송 비율 67.5%. competing은 13/30회 완료, 목표 95% 수신은 30/30회·평균 3.3656초.'),
        ('break',),
        ('h2', '2. 문제 상황 - 미완료 62회 원인 분석·수정'),
        ('h3', '2-1. 같은 시나리오·스케줄러·seed 재실험 (미완료 62회 모두 전체 수신)'),
        ('image', 'recovery_counts.png', '그림 2. 기존 코드와 수정 코드의 630회 결과 (동일 실행 조건, 완료 후 10ms 종료 유지)'),
        ('bullet', '**최초 문제 상황(현상)**'),
        ('sub', '7개 스케줄러·시나리오 조합에서 62회 미완료. 제공 seed 1~10의 19회는 기준과 동일, 추가 seed 11~30의 43회는 제공 기준 없음.'),
        ('bullet', '**문제 정의·식별**'),
        ('sub', '54회: 이미 전달한 중복 데이터가 수신 버퍼에 들어가, 수신 위치 계산과 실제 전달 바이트가 달라짐. 8회: 네트워크 큐(FqCoDel)의 지연 목표 초과로 IPv4 조각(분할 패킷) 폐기, 재전송 판단 누락.'),
        ('bullet', '**접근(수정) 방법**'),
        ('sub', 'QuicStreamBase::Recv의 중복·부분 중복 처리와 실제 수신량 계산 수정. QuicSocketTxBuffer::OnAckUpdate의 손실 판단 보완. 종료 표시(FIN) 보존 및 수신 버퍼 부분 읽기 수정.'),
        ('table', ['원인별 검증 테스트', '완료 처리', '전체 수신', '확인 결과'], [
            ['종료 시각 60 → 300초', '0/62', '0/62', '수신량 동일 · 시간 연장 효과 없음'],
            ['수신 버퍼 부분 읽기만 수정', '0/62', '0/62', '개별 버퍼 결함 확인 · 미완료는 유지'],
            ['중복 수신 처리만 수정', '54/62', '54/62', '중복 데이터 관련 54회 복구'],
            ['재전송 판단만 수정 · 나머지 8회', '8/8', '8/8', 'IPv4 조각 유실 관련 8회 복구'],
            ['수정 통합 · seed 1~30 전체', '630/630', '621/630', '기존 미완료 62회 모두 전체 수신'],
            ['남은 9회 · 종료 대기 10 → 250ms', '9/9', '9/9', '후속 바이트 수신 · 완료 시각 동일'],
        ], [2.30, .70, .70, 1.80]),
        ('bullet', '**결과**'),
        ('sub', '기본 종료 대기 10ms에서 전체 수신 미달 9회 유지: 기존 미달 5회 + 수정 후 신규 미달 4회. 별도 250ms 대기 실험에서는 9회 모두 전체 수신.'),
        ('sub', '수신·재전송·FIN 단위 검증 통과. 관찰 옵션 전후 62회 결과 일치. 동결 기준 자료 27개 파일의 해시(내용 식별값) 유지.'),
        ('h3', '2-2. 남은 확인·다음 작업 (시간 증가 및 기준선 채택 검토)'),
        ('bullet', '**전송 시간:** competing·MinRTT-multi의 수정 전후 공통 완료 seed 13개 평균 3.4185 → 3.7220초, **0.3035초 증가**. 시간 증가 원인과 남은 9회 종료 처리 검토.'),
        ('bullet', '**게이트 2:** dominating 평균의 95% 신뢰구간 폭(상한-하한) 기준 0.1초. MinRTT-multi는 기존 0.0130초 → 수정 0.0257초로 충족. MinRTT·ECF·Peekaboo는 수정 후에도 0.1647~0.1751초로 초과. 적용 대상·기준선 확정 → 기준 충족 여부 판정 → 3주차 진입 결정.'),
        ('link', '수정 코드·측정 자료', 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/pull/10'),
        ('link', '기존 630회 기준 자료', 'https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/artifacts/week2-2026-10-02/run-01'),
    ]


def inline(text, kind='html'):
    import re
    text = html.escape(text)
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)


def documents(out, data):
    md, parts = [], []
    for b in data:
        kind = b[0]
        if kind in ('h2', 'h3'):
            md += [('#' * int(kind[1])) + ' ' + b[1], '']
            parts += [f'<{kind}>{html.escape(b[1])}</{kind}>']
        elif kind in ('bullet', 'sub'):
            md += [('  ' if kind == 'sub' else '') + '- ' + b[1]]
            parts += [f'<div class="{kind}">• {inline(b[1])}</div>']
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
    # A blank line before the first list and after its previous block is required.
    formatted = []
    for line in md:
        if line.startswith('- ') and formatted and formatted[-1] and not formatted[-1].lstrip().startswith('- '):
            formatted.append('')
        formatted.append(line)
    (out/'2주차 진행상황.md').write_text('\n'.join(formatted).rstrip()+'\n', encoding='utf-8', newline='\n')
    css = '''body{font-family:"Malgun Gothic",sans-serif;color:#203446;max-width:780px;margin:24px auto;line-height:1.5;font-size:13px}h2{font-size:20px;background:#e2eee8;padding:8px 12px;margin:0 0 12px}h3{font-size:15px;background:#e9eff6;padding:7px 10px;margin:13px 0 8px}figure{margin:12px 0}img{width:100%;display:block}figcaption,.note{font-size:11px;color:#526576}table{width:100%;border-collapse:collapse;margin:9px 0}th{background:#edf2f6}th,td{border-bottom:1px solid #d8e0e5;padding:5px;text-align:left;font-size:11px}.bullet{margin:5px 0}.sub{margin:3px 0 5px 16px}.link{font-size:9px;overflow-wrap:anywhere;margin:3px 0}.pagebreak{height:18px}@media print{@page{size:A4;margin:13mm}body{margin:0;font-size:10px;max-width:none;line-height:1.35}h2{font-size:16px}h3{font-size:12px}.pagebreak{break-before:page;height:0}figure,table{break-inside:avoid}}'''
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
    args = parser.parse_args()
    out = args.repo/'reports/week2/summary'
    (out/'figures').mkdir(parents=True, exist_ok=True)
    original, fixed = read_rows(args.repo/BASE), read_rows(args.repo/FIXED)
    if args.charts:
        make_charts(args.repo, out, original, fixed)
    else:
        data = blocks(original, fixed)
        documents(out, data)
        pdf(out, data)
        (out/'source.json').write_text(json.dumps({'original':BASE,'modified':FIXED,'original_counts':counts(original),'modified_counts':counts(fixed),'modified_source_commit':'856af610bc34cf3aeefe57bc6843c5480658fbe7','report_scope':'2주차 측정 및 미완료 원인 분석 요약'}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(out)


if __name__ == '__main__':
    main()
