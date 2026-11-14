# 05: Scale to zero and cold start hold

**What to build:** Pod `b` scales to zero when idle, and the router scales it up and holds the request until the pod is ready.

**Blocked by:** 04

**Status:** ready-for-agent

**Test status:** done on WSL2 on 2026-11-14 (numbers in `docs/benchmarks.md`). 71 tests pass; the idle timer, the hold, and the wake were written test first with a fake clock and a fake scale client. On the cluster: idle pod `b` went to zero after 90 s and `a` stayed; with nothing ready and a limit of 5 s the answer was 503 after 5.1 s; with a limit of 120 s the request waited 45.4 s and was answered by pod `a`. The router only wakes a pod when no pod is ready, so `b` stays at zero under load (autoscaling by load is out of scope).

- [x] Pod `b` goes to zero replicas after the idle time (start value 10 minutes, an environment variable); pod `a` never goes below one
- [x] A request that needs pod `b` makes the router scale it to one and hold the request, for at most 120 seconds; after that the answer is 503
- [x] The wait time is measured and recorded (the cold start of the proof of concept was 51 to 71 seconds)
- [x] Tests are written first for the idle timer and the hold logic with a fake clock and a fake scale client
- [x] Scale events are logged and counted in `router_scale_events_total`
