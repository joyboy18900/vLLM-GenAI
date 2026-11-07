# 15: Documents: GUIDE, setup, benchmarks

**What to build:** A reader can understand the system and set it up from the documents alone. The documents follow the reference project, in English.

**Blocked by:** 13, 14

**Status:** ready-for-agent

**Test status:** drafted. GUIDE and the EC2 section are written. The setup runbook is in order. Still open: the sentence "tested on the local PC" with the PC spec, and the benchmark summary with the recommended config. Both need the first real run.

- [ ] GUIDE: how a text request and a voice request move through the system, what k3s does at each step, how to access and read the dashboards
- [ ] Setup runbook complete and in order; it says the system was tested on the local PC (with the PC spec)
- [ ] Setup runbook has an "If you run on EC2" section: no instance type name, the differences to check (fp8 and bf16 support, VRAM, quota, cost, HTTPS or SSH tunnel for the microphone)
- [ ] Benchmarks document has a final summary and the recommended config
- [ ] ASD-STE100 style, no em dashes, no filler text
