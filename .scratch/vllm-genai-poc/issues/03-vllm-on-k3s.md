# 03: vLLM on k3s

**What to build:** vLLM runs as a k3s Deployment behind a ClusterIP Service named `vllm`. A pod in the cluster gets a chat completion through the Service.

**Blocked by:** 02

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-13 with Qwen2.5-3B-Instruct. The pod became ready, the Service answered from a pod in the cluster (`/v1/models`, chat, stream, tool call), and a restart came back without a new download. `/dev/shm` in the pod is a 2.0G tmpfs. Not ticked: the flags (they wait for the benchmark of ticket 13) and the startup window (the first download did not fit in 10 minutes, see `docs/setup.md`, "Download the model first"). Numbers are in `docs/benchmarks.md`.

- [ ] Deployment uses the flags chosen in ticket 02, requests one GPU, uses the `nvidia` RuntimeClass and the Recreate strategy
- [x] Service links disabled on the pod (prevents the `VLLM_PORT` collision)
- [x] Model and compile caches on a PersistentVolumeClaim (k3s local-path), so a restart does not download again
- [x] Shared-memory volume mounted
- [ ] Startup, readiness, and liveness probes on `/health`, with a startup window long enough for a cold start
- [x] `curl` from a pod in the cluster to the `vllm` Service returns a chat completion
- [x] A pod restart comes back ready without a new model download
- [x] The setup runbook has the deploy and check steps
