# What is left

Read this file first when you continue the work. Then read `README.md`, `docs/setup.md`, and the
tickets in `.scratch/vllm-genai-poc/issues/`. The tickets show which checks passed. A box that is
not ticked is not checked on the target machine.

## Where the work stopped

The code and the documents are written. Part of the stack ran on the local PC in WSL2. The rest is
not tested. The README has the status table.

On the PC, in k3s, at the time of the stop:
- The speech pods and the Open WebUI pod ran and passed their checks.
- vLLM runs with Qwen2.5-3B-Instruct (checked on 2026-11-13, see `docs/benchmarks.md`). The model is
  in the `vllm-cache` PVC, so a restart does not download it again.
- The monitoring pods run (checked on 2026-11-13): all 7 Prometheus targets are up, DCGM works on
  WSL2, and the alert test passed. `node-exporter` needs `mount --make-rshared /` as root in WSL2
  after each boot of WSL2. Not looked at yet: the dashboard panels in the browser.
- The benchmark ran on 2026-11-13 (6 of 9 configurations, see `docs/benchmarks.md`). The Deployment
  is back to the arguments of `k8s/vllm-deployment.yaml`. The raw results are in `bench/results/` (it is
  not in git) on the PC copy and on the Mac.
- The copy of the project on the PC is the repository of the last send, not the newest commits. It has
  one file that is not tracked: `docs/diagram-prompt.md`.
- The SSH server and the firewall rule for it are still enabled on the PC.

## The three runs

Each run follows `docs/setup.md` and ends with `sh bench/smoke_test.sh`.

1. **PC, WSL2 (partly done).** Done: the GPU node, the speech pods, the Open WebUI pod, and vLLM
   with Qwen2.5-3B-Instruct on k3s (VRAM and KV cache, start, a chat through the Service, a restart
   without a new download), vLLM standalone (ticket 02), the monitoring pods, and the benchmark of 6
   configurations. Left: the choice of the final vLLM flags (open questions: keep n-gram decoding, AWQ,
   and a lower utilization for the three configurations that need 0.92), the dashboard panels in the
   browser, and chat and voice in the browser. The smoke test passed (10 of 10, `--no-https`) with the
   arguments of the repository. Run it again after the final flags. Before you start, send the
   project to the PC again if the repository changed (see "Get the code into WSL2 without a push" in
   `docs/setup.md`).
2. **PC, bare-metal Ubuntu.** Install Ubuntu on the PC, then repeat everything. Also test what WSL2
   cannot: the HTTPS Ingress and the NodePort. Check that the model runner V2 works there (on WSL2 it
   stops with "UVA is not available", see `docs/setup.md`, "Benchmark harness"). Fill the PC spec table again.
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
  - `--gpu-memory-utilization` must stay below the free VRAM at the start. On this PC, vLLM sees
    10.79 GiB free of 11.99 GiB, so 0.92 does not start. The Windows desktop uses about 0.8 to 1.2 GiB
    of the 12 GiB, and that does not change the free VRAM that vLLM sees.
  - The WSL2 VM stops when no session is open, and k3s stops with it. Every pod restarts at the next
    connection. For a long run, keep a session open from the Mac:
    `ssh ... 'wsl -d Ubuntu-24.04 -- sleep infinity'` (in the background).
  - `kubectl logs -l <selector>` shows only the last 10 lines. Add `--tail=-1`, or use `deploy/<name>`.
  - After a restart of the VM, `kubectl get pods` can list old pods as `Completed` or `Unknown`. They
    are stale records. Delete them (`--force --grace-period=0` for `Unknown`).
