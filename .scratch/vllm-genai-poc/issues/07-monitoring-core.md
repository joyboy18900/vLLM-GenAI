# 07: Core monitoring

**What to build:** The user opens Grafana (with a login) and sees a serving dashboard for vLLM, the GPU, and the cluster: latency, throughput, KV cache, queue, preemptions, GPU health, CPU, RAM, disk, and pod state.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Monitoring namespace with Prometheus, Grafana, DCGM exporter, Node Exporter, and kube-state-metrics, all images pinned
- [ ] DCGM exporter reads GPU metrics without a GPU request
- [ ] Prometheus scrapes vLLM, DCGM, Node Exporter, kube-state-metrics, and itself; all targets up
- [ ] Prometheus and Grafana data on PersistentVolumeClaims
- [ ] Grafana requires a login (no anonymous admin)
- [ ] Dashboard stored as code in the repository and provisioned at start, with rows: SLO (TTFT, TPOT, E2E, throughput, finish reasons, queue), saturation (KV cache, running vs waiting, preemptions, prefix cache hit rate, batch size, spec-decode acceptance), GPU (temperature, utilization, power, VRAM, clocks), node and pods (CPU, RAM, disk, pod state)
- [ ] Panels move when a few chat requests are sent
- [ ] The setup runbook has the deploy and access steps
