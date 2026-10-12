from pathlib import Path
import re,base64,shutil,json
from markdown_it import MarkdownIt
r=Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic/reports/week3')
source=(r/'3주차 진행상황.md').read_text()
def embed(m):
    f=r/m.group(2);assert f.exists()
    return f'![{m.group(1)}](data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode()+')'
md=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',embed,source)
parser=MarkdownIt('commonmark',{'html':True}).enable('table');body=parser.render(md)
html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>3주차 진행상황</title><style>body{max-width:1100px;margin:30px auto;padding:0 20px;font:15px/1.6 "Malgun Gothic",sans-serif;color:#203344}h2{background:#e5f1e9;padding:8px 12px;margin-top:28px}h3{background:#e8eff7;padding:7px 10px}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #cbd5df;padding:7px;vertical-align:top}th{background:#f0f4f7}li{margin:3px 0}code{font:12px Consolas,monospace;overflow-wrap:anywhere}a{overflow-wrap:anywhere}</style></head><body>'+body+'</body></html>'
p=r/'3주차 진행상황.html';p.write_text(html)
shutil.copyfile(p,Path('/mnt/c/Users/okqkf/OneDrive/Desktop/keti/outputs/week3-2026-10-12')/p.name)
assert html.count('data:image/png;base64,')==2
assert [t.tag for t in parser.parse(source) if t.type=='heading_open']==['h2' if x=='h2' else 'h3' for x in re.findall(r'<(h[23])>',body)]
assert '<title>3주차 진행상황</title>' in html
print(json.dumps(dict(embedded_images=2,headings=len(re.findall(r'<h[23]>',body)),tables=body.count('<table>'),html_bytes=len(html.encode()),markdown_unchanged=True)))
