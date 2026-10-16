"""Thread pool of long-lived Lean verifiers (one REPL process per worker).

Each worker owns its own verifier (REPL processes are not thread-safe), pulls
tasks from a shared FIFO queue and records queue wait / service time so queue
latency can be reported separately from verification latency.
"""

import queue
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from src.lean_verifier import VerificationResult


class Verifier(Protocol):
    """Anything with `verify(code) -> VerificationResult`."""

    def verify(self, code: str) -> VerificationResult: ...


@dataclass
class PoolResult:
    """Result of one task plus scheduling metadata."""

    index: int
    result: Any
    worker_id: int
    queue_wait_ms: float
    service_ms: float
    payload: Any = None


class VerifierPool:
    """Runs `verify` over many snippets with `n_workers` independent verifiers.

    Args:
        factory: Zero-arg callable building one worker object (called once per
            worker, inside the worker thread so expensive imports run in parallel).
        n_workers: Number of worker threads / verifier processes.
        task: `task(worker_obj, item) -> result`; defaults to `worker.verify(item)`.
    """

    def __init__(
        self,
        factory: Callable[[], Any],
        n_workers: int = 1,
        task: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self.factory = factory
        self.n_workers = n_workers
        self.task = task or (lambda worker, code: worker.verify(code))
        self.startup_ms: list[float] = []

    def imap(
        self, items: Iterable[tuple[str, Any]]
    ) -> Iterator[PoolResult]:
        """Runs the task on `(item, payload)` pairs; yields results as they complete."""
        tasks: queue.Queue[tuple[int, str, Any, float] | None] = queue.Queue()
        results: queue.Queue[PoolResult | BaseException] = queue.Queue()
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            start = time.perf_counter()
            try:
                verifier = self.factory()
            except BaseException as exc:  # surface startup failures to the caller
                results.put(exc)
                return
            with lock:
                self.startup_ms.append(round((time.perf_counter() - start) * 1000, 1))
            try:
                while True:
                    task = tasks.get()
                    if task is None:
                        break
                    idx, code, payload, enqueued = task
                    begin = time.perf_counter()
                    try:
                        res = self.task(verifier, code)
                    except Exception as exc:  # one bad item must not kill the worker
                        res = exc
                    end = time.perf_counter()
                    results.put(
                        PoolResult(
                            index=idx,
                            result=res,
                            worker_id=worker_id,
                            queue_wait_ms=round((begin - enqueued) * 1000, 3),
                            service_ms=round((end - begin) * 1000, 3),
                            payload=payload,
                        )
                    )
            finally:
                close = getattr(verifier, "close", None) or getattr(
                    getattr(verifier, "verifier", None), "close", None
                )
                if close:
                    close()

        threads = [
            threading.Thread(target=worker, args=(i,), daemon=True) for i in range(self.n_workers)
        ]
        for t in threads:
            t.start()

        count = 0
        for idx, (code, payload) in enumerate(items):
            tasks.put((idx, code, payload, time.perf_counter()))
            count += 1
        for _ in threads:
            tasks.put(None)

        for _ in range(count):
            item = results.get()
            if isinstance(item, BaseException):
                raise item
            yield item
        for t in threads:
            t.join()
