# Autumn local evidence multi agent system

Repository: https://github.com/Rasarow/autumn-multi-agent-system

## Recorded results

The three-model diagnostic passed 6/12 cases for 0.8B, 11/12 for 2B, and 10/12 for 4B.
The complete system passed 7/8 scenarios. The failed historical case is a verifier error about the validity interval;
it returned no claims after one repair. Fourteen deterministic regression tests pass.
Docker configuration is supplied but has not been executed on the measured host.

Open the single submission report in docs/Autumn_Multi_Agent_Project_Report.docx for the complete solution process,
architecture, stack, screenshots, code excerpts, repository links, measurements, and conclusions.

Autumn answers questions about a small fictional operations handbook using local open-weight LLMs.
A planner, evidence researcher, writer, and independent verifier share a bounded LangGraph workflow.
The output is a set of exact source quotations with identifiers, or an explicit abstention.

## Included

- English technical report in docs/report.md and the separately delivered Word document.
- Working graph, three model routes, actual system prompts, skill files, and identity and memory contracts.
- Seven dated handbook fixtures, SQLite FTS5 memory, provenance checks, and one bounded repair.
- Real three-model benchmark, raw responses, real end-to-end evaluation, and deterministic regression tests in evidence/.
- Windows resource-isolated launcher; Docker files prepared for a stronger deployment boundary.
- Mermaid C4 and sequence diagrams, local metrics, correlated traces, logs, and file alerts.

## Measured environment

Windows, Intel Core i5-12500H, 15.7 GiB system RAM, RTX 4060 Laptop 8 GiB VRAM.
llama.cpp b12110 Vulkan, Qwen3.5 0.8B / 2B / 4B Q4_K_M, 4096-token runtime context, one inference slot per server.
See artifact_manifest.json for exact download URLs, Hugging Face revisions, file sizes, and SHA256 checksums.
Model files total about 4.55 GB in decimal units. Downloads and the runtime are excluded from the ZIP.

## Windows quick start

From the extracted project folder, in PowerShell with Python 3.12 installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_assets.py
powershell -NoProfile -File scripts\start_models.ps1
Invoke-RestMethod http://127.0.0.1:8181/health
Invoke-RestMethod http://127.0.0.1:8182/health
Invoke-RestMethod http://127.0.0.1:8183/health
.\.venv\Scripts\python.exe scripts\run_isolated.py "How long is backup retention?"
.\.venv\Scripts\python.exe scripts\run_isolated.py --as-of 2026-08-31 "How long is backup retention?"
```

Wait until all three health endpoints report ok. Vulkan0 must be the dedicated GPU; use the runtime's --list-devices if needed.
If GPU capacity is insufficient, stop all project model servers before changing their launch configuration.
CPU operation can use -ngl 0 and no --device argument; its performance was not benchmarked.

## Evaluate

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe evals\benchmark.py
.\.venv\Scripts\python.exe evals\system_eval.py
.\.venv\Scripts\python.exe -m autumn.monitor
```

Open http://127.0.0.1:9091/metrics, /traces, or /alerts. The monitor serves local state only.
The benchmark uses 12 diagnostics per model with unconstrained JSON and deterministic grading.
The system evaluation uses eight scenarios and the isolated launcher. It records exact outputs and isolation assignment.
Use a fresh AUTUMN_STATE directory to avoid recalling earlier evaluation sessions when reproducing a run.
Live model results can vary by runtime, hardware, quantization, and numerical kernels despite a fixed seed.

To review the recorded results in a browser without loading a model:

```powershell
.\.venv\Scripts\python.exe scripts\review_evidence.py
```

Open http://127.0.0.1:8765. The three read-only pages display the saved system run, model comparison,
regression output, and monitoring captures. These are recorded results, not live inference.

## Memory and maintenance

```powershell
.\.venv\Scripts\python.exe -m autumn.cli ingest
.\.venv\Scripts\python.exe -m autumn.cli forget demo
powershell -NoProfile -File scripts\stop_models.ps1
```

Source edits become active after ingest. Reingestion removes deleted records and replaces the index transactionally.
valid_from is inclusive; valid_to is exclusive. The CLI defaults to the submission date 2026-11-10; set --as-of for another date.
Keep only trusted administrator-maintained source files in data/. The malicious note is explicitly an adversarial test fixture.

## Isolation status

The measured runs used a Python -I child plus a verified Windows Job Object: 2 GiB process memory,
one active process, 60 CPU seconds, 120 wall-clock seconds. Only allowlisted source-reading tools exist.
This is resource and dependency isolation. It does not deny host filesystem or outbound network access at the OS level.
Do not treat it as a security boundary for untrusted code or other users. The agents have no code-execution tool.

For a Docker host, `python scripts/download_assets.py --models-only`, then `docker compose build` and
`docker compose up -d llm-small llm-medium llm-large`. Wait for the three servers to become ready in logs,
then `docker compose run --rm agent ask "How long is backup retention?"`.
The prepared CPU topology has an internal network, unprivileged users, read-only roots, dropped capabilities,
resource limits, and no published model ports. Docker was absent on the measured host, so this path is unverified.
The base images and package repository are not digest-pinned; resolve digests and scan builds before production.

## Boundaries

The corpus and diagnostic set are intentionally small. These results are not general intelligence, safety, or production-readiness claims.
The three models are different sizes of one family, not independent families. Their errors may be correlated.
An independent verifier role is a separate model call and prompt, not statistical independence or a second vendor.
Exact quotation checks prove source matching, not source truth or relevance. The verifier supplies a fallible relevance check.
The optional undefined Jev-like item is documented in docs/optional_jev.md with the user's confirmed interpretation boundary.

Source code is original for this project. Third-party frameworks and model files retain their own licenses.
