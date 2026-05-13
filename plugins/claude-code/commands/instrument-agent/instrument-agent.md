---
description: Instrument a new AI agent in a Python codebase for Monte Carlo Agent Observability
---

Activate the Monte Carlo Instrument-Agent skill against the current Python codebase. The skill walks the workflow in `references/workflow.md` — detect AI libraries and runtime via `scripts/detect_libraries.py`, ask self-hosted vs MC-hosted OTel, ask about sensitive data (gates redaction), snapshot existing agents via `get_agent_metadata`, resolve the OTLP endpoint, propose dependency edits, propose `mc.setup()`, propose decorator diffs, confirm env vars, and verify traces flow.

Always proposes diffs and waits for explicit per-file user approval before modifying any file.
