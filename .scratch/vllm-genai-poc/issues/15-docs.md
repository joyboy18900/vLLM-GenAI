# 15: Documents: GUIDE, setup, benchmarks

**What to build:** A reader can understand the system and set it up from the documents alone. The documents follow the reference project, in English.

**Blocked by:** 13, 14

**Status:** ready-for-agent

**Test status:** written and checked on 2026-11-14 after the WSL2 run. The setup runbook says what ran on the local PC (WSL2), and the PC spec is in `docs/benchmarks.md`. The benchmark summary and the final choice (`baseline`) are in `docs/benchmarks.md`. The runbook is not yet tested on bare-metal Ubuntu (run 2).

- [x] GUIDE: how a text request and a voice request move through the system, what k3s does at each step, how to access and read the dashboards
- [x] Setup runbook complete and in order; it says the system was tested on the local PC (with the PC spec)
- [x] Setup runbook has an "If you run on EC2" section: no instance type name, the differences to check (fp8 and bf16 support, VRAM, quota, cost, HTTPS or SSH tunnel for the microphone)
- [x] Benchmarks document has a final summary and the recommended config
- [x] ASD-STE100 style, no em dashes, no filler text
