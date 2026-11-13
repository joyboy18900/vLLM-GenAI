# 14: Full smoke test

**What to build:** One `curl`-based script checks the whole stack in about one minute and prints pass or fail for each check.

**Blocked by:** 06, 08, 09, 10, 11

**Status:** ready-for-agent

**Test status:** ran on k3s in WSL2 on 2026-11-13 with `--no-https`: all 10 checks passed (first with the earlier flags, then again with the final flags of ticket 13). The HTTPS checks are not run (no Ingress on WSL2). The pass and fail logic ran with a fake `curl` on a Mac. The script is in `bench/smoke_test.sh` (no new top-level folder).

- [x] vLLM chat completion returns a non-empty answer
- [x] TTS to STT round trip returns "hello world"
- [ ] Open WebUI and Grafana answer over HTTPS through the Ingress
- [x] Prometheus reports vLLM, STT, TTS, DCGM, Node Exporter, and kube-state-metrics targets as up
- [x] Loki and Alertmanager report ready
- [ ] The script exits non-zero when any check fails
- [ ] The setup runbook and README draft notes say how to run it
