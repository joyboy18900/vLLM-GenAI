# 04: Deploy the router on k3s

**What to build:** The router runs as a Deployment on k3s with its own Service, a ServiceAccount, and a Role that can only read pods and change the scale of the two AWQ Deployments. Open WebUI uses the router.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** not started.

- [ ] Image built on the PC and imported into k3s (`docker save`), no registry
- [ ] ServiceAccount, Role, and RoleBinding limited to pods and the scale of `vllm-awq-a` and `vllm-awq-b`; the manifest passes `kubeconform -strict`
- [ ] Open WebUI `OPENAI_API_BASE_URL` points to the router Service; a chat in the browser works and the header shows the pod
- [ ] A stopped pod leaves the pool and the chat still works through the other pod
- [ ] Pointing Open WebUI back to the Service `vllm` restores the single pod (the way back is in the runbook)
- [ ] The setup runbook has the deploy and check steps
