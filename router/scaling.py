"""Scale to zero for the pods of the pool. The Kubernetes calls are in a client that the caller gives."""
import logging
from typing import Optional

log = logging.getLogger("router")


class Scaler:
    """members maps a pool member name (the label `pool-member`) to its Deployment.
    always_on members never go to zero. on_event gets "up" or "down" after each change."""

    def __init__(self, client, members, always_on, idle_seconds, on_event=None):
        self._client = client
        self._members = dict(members)
        self._always_on = set(always_on)
        self._idle_seconds = idle_seconds
        self.on_event = on_event or (lambda _direction: None)

    async def wake(self) -> Optional[str]:
        """Scale the first member that is at zero (in sort order) to one. None when no member is at zero."""
        for member in sorted(self._members):
            deployment = self._members[member]
            if await self._client.get_replicas(deployment) == 0:
                await self._client.set_replicas(deployment, 1)
                log.info("scaled %s up to 1", deployment)
                self.on_event("up")
                return member
        return None

    async def scale_down_idle(self, candidates):
        """candidates: (member, seconds idle, requests in flight) for each ready pod."""
        for member, idle, in_flight in candidates:
            if member not in self._members or member in self._always_on:
                continue
            if in_flight > 0 or idle < self._idle_seconds:
                continue
            deployment = self._members[member]
            if await self._client.get_replicas(deployment) == 0:
                continue
            await self._client.set_replicas(deployment, 0)
            log.info("scaled %s down to 0 after %.0f s idle", deployment, idle)
            self.on_event("down")
