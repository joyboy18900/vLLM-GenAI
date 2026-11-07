# 14: Full smoke test

**What to build:** One `curl`-based script checks the whole stack in about one minute and prints pass or fail for each check.

**Blocked by:** 06, 08, 09, 10, 11

**Status:** ready-for-agent

- [ ] vLLM chat completion returns a non-empty answer
- [ ] TTS to STT round trip returns "hello world"
- [ ] Open WebUI and Grafana answer over HTTPS through the Ingress
- [ ] Prometheus reports vLLM, STT, TTS, DCGM, Node Exporter, and kube-state-metrics targets as up
- [ ] Loki and Alertmanager report ready
- [ ] The script exits non-zero when any check fails
- [ ] The setup runbook and README draft notes say how to run it
