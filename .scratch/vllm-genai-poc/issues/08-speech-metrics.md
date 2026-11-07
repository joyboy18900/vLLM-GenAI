# 08: Speech metrics

**What to build:** The STT and TTS servers expose `/metrics`. Prometheus shows them as up, and Grafana shows their request latency.

**Blocked by:** 05, 07

**Status:** ready-for-agent

- [ ] STT and TTS expose request count and latency histograms on `/metrics`
- [ ] Prometheus scrapes both; targets up
- [ ] Dashboard has a speech row (request rate, p50/p99 latency for transcription and synthesis)
- [ ] A TTS to STT round trip shows in the panels
