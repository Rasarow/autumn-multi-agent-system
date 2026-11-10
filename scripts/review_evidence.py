"""Read-only browser view of recorded project evidence. No model calls or writes."""

import argparse, html, json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]


def esc(x):
    return html.escape(str(x))


def pre(x):
    return "<pre>" + esc(x) + "</pre>"


def table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join("<th>" + esc(h) + "</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + esc(v) + "</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def page(route):
    evidence = ROOT / "evidence"
    if route == "/models":
        title = "Local model comparison"
        source = "evidence/model_summary.json and evidence/model_benchmark.json"
        rows = json.loads((evidence / "model_summary.json").read_text())
        body = table(
            ["Model", "Passed", "Valid JSON", "Median seconds", "p95 seconds"],
            [
                (
                    r["model"],
                    str(r["passed"]) + "/12",
                    str(r["schema_valid"]) + "/12",
                    f"{r['median_s']:.3f}",
                    f"{r['p95_s']:.3f}",
                )
                for r in rows
            ],
        )
        body += "<h2>Recorded test conditions</h2><p>12 cases per model · one measured repetition · seed 42 · temperature 0 · 180 output tokens · thinking disabled · unconstrained JSON</p>"
        body += table(
            ["Category", "0.8B", "2B", "4B"],
            [
                (
                    c,
                    *[
                        str(r["by_category"][c]["passed"])
                        + "/"
                        + str(r["by_category"][c]["n"])
                        for r in rows
                    ],
                )
                for c in rows[0]["by_category"]
            ],
        )
        body += "<p>The first request includes warmup. This is a small engineering diagnostic, not a general model ranking.</p>"
    elif route == "/checks":
        title = "Contracts and observability"
        source = "evidence/unit_tests.txt, metrics.prom, monitor_smoke.json"
        body = (
            '<div class="columns"><section><h2>Deterministic regression run</h2>'
            + pre((evidence / "unit_tests.txt").read_text())
            + "</section><section><h2>Captured metrics</h2>"
            + pre((evidence / "metrics.prom").read_text())
            + "<h2>Endpoint smoke test</h2>"
            + pre(
                json.dumps(
                    json.loads((evidence / "monitor_smoke.json").read_text()), indent=2
                )
            )
            + "</section></div>"
        )
    else:
        title = "End to end evaluation"
        source = "evidence/system_eval.json"
        data = json.loads((evidence / "system_eval.json").read_text())
        rows = data["cases"]
        body = f'<p class="score">{data["passed"]} / {data["n"]} scenarios passed</p>'
        body += table(
            ["Scenario", "Effective date", "Result", "Pass", "Repairs"],
            [
                (
                    r["case"]["id"],
                    r["case"]["as_of"],
                    r["result"]["status"],
                    "PASS" if r["passed"] else "FAIL",
                    r["result"]["repairs"],
                )
                for r in rows
            ],
        )
        body += (
            '<div class="columns"><section><h2>Approved answer</h2>'
            + pre(json.dumps(rows[0]["result"], indent=2))
            + "</section><section><h2>Historical case requiring work</h2>"
            + pre(json.dumps(rows[2]["result"], indent=2))
            + "</section></div>"
        )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><title>Autumn evidence review</title><style>
    *{box-sizing:border-box}body{margin:0;background:#fff;color:#17212c;font:17px/1.45 'Segoe UI',Arial,sans-serif}main{max-width:1550px;margin:auto;padding:28px 40px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #d6dee5;padding-bottom:14px}header strong{font-size:21px}nav a{margin-left:22px;color:#174a76;text-decoration:none}h1{font-size:34px;margin:24px 0 8px}h2{font-size:20px;margin:20px 0 8px}.source{color:#586878;font-size:15px}.score{font-size:24px;margin:14px 0}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #d7dfe5;padding:9px 14px;text-align:left}th{background:#eaf0f5}tbody tr:nth-child(even){background:#f8fafb}.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}section{min-width:0}pre{font:14px/1.4 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0;background:#f5f7f9;border:1px solid #e0e6eb;padding:14px}.notice{font-size:14px;color:#566675;margin-top:20px}</style><main><header><strong>Autumn evidence review</strong><nav><a href="/">System run</a><a href="/models">Models</a><a href="/checks">Checks and metrics</a></nav></header>"""
        + f'<h1>{title}</h1><p class="source">Recorded evidence · {source}</p>'
        + body
        + '<p class="notice">Read-only view of saved measurements. This page does not run inference and does not imply that model servers are currently running.</p></main></html>'
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ["/", "/models", "/checks"]:
                self.send_error(404)
                return
            data = page(self.path).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    print(f"Recorded evidence viewer: http://127.0.0.1:{a.port}", flush=True)
    HTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
