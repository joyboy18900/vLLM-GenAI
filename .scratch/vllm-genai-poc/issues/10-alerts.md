# 10: Alerts with Alertmanager

**What to build:** Alertmanager receives alerts from Prometheus rules. The user sees active alerts when a target is down, when vLLM preempts requests, or when the GPU is too hot.

**Blocked by:** 07

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13. The runbook check passed: scaling `kube-state-metrics` to zero made `TargetDown` fire after about 100 s, Alertmanager listed it as active, and both were empty about 20 s after the restore. A pod from pod discovery (vLLM, STT, TTS) gives no alert when scaled to zero, as the runbook says.

- [x] Alertmanager deployed, image pinned, connected to Prometheus
- [x] Rules stored as code: any scrape target down, vLLM preemptions above zero, GPU temperature too high, KV cache usage near full
- [x] One alert is triggered on purpose (for example, scale a target to zero) and shows as firing, then resolves
- [x] The setup runbook has the check steps
