# 04: Open WebUI text chat

**What to build:** Open WebUI runs in the cluster and uses the `vllm` Service. The user opens it in a browser (through an SSH tunnel from the Mac to `localhost`) and has a streamed text chat with Qwen2.5-3B-Instruct.

**Blocked by:** 03

**Status:** ready-for-agent

**Test status:** deployed on WSL2 on 2026-11-08. The pod is ready and `/health` returns 200 through the Service. The chat in the browser and the restart check are not tested. No box is ticked.

- [ ] Open WebUI image pinned to a version
- [ ] Configured by environment variables to use the `vllm` Service; Ollama off; first boot kept light (no auto model updates, no web search)
- [ ] ClusterIP Service named `webui`, plus a NodePort for the SSH tunnel path
- [ ] Data (chat history, settings) on a PersistentVolumeClaim; history survives a pod restart
- [ ] A text chat in the browser streams the answer token by token
- [ ] The setup runbook has the deploy steps and the SSH tunnel command
