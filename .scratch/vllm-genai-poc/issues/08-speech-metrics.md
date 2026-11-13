# 08: Speech metrics

**What to build:** The STT and TTS servers expose `/metrics`. Prometheus shows them as up, and Grafana shows their request latency.

**Blocked by:** 05, 07

**Status:** ready-for-agent

**Test status:** `/metrics` on both servers tested in Docker on a Mac. On WSL2 on 2026-11-13, Prometheus showed both `speech` targets up, and the dashboard has the row "Speech (STT and TTS)". The smoke test of ticket 14 passed the round trip ("hello world"). In Grafana the row "Speech (STT and TTS)" shows the request rate (a spike for the smoke test and one for a read-aloud click in Open WebUI) and the STT and TTS latency.

- [x] STT and TTS expose request count and latency histograms on `/metrics`
- [x] Prometheus scrapes both; targets up
- [x] Dashboard has a speech row (request rate, p50/p99 latency for transcription and synthesis)
- [x] A TTS to STT round trip shows in the panels
