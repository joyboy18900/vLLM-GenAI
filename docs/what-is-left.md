# What is left

Read this file first when you continue the work. Then read `README.md`, `docs/setup.md`, and the
tickets in `.scratch/vllm-genai-poc/issues/`. The tickets show which checks passed. A box that is
not ticked is not checked on the target machine.

## Where the work stopped

The code and the documents are written. Part of the stack ran on the local PC in WSL2. The rest is
not tested. The README has the status table.

On the PC, in k3s, at the time of the stop:
- The speech pods and the Open WebUI pod ran and passed their checks.
- The vLLM Deployment and the monitoring manifests were applied, but nobody checked the result.
- The Deployments still use the first model (Qwen3.5-4B). The repository now uses Qwen2.5-3B-Instruct.
- The copy of the project on the PC is older than the repository.
- The SSH server and the firewall rule for it are still enabled on the PC.

## The three runs

Each run follows `docs/setup.md` and ends with `sh bench/smoke_test.sh`.

1. **PC, WSL2 (partly done).** Done: the GPU node, the speech pods, and the Open WebUI pod. Left:
   vLLM with Qwen2.5-3B-Instruct, standalone and on k3s (VRAM and KV cache, start, a chat through the
   Service, a restart without a new download), the monitoring pods (DCGM may not work on WSL2), chat
   and voice in the browser, the benchmark and the configurations in `bench/levers.py` (to choose the
   final vLLM flags), and the smoke test. Before you start, send the project to the PC again and apply
   the manifests again (see "Get the code into WSL2 without a push" in `docs/setup.md`).
2. **PC, bare-metal Ubuntu.** Install Ubuntu on the PC, then repeat everything. Also test what WSL2
   cannot: DCGM, the HTTPS Ingress, and the NodePort. Fill the PC spec table again.
3. **EC2.** Repeat the run on a rented GPU machine. It is the backup when the PC is not ready. Check
   the differences in "If you run on EC2" (fp8 and bf16 support, VRAM, quota, cost).

After each run: tick the boxes of the tickets that passed, update the status tables (the README,
`docs/setup.md`, `docs/benchmarks.md`), and put the final vLLM flags in `k8s/vllm-deployment.yaml`
and in `bench/levers.py` (the configuration `deployed` must equal the Deployment).

## Small items that are not test runs

- Make `docs/workflow.png` again with ChatGPT. Fix the arrows in the monitoring box (the real ones
  are Prometheus to Alertmanager, Loki to Grafana, and Prometheus to Grafana). Change the vLLM box to
  "Qwen2.5-3B-Instruct, fp16". Check the spelling of "Traefik". The notes are in ticket 16.
  The text for ChatGPT is in the files `prompt.md` and `architecture.md` on the owner's Desktop.
  They are not in the repository.
- Thai TTS (bonus): run `bench/thai_tts`, listen, and choose a voice (ticket 18).
- When the PC runs are over, remove the SSH access (see "Remote access" in `docs/setup.md`).

## What a new session does not know

The owner keeps these facts outside the repository. Ask the owner.

- **Remote access to the PC.** An earlier session connected from the Mac to the PC with the SSH
  server of Windows, and ran commands in WSL2 through it. The firewall rule allows only the home
  network, so it does not work from outside. Do not connect before you agree with the owner how to do
  it. The owner gives the address of the PC.
- **Root on the PC.** The commands that need root ran as root in WSL2 (`wsl -d Ubuntu-24.04 -u root`),
  because the owner allowed it. Ask again in a new session.
- **Places on the PC.** The WSL2 distribution is `Ubuntu-24.04`. Its disk is on the drive D: in
  `D:\vLLM\wsl`. The project copy is in `D:\vLLM\vLLM-GenAI`. The Grafana admin password is in the
  file `.grafana-admin-password` in the home folder of the WSL2 user. The password is not in the
  repository. Do not put it there.
- **Rules of the owner.**
  - Nothing goes to GitHub without a clear "push" from the owner, every time. The GitHub repository
    is private. The owner decides when it becomes public.
  - No LICENSE file and no CI.
  - The agent gets no AWS credentials. The owner makes AWS changes in the console.
  - Work on the Mac. The PC only runs the stack. Change files on the Mac and send them to the PC.
  - The values of the files follow the project that inspired this one, except where this project adds
    its own features. Only the README names that project. Do not name it in other files.
  - The owner talks Thai in the chat. The files of the repository are English (ASD-STE100) and have
    no em dash.
- **Checks before a commit.** No em dash (`git grep -I -l -P '\xe2\x80\x94'` finds the bytes of it). The manifests pass
  `kubeconform -strict` (run it with Docker). The scripts pass `bash -n` and `shellcheck`. The
  Prometheus config passes `promtool check config`.
- **Lessons from the commands on the PC.**
  - Send a long script through stdin (`ssh ... 'wsl -d Ubuntu-24.04 -- bash -s' <<'EOF'`). A command
    in quotes is expanded by another shell on the way.
  - `kubectl run -i` reads the stdin of the script. Add `< /dev/null` to it.
  - The shell of the Mac (zsh) does not split a variable that holds a command. Use a function.
  - `--gpu-memory-utilization` must stay below the free VRAM at the start. The Windows desktop uses
    about 1 GiB of the 12 GiB.
