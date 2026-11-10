import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--deps'); p.add_argument('--session',default='demo'); p.add_argument('--as-of',default='2026-11-10'); p.add_argument('question'); a=p.parse_args()
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from autumn.isolation import apply_limits
isolation=apply_limits()  # Before loading third-party packages or agent code.
if a.deps: sys.path.insert(0,str(Path(a.deps).resolve()))
from autumn.core import run
result=run(a.question,session=a.session,as_of=a.as_of); result['isolation']=isolation
print(json.dumps(result,indent=2))
