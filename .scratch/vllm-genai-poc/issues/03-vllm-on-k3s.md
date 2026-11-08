# 03: vLLM on k3s

**What to build:** vLLM runs as a k3s Deployment behind a ClusterIP Service named `vllm`. A pod in the cluster gets a chat completion through the Service.

**Blocked by:** 02

**Status:** ready-for-agent

**Test status:** applied on WSL2 on 2026-11-08. The Deployment, Service, and PVC were created. The result of the pod start was not seen (the SSH connection dropped). No box is ticked. Memory flags measured in ticket 02.

- [ ] Deployment uses the flags chosen in ticket 02, requests one GPU, uses the `nvidia` RuntimeClass and the Recreate strategy
- [ ] Service links disabled on the pod (prevents the `VLLM_PORT` collision)
- [ ] Model and compile caches on a PersistentVolumeClaim (k3s local-path), so a restart does not download again
- [ ] Shared-memory volume mounted
- [ ] Startup, readiness, and liveness probes on `/health`, with a startup window long enough for a cold start
- [ ] `curl` from a pod in the cluster to the `vllm` Service returns a chat completion
- [ ] A pod restart comes back ready without a new model download
- [ ] The setup runbook has the deploy and check steps
