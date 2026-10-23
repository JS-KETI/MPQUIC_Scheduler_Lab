"""Korean presentation labels; chart values and frozen CSV files stay unchanged."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, sys
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.ticker import PercentFormatter

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS={
 'dominating':'한 경로가 속도·지연 모두 유리\n(dominating)',
 'competing':'빠른 경로의 지연이 더 큼\n(competing)',
 'degrade':'전송 중 경로 1 성능 저하\n(degrade)',
}
CONDITIONS={
 'Default':'기존 조건', 'Event 0.75 s':'경로 열화 시점\n전송 시작 후 0.75초',
 'Event 3 s':'경로 열화 시점\n전송 시작 후 3초',
 'After 3 Mbps':'열화 후 경로 1 속도\n3Mbps', 'After 0.5 Mbps':'열화 후 경로 1 속도\n0.5Mbps',
 'After 80 ms':'열화 후 경로 1 편도 지연\n80ms', 'After 180 ms':'열화 후 경로 1 편도 지연\n180ms',
 'Packet loss 0.1%':'패킷 손실률 0.1%', 'Packet loss 1%':'패킷 손실률 1%',
 'FqCoDel 100 packets':'네트워크 큐 상한\n100패킷', 'FqCoDel 1000 packets':'네트워크 큐 상한\n1,000패킷',
 'QUIC buffers 1 MiB':'송수신 버퍼 각각\n1MiB', 'QUIC buffers 8 MiB':'송수신 버퍼 각각\n8MiB',
 '50 MiB / 80 MB buffers':'50MiB 장시간 전송', '4-path probe':'4경로 동작',
}
def configure_font():
    candidates=[Path('/mnt/c/Windows/Fonts/malgun.ttf'),Path('C:/Windows/Fonts/malgun.ttf')]
    for path in candidates:
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            matplotlib.rcParams['font.family']=font_manager.FontProperties(fname=str(path)).get_name()
            break
    else:
        available={f.name for f in font_manager.fontManager.ttflist}
        for name in ['Noto Sans CJK KR','Noto Sans CJK JP','NanumGothic','Malgun Gothic']:
            if name in available:
                matplotlib.rcParams['font.family']=name
                break
        else: raise RuntimeError('A Korean font is required (Malgun Gothic, Noto CJK or NanumGothic).')
    matplotlib.rcParams['axes.unicode_minus']=False

def translate_text(s,kind):
    fixed={**SCENARIOS,**CONDITIONS,
      'Completed':'완료 처리', 'Exact receipt':'목표 데이터 전체 수신',
      'Before: completed':'수정 전 완료 횟수', 'Integrated: completed':'통합 수정 후 완료 횟수',
      'Completed executions':'완료 처리된 실행 수(회)',
      'flow completion time [s]':'전송 완료 시간(초)',
      'Fraction of transmitted STREAM payload\n(retransmissions included)':'보낸 데이터의 경로별 비중(%)\n(재전송 포함)',
      'NO VALID TX':'유효한 송신 기록 없음',
    }
    if s in fixed: return fixed[s]
    if s.startswith('5 MiB: mean completion time;'):
        return ('5MiB 전송: 스케줄러별 평균 전송 완료 시간\n'
                '각 칸: 완료한 실행의 평균(초) · 완료 횟수 · 전체 수신 횟수\n'
                'OLIA · 종료 대기 250ms · seed 1~5 · 행마다 한 설정 변경 · 색이 진할수록 오래 걸림')
    if s.startswith('5 MiB: seven schedulers'):
        return ('5MiB 전송: 설정별 완료 처리와 목표 데이터 전체 수신\n'
                '각 칸: 7개 스케줄러 × seed 1~5 = 35회 · OLIA · 종료 대기 250ms\n'
                '색이 진할수록 완료 처리 비율이 높음')
    if s.startswith('Week 4: original settings'):
        return ('4주차 통합 수정 전후 완료 횟수\n'
                '동일한 1,163회 조건·seed·버퍼·손실률·큐·제한 시각으로 재검증')
    if s.startswith('50 MiB transfer: completion'):
        return ('50MiB 전송: 완료 처리율과 목표 데이터 전체 수신율\n'
                '막대 아래 숫자: 위는 완료 횟수, 아래는 전체 수신 횟수 (각 10회)\n'
                'OLIA · 손실률 0 · 버퍼 각각 80,000,000B · 종료 대기 250ms · seed 1~10')
    if s.startswith('50 MiB transfer: path 1 fraction'):
        return ('50MiB 전송: 받은 IP 데이터 중 경로 1의 비중\n'
                '완료한 실행별 비중의 평균 · IP/UDP/QUIC 헤더 포함 · 아래 숫자는 완료 횟수\n'
                'OLIA · 손실률 0 · 버퍼 각각 80,000,000B · 종료 대기 250ms · seed 1~10')
    if s.startswith('4-path operation probe'):
        return ('4경로 동작: 스케줄러가 각 경로에 보낸 데이터 비중\n'
                'seed 1 · 5MiB · OLIA · 손실률 0 · 추가 경로 2개는 각각 8Mbps·편도 지연 20ms')
    if s.startswith('MPQUIC ns-3,'):
        amounts=re.findall(r'([0-9,]+) B',s)
        sizes=[]
        for value in amounts:
            n=int(value.replace(',',''))
            sizes.append(f'{n//1048576}MiB' if n%1048576==0 else f'{n:,}B')
        size_label=' · '.join(sizes) if sizes else '데이터'
        return (f'{size_label} 전송: 스케줄러별 전송 완료 시간 분포\n'
                '주황선: 중앙값 · 초록 삼각형: 평균 · 이름 아래: 완료 횟수/전체 실행 수\n'
                '제한 시각 내 미완료 실행은 시간 분포에서 제외')
    m=re.fullmatch(r'Completed (\d+/\d+)\nExact bytes (\d+/\d+)',s)
    if m: return f'완료 {m[1]}\n전체 수신 {m[2]}'
    m=re.fullmatch(r'(.+)\n(\d+/\d+) · (\d+/\d+)',s)
    if m:
        value='완료 없음' if m[1]=='—' else m[1].removesuffix('s')+'초'
        return f'{value}\n완료 {m[2]}\n전체 수신 {m[3]}'
    m=re.fullmatch(r'(\d+/\d+)\n(\d+/\d+)',s)
    if m:return s if kind=='long_completion' else f'완료 {m[1]}\n전체 수신 {m[2]}'
    m=re.fullmatch(r'(\d+)/(\d+) -> (\d+)/(\d+)',s)
    if m:return f'{m[1]}/{m[2]} → {m[3]}/{m[4]}'
    if s.startswith('path '):return s.replace('path ','경로 ')
    if '\ndone ' in s:
        return s.replace('(new)','').replace('*','').replace('NewSched','ID 7 기본 모드').replace('done ','완료 ').replace(' · full ','\n전체 수신 ').replace('active ','연결된 경로 ')
    m=re.fullmatch(r'([^\n]+)\n(\d+/\d+)',s)
    if m:return m[1].replace('*','')+'\n완료 '+m[2]
    return s.replace('(new)','').replace('*','')

def localize(fig,kind):
    """Replace text only, keeping all plotted samples, bars and heatmap arrays."""
    # Cell edges stay visible even when adjacent cells have the same color.
    if kind in ('degradation','robustness','overview'):
        from matplotlib.collections import LineCollection
        for ax in fig.axes:
            for image in ax.images:
                rows,cols=image.get_array().shape[:2]
                segments=[[(x-.5,-.5),(x-.5,rows-.5)] for x in range(cols+1)]
                segments += [[(-.5,y-.5),(cols-.5,y-.5)] for y in range(rows+1)]
                ax.add_collection(LineCollection(segments,colors='#9eacbd',linewidths=1.0,zorder=2),autolim=False)
    for ax in fig.axes:
        for axis in (ax.xaxis,ax.yaxis):
            labels=[t.get_text() for t in axis.get_ticklabels()]
            translated=[translate_text(t,kind) for t in labels]
            if labels!=translated:
                axis.set_ticklabels(translated)
    for text in fig.findobj(Text):
        text.set_text(translate_text(text.get_text(),kind))
    if kind in ('long_completion','long_path_share','four_path'):
        for ax in fig.axes:
            ax.yaxis.set_major_formatter(PercentFormatter(1))
    if kind=='long_completion':
        for ax in fig.axes:ax.set_ylabel('완료·전체 수신 비율(%)')
    elif kind=='long_path_share':
        for ax in fig.axes:ax.set_ylabel('경로 1 수신 비중(%)')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report',type=Path,default=ROOT/'reports/week4')
    a=ap.parse_args();report=a.report.resolve();data=report/'data';out=report/'figures'
    # A report directory is required: never write into frozen experiment folders.
    if (report/'4주차 진행상황.md').is_file() is False or 'artifacts' in report.parts:
        raise ValueError('Use reports/week4 or its handoff copy; frozen artifacts are read-only.')
    import pandas as pd
    from week4_analyze import plots
    from week4_final_compare import plot_comparison
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob('*.csv')}
    plots(pd.read_csv(data/'results.csv'),pd.read_csv(data/'summary.csv'),out,language='ko')
    plot_comparison(pd.read_csv(data/'final-before-after-conditions.csv'),out/'final_validation.png',language='ko')
    for prefix in ['', 'final-']:
        name='final_robustness_overview.png' if prefix else 'robustness_overview.png'
        subprocess.run([sys.executable,str(ROOT/'sched-lab/plot_week4_overview.py'),str(data/(prefix+'summary.csv')),str(out/name),'--language','ko'],check=True)
        source='final-long-results.csv' if prefix else 'baseline-long.csv'
        name='final_long_fct_provided.png' if prefix else 'long_fct_provided.png'
        subprocess.run([sys.executable,str(ROOT/'sched-lab/analyze.py'),str(data/source),'--language','ko','--plot-only','--output',str(out/name)],check=True)
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.glob('*.csv')}
    assert before==after,'CSV files changed during label rendering'
    record={'language':'ko','csv_files_unchanged':before,'plotting':'Existing plot functions and supplied analyze.py; Korean labels and layout only','font':matplotlib.rcParams['font.family'],'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))}}
    (report/'records/korean-figures.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'figures':len(record['figures']),'unchanged_csv':len(before)},ensure_ascii=False))

if __name__=='__main__':main()
