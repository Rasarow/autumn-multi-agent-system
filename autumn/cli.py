import argparse,json,os
from pathlib import Path
from .core import run,Memory,ROOT
def main():
    p=argparse.ArgumentParser(description='Autumn local evidence assistant')
    sub=p.add_subparsers(dest='command',required=True)
    ask=sub.add_parser('ask'); ask.add_argument('question'); ask.add_argument('--session',default='demo'); ask.add_argument('--as-of',default='2026-11-10')
    sub.add_parser('ingest')
    forget=sub.add_parser('forget'); forget.add_argument('session')
    args=p.parse_args(); state=Path(os.environ.get('AUTUMN_STATE',ROOT/'state'))
    if args.command=='ask': print(json.dumps(run(args.question,session=args.session,as_of=args.as_of),indent=2))
    else:
        m=Memory(state/'memory.db')
        if args.command=='ingest': print(json.dumps({'sections':m.ingest(ROOT/'data')}))
        else: m.forget(args.session); print('{"deleted":true}')
if __name__=='__main__': main()
