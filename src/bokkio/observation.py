"""Read accounting shared by the tree adapter and native annotation pass."""
from __future__ import annotations

from contextvars import ContextVar
import time
from .model import BokkioError


active_read = ContextVar('bokkio_active_read', default=None)


class ReadStopped(BokkioError):
    """Cooperative stop between native calls, never cancellation of a COM call."""


class ReadBudget:
    def __init__(self, nodes=None, timeout=None, depth=None):
        for name, value, upper in [('read_nodes', nodes, 100000), ('read_depth', depth, 64)]:
            if value is not None and (type(value) is not int or not 1 <= value <= upper):
                raise ValueError(f'{name} must be 1..{upper}')
        if timeout is not None and (type(timeout) not in (int, float) or not 0 < timeout <= 30):
            raise ValueError('read_timeout must be greater than 0 and at most 30 seconds')
        self.started = time.monotonic()
        self.deadline = self.started + timeout if timeout is not None else None
        self.limit, self.depth = nodes, depth
        self.visited = {'tree': 0, 'annotation': 0}
        self.child_batches = self.child_candidates = 0
        self.reason = None

    def check(self):
        if self.reason:
            return False
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.reason = 'time_limit'
        return self.reason is None

    def enter(self, stage, depth):
        if not self.check():
            return False
        if self.depth is not None and depth > self.depth:
            self.reason = 'depth_limit'
        elif self.limit is not None and sum(self.visited.values()) >= self.limit:
            self.reason = 'node_limit'
        else:
            self.visited[stage] += 1
        return self.reason is None

    def result(self):
        self.check()
        return {'complete': self.reason is None, 'reason': self.reason,
                'visited_nodes': sum(self.visited.values()), **self.visited,
                'child_batches': self.child_batches, 'child_candidates': self.child_candidates,
                'elapsed_ms': round((time.monotonic() - self.started) * 1000, 3),
                'node_limit': self.limit, 'depth_limit': self.depth,
                'native_calls_interruptible': False,
                'child_enumeration': 'provider_batch_not_paged'}


def require_complete(snapshot):
    if snapshot.get('read', {}).get('complete') is False:
        from .model import BokkioActionRefused
        raise BokkioActionRefused('Observation is incomplete; read the complete operation scope before input',
                                 'observation_incomplete')
