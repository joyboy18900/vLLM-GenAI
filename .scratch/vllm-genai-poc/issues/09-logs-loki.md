# 09: Logs with Loki

**What to build:** Logs from every pod go to Loki. The user searches vLLM, STT, TTS, and Open WebUI logs in Grafana.

**Blocked by:** 07

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13. The Loki API returned lines for `{app="vllm"}`, `{app="stt"}`, `{app="tts"}`, and `{app="open-webui"}`. Not ticked: the search in the Explore page of Grafana was not done.

- [x] Loki and a log collector deployed, images pinned, Loki data on a PersistentVolumeClaim with a retention limit
- [x] Loki added as a Grafana data source by provisioning
- [ ] A search in Grafana returns recent log lines from the `vllm` pod
- [x] The setup runbook has the deploy and check steps
