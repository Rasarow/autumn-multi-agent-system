import argparse, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--python", default=sys.executable)
p.add_argument("--deps")
p.add_argument("--session", default="demo")
p.add_argument("--as-of", default="2026-11-10")
p.add_argument("question")
a = p.parse_args()
cmd = [
    a.python,
    "-I",
    "-X",
    "utf8",
    str(Path(__file__).with_name("isolated_worker.py")),
    "--session",
    a.session,
    "--as-of",
    a.as_of,
]
if a.deps:
    cmd += ["--deps", str(Path(a.deps).resolve())]
cmd += [a.question]
try:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    print(result.stdout, end="")
    if result.returncode:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
except subprocess.TimeoutExpired:
    print('{"status":"error","reason":"wall_clock_budget_exceeded","claims":[]}')
    sys.exit(1)
