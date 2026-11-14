# 05: Scale to zero and cold start hold

**What to build:** Pod `b` scales to zero when idle, and the router scales it up and holds the request until the pod is ready.

**Blocked by:** 04

**Status:** ready-for-agent

**Test status:** not started.

- [ ] Pod `b` goes to zero replicas after the idle time (start value 10 minutes, an environment variable); pod `a` never goes below one
- [ ] A request that needs pod `b` makes the router scale it to one and hold the request, for at most 120 seconds; after that the answer is 503
- [ ] The wait time is measured and recorded (the cold start of the proof of concept was 51 to 71 seconds)
- [ ] Tests are written first for the idle timer and the hold logic with a fake clock and a fake scale client
- [ ] Scale events are logged and counted in `router_scale_events_total`
