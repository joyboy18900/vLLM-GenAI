# 07: Core monitoring

**What to build:** The user opens Grafana (with a login) and sees a serving dashboard for vLLM, the GPU, and the cluster: latency, throughput, KV cache, queue, preemptions, GPU health, CPU, RAM, disk, and pod state.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13. All 7 targets up. All 36 dashboard queries and the 4 alert rules use metric names that exist on the live Prometheus (checked by script), and the vLLM counters moved after 12 chat requests. Not ticked: the panels were not looked at in a browser. On WSL2, `node-exporter` needs `mount --make-rshared /` (see `docs/setup.md`).

- [x] Monitoring namespace with Prometheus, Grafana, DCGM exporter, Node Exporter, and kube-state-metrics, all images pinned
- [x] DCGM exporter reads GPU metrics without a GPU request
- [x] Prometheus scrapes vLLM, DCGM, Node Exporter, kube-state-metrics, and itself; all targets up
- [x] Prometheus and Grafana data on PersistentVolumeClaims
- [x] Grafana requires a login (no anonymous admin)
- [x] Dashboard stored as code in the repository and provisioned at start, with rows: SLO (TTFT, TPOT, E2E, throughput, finish reasons, queue), saturation (KV cache, running vs waiting, preemptions, prefix cache hit rate, batch size, spec-decode acceptance), GPU (temperature, utilization, power, VRAM, clocks), node and pods (CPU, RAM, disk, pod state)
- [ ] Panels move when a few chat requests are sent
- [x] The setup runbook has the deploy and access steps
