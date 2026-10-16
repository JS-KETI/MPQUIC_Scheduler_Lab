"""Render an edited weekly Markdown report without rewriting its contents."""
from pathlib import Path
import argparse
import base64
import hashlib
import html
import json
import mimetypes
import re
import shutil
from markdown_it import MarkdownIt

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--week',type=int,required=True)
    ap.add_argument('--source',type=Path)
    ap.add_argument('--handoff',action='store_true',help='Copy HTML to the fixed Windows outputs/weekN directory')
    args=ap.parse_args()
    if args.week<1:ap.error('--week must be positive')
    repo=Path(__file__).resolve().parents[1]
    name=f'{args.week}주차 진행상황'
    source=args.source or repo/f'reports/week{args.week}/{name}.md'
    root=source.resolve().parent
    original=source.read_bytes()
    text=original.decode('utf-8-sig')
    handoff=None
    if args.handoff:
        handoff=Path('/mnt/c/Users/okqkf/OneDrive/Desktop/keti/outputs')/f'week{args.week}'
        other=handoff/source.name
        if not other.exists() or other.read_text(encoding='utf-8-sig')!=text:
            raise ValueError('Windows Markdown differs: render the edited file with --source; do not overwrite it')
    images=[]
    def embed(m):
        target=m.group(2).strip('<>')
        if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target):
            raise ValueError(f'Use a portable relative image path: {target}')
        p=(root/target).resolve()
        if not p.is_relative_to(root):raise ValueError('Image is outside the weekly report directory')
        data=p.read_bytes()
        mime=mimetypes.guess_type(p.name)[0]
        if mime not in ('image/png','image/jpeg','image/svg+xml','image/webp'):raise ValueError('Unsupported image')
        images.append({'path':target,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        return f'![{m.group(1)}](data:{mime};base64,{base64.b64encode(data).decode()})'
    md=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',embed,text)
    md=re.sub(r'(?m)^(\s*-\s+)(https://\S+)$',r'\1<\2>',md)
    md=re.sub(r'(?m)^(\s*-\s+.+?:\s+)(https://[^\s<>)]+)$',r'\1<\2>',md)
    parser=MarkdownIt('commonmark',{'html':True}).enable('table')
    body=parser.render(md)
    style='body{max-width:1100px;margin:30px auto;padding:0 20px;font:15px/1.6 "Malgun Gothic",sans-serif;color:#203344}h2{background:#e5f1e9;padding:8px 12px;margin-top:28px}h3{background:#e8eff7;padding:7px 10px}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #cbd5df;padding:7px;vertical-align:top}th{background:#f0f4f7}li{margin:3px 0}code{font:12px Consolas,monospace;overflow-wrap:anywhere}a{overflow-wrap:anywhere}'
    rendered='<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>'+html.escape(name)+'</title><style>'+style+'</style></head><body>'+body+'</body></html>'
    assert source.read_bytes()==original,'Source changed during rendering'
    assert [t.tag for t in parser.parse(text) if t.type=='heading_open']==re.findall(r'<(h[1-6])>',body)
    assert len(re.findall(r'<img[^>]+src="data:image/',body))==len(images)
    dest=source.with_suffix('.html')
    dest.write_text(rendered,encoding='utf-8')
    validation={'week':args.week,'source_markdown_sha256':hashlib.sha256(original).hexdigest(),'html_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'images':images,'heading_count':len(re.findall(r'<h[1-6]>',body)),'tables':body.count('<table>'),'clickable_links':body.count('<a href='),'source_unchanged':True,'all_report_images_embedded':True}
    record=root/'records/render.json';record.parent.mkdir(parents=True,exist_ok=True)
    record.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    if args.handoff:
        if dest.resolve()!=(handoff/dest.name).resolve():shutil.copy2(dest,handoff/dest.name)
        if record.resolve()!=(handoff/'records/render.json').resolve():shutil.copy2(record,handoff/'records/render.json')
    print(json.dumps({'week':args.week,'images':len(images),'headings':validation['heading_count'],'source_unchanged':True,'html':str(dest)},ensure_ascii=False))

if __name__=='__main__':main()
