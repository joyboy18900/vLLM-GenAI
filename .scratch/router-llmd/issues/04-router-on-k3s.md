# 04: Deploy the router on k3s

**What to build:** The router runs as a Deployment on k3s with its own Service, a ServiceAccount, and a Role that can only read pods and change the scale of the two AWQ Deployments. Open WebUI uses the router.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** ran on WSL2 on 2026-11-14. The image was built on the PC and imported. The manifest passes `kubeconform -strict`. The router read both pool pods from the Kubernetes API (`/router/stats`), answered chat requests with the header `X-Routed-Pod`, and Open WebUI (set with `kubectl set env`) reached `http://router:8000/v1/models` and `/chat/completions` from its own pod. With pod `a` at zero replicas the router answered through `b` and `/health` showed 1 ready pod; pod `a` came back and joined the pool. Prometheus shows both pool pods up (`up{job="vllm",variant="awq"}`). Not tested: a chat in the browser (the box stays open). `k8s/open-webui-deployment.yaml` keeps the Service `vllm` as the default, and the switch is a `kubectl set env` command in the runbook. The PC now runs the pool and the router, and the fp16 pod is at zero replicas.

- [x] Image built on the PC and imported into k3s (`docker save`), no registry
- [x] ServiceAccount, Role, and RoleBinding limited to pods and the scale of `vllm-awq-a` and `vllm-awq-b`; the manifest passes `kubeconform -strict`
- [ ] Open WebUI `OPENAI_API_BASE_URL` points to the router Service; a chat in the browser works and the header shows the pod
- [x] A stopped pod leaves the pool and the chat still works through the other pod
- [x] Pointing Open WebUI back to the Service `vllm` restores the single pod (the way back is in the runbook)
- [x] The setup runbook has the deploy and check steps
