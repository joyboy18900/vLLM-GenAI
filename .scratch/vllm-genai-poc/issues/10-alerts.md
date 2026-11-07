# 10: Alerts with Alertmanager

**What to build:** Alertmanager receives alerts from Prometheus rules. The user sees active alerts when a target is down, when vLLM preempts requests, or when the GPU is too hot.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Alertmanager deployed, image pinned, connected to Prometheus
- [ ] Rules stored as code: any scrape target down, vLLM preemptions above zero, GPU temperature too high, KV cache usage near full
- [ ] One alert is triggered on purpose (for example, scale a target to zero) and shows as firing, then resolves
- [ ] The setup runbook has the check steps
