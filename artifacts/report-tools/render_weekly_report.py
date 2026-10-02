#!/usr/bin/env python3
"""Render the weekly Markdown report as standalone HTML with embedded figures."""
import argparse
import base64
import html
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote

REPO_FILES = "https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/week1/"


def inline(text):
    pattern = r"(`[^`]+`|\*\*.+?\*\*|\[[^\]]+\]\([^)]+\))"
    result = []
    for part in re.split(pattern, text):
        if part.startswith("`") and part.endswith("`"):
            result.append("<code>" + html.escape(part[1:-1]) + "</code>")
        elif part.startswith("**") and part.endswith("**"):
            result.append("<strong>" + html.escape(part[2:-2]) + "</strong>")
        else:
            link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", part)
            if link:
                label, url = link.groups()
                if not url.startswith(("https://", "http://")):
                    url = REPO_FILES + quote(url, safe="/")
                result.append(html.escape(label + " : " + url))
            else:
                result.append(html.escape(part))
    return "".join(result)


def render_lines(lines, root):
    result, index = [], 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        image = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if heading:
            level, title = len(heading[1]), heading[2]
            result.append(f"<h{level}>" + inline(title) + f"</h{level}>")
        elif image:
            caption, source = image.groups()
            path = (root / source).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Figure must be inside report directory")
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            result.append('<figure><img alt="' + html.escape(caption, quote=True) + '" src="data:' + mime + ';base64,' + data + '"><figcaption>' + html.escape(caption) + '</figcaption></figure>')
        elif line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                index += 1
            header = "".join("<th>" + inline(c) + "</th>" for c in rows[0])
            body = "".join("<tr>" + "".join("<td>" + inline(c) + "</td>" for c in row) + "</tr>" for row in rows[1:])
            result.append('<div class="table-wrap"><table><thead><tr>' + header + '</tr></thead><tbody>' + body + '</tbody></table></div>')
            continue
        elif line.startswith("- "):
            result.append("<ul>")
            while index < len(lines) and lines[index].startswith("- "):
                result.append("<li>" + inline(lines[index][2:]))
                index += 1
                children = []
                while index < len(lines) and lines[index].startswith("  - "):
                    children.append("<li>" + inline(lines[index][4:]) + "</li>")
                    index += 1
                if children:
                    result.append('<ul class="detail">' + "".join(children) + "</ul>")
                result.append("</li>")
            result.append("</ul>")
            continue
        else:
            result.append("<p>" + inline(line) + "</p>")
        index += 1
    return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", "--artifacts-root", dest="report_root", type=Path, default=Path(__file__).resolve().parents[2] / "reports" / "week1")
    parser.add_argument("--name", default="1주차 진행상황", help="Report file stem and HTML title")
    args = parser.parse_args()
    if Path(args.name).name != args.name:
        parser.error("--name must be a file stem, not a path")
    global REPO_FILES
    REPO_FILES = "https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/" + args.report_root.name + "/"
    root = args.report_root.resolve()
    source = root / (args.name + ".md")
    body = render_lines(source.read_text(encoding="utf-8").splitlines(), root)
    style = """
    * { box-sizing: border-box; } body { margin: 0; background: #eef2f4; color: #17252e; font-family: 'Malgun Gothic','Noto Sans KR',sans-serif; font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }
    main { max-width: 960px; margin: 24px auto; padding: 28px 36px; background: white; box-shadow: 0 2px 14px #0001; }
    h1 { font-size: 23px; margin: 0 0 10px; } h2 { font-size: 17px; margin: 25px 0 12px; padding: 9px 12px; background: #e4f1e9; border-left: 4px solid #38845b; }
    h3 { font-size: 14px; margin: 18px 0 10px; padding: 7px 10px; background: #e9f1fa; border-left: 3px solid #5682b2; }
    p { margin: 8px 0; } ul { margin: 7px 0; padding-left: 20px; } li { margin: 4px 0; } ul.detail { margin: 5px 0 9px; }
    li:has(ul.detail)>strong { background: #fff2c5; padding: 2px 5px; } code { font-family: Consolas,monospace; font-size: .96em; background: #f0f3f6; padding: 1px 4px; border-radius: 3px; }
    a { color: #245f93; } table { border-collapse: collapse; width: 100%; font-size: 12px; } th, td { border: 1px solid #d8e0e5; padding: 6px 8px; text-align: left; vertical-align: top; } th { background: #f2f5f8; } .table-wrap { overflow-x: auto; }
    figure { margin: 10px 0 8px; text-align: center; } img { display: block; width: 100%; height: auto; margin: auto; } figcaption { font-size: 11px; color: #657380; margin-top: 5px; }
    @media(max-width: 650px) { main { margin: 0; padding: 18px; } body { font-size: 12px; } }
    @media print { body { background: white; } main { max-width: none; margin: 0; padding: 0; box-shadow: none; } h2,h3,figure,table { break-inside: avoid; } }
    """
    output = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(args.name) + '</title><style>' + style + '</style></head><body><main>' + body + '</main></body></html>\n'
    target = root / (args.name + ".html")
    target.write_text(output, encoding="utf-8", newline="\n")
    print(f"Created {target.name}: {len(output.encode('utf-8'))} bytes, {body.count('<figure>')} embedded figures")


if __name__ == "__main__":
    main()
