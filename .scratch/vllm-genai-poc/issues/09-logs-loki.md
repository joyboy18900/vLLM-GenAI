# 09: Logs with Loki

**What to build:** Logs from every pod go to Loki. The user searches vLLM, STT, TTS, and Open WebUI logs in Grafana.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Loki and a log collector deployed, images pinned, Loki data on a PersistentVolumeClaim with a retention limit
- [ ] Loki added as a Grafana data source by provisioning
- [ ] A search in Grafana returns recent log lines from the `vllm` pod
- [ ] The setup runbook has the deploy and check steps
