"""Compatibility entry point using the fixed weekly output convention."""
from pathlib import Path
import subprocess
import sys

if __name__=='__main__':
    subprocess.run([sys.executable,str(Path(__file__).with_name('render_weekly_report.py')),
                    '--week','3','--handoff',*sys.argv[1:]],check=True)
