# 01: PC as a GPU node

**What to build:** The Ubuntu PC becomes a single-node k3s cluster that can schedule pods on the RTX 4070 SUPER. A test pod that requests one GPU runs `nvidia-smi` and shows the card.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Test status:** written, untested. The manifests pass kubeconform and the image tags exist. The PC runs Windows now: install Ubuntu again first. No box is ticked.

Notes:
- The agent works from the Mac. The user runs the commands that need `sudo` on the PC, or gives the agent SSH access first.
- Record the PC spec (CPU, RAM, GPU, disk, OS version, driver version) in the setup runbook.

- [ ] NVIDIA driver installed, `nvidia-smi` shows the RTX 4070 SUPER on the host
- [ ] NVIDIA Container Toolkit installed and detected by k3s
- [ ] k3s installed as a single node, `kubectl` works from the Mac
- [ ] `nvidia` RuntimeClass and NVIDIA device plugin applied, the node reports `nvidia.com/gpu: 1`
- [ ] A test pod with a GPU request runs `nvidia-smi` and completes
- [ ] The setup runbook has a section for each step, with a check command and its expected output
