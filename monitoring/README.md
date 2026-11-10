# Observability
Run `python -m autumn.monitor` while the model servers are running.
Local endpoints are /health, /metrics, /traces, and /alerts on 127.0.0.1:9091.
Spans share a trace_id; each node has a span_id, start, end, duration, and errors.
Model events store tier, model, latency, and token usage; retrieval records source IDs.
Questions, full prompts, and source bodies are excluded from telemetry. The SQLite episode store does contain questions and approved answers.
Counters persist across sequential CLI invocations. This prototype supports a single request writer; simultaneous writers need a central metrics collector and database transaction policy.
Alerts are actively emitted to state/telemetry/alerts.jsonl for withheld answers, failed workflows, errors, and nodes over 30 seconds.
No email, Slack, or webhook was configured or contacted. Prometheus scrape and alert rules are provided for later integration; the Prometheus/Alertmanager services were not run.
Rotate JSONL files and apply retention in production. SQLite supports episode deletion per session but has no automatic retention daemon.
