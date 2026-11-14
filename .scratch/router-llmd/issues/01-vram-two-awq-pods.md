# 01: Measure two AWQ pods on one GPU

**What to build:** Two AWQ vLLM pods run at the same time on the one GPU. The real VRAM use and the KV cache of each pod are measured and written down before any router manifest is written.

**Blocked by:** None (can start when the PC is on)

**Status:** ready-for-agent

**Test status:** done on WSL2 on 2026-11-14. Two pods at 0.40 start and answer (72,832 tokens of KV cache each, 10851 MiB of GPU in total). The second pod was `Pending` until the device plugin got time-slicing (`k8s/nvidia-device-plugin.yaml`, `nvidia.com/gpu: 3`). A third pod at 0.29 did not start (`No available memory for the cache blocks`), and other shares were not tested. The Service `vllm` now selects `variant: fp16`. Numbers are in `docs/benchmarks.md`. Not checked: the Prometheus targets of the pool pods (the label `app: vllm` matches the `vllm` job by its rule, but the pods were not scraped in this run).

- [x] Two Deployments, `vllm-awq-a` and `vllm-awq-b`, each with a share of `--gpu-memory-utilization`, start one after the other and both become ready (the fp16 `baseline` pod is scaled to zero first)
- [x] VRAM of each pod, KV cache (tokens and concurrency), and the VRAM left on the GPU are recorded in `docs/benchmarks.md`
- [x] The result says if a third pod fits, and the shares that were tested
- [ ] The label of the pods matches the `vllm` job of Prometheus, and both targets are up
- [x] The setup runbook has the commands and the check steps
