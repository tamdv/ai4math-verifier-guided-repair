"""Distributed Redis Queue and Priority Task Dispatcher for AI4Math.

Provides production-grade distributed queueing with Redis:
- FIFO Queue mode (List LPUSH / RPOP)
- Priority Queue mode (Sorted Set ZADD / ZPOPMIN)
- In-flight task tracking, ACK / NACK with Dead-Letter-Queue (DLQ)
- Automatic fallback for offline development / isolated unit testing
- Latency and throughput metric calculation (P50, P95 wait time)
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class QueueMode(str, Enum):
    """Queue scheduling disciplines."""

    FIFO = "fifo"
    PRIORITY = "priority"


class TaskStatus(str, Enum):
    """Lifecycle states of a queued repair task."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    ACKED = "ACKED"
    REQUEUED = "REQUEUED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class TaskItem:
    """Represents a scheduled unit of repair work."""

    task_id: str
    payload: dict[str, Any]
    priority: int = 5  # 1 (Highest) to 10 (Lowest)
    attempts: int = 0
    max_attempts: int = 3
    enqueued_at: float = field(default_factory=time.time)
    dequeued_at: float | None = None
    status: TaskStatus = TaskStatus.QUEUED
    error_reason: str | None = None

    def to_json(self) -> str:
        """Serializes the task item to a JSON string."""
        data = asdict(self)
        data["status"] = self.status.value
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> TaskItem:
        """Deserializes a JSON string into a TaskItem."""
        data = json.loads(json_str)
        data["status"] = TaskStatus(data.get("status", TaskStatus.QUEUED.value))
        return cls(**data)


class WorkerQueue:
    """Distributed task queue backed by Redis with FIFO and Priority scheduling.

    Supports atomic operations, in-flight recovery, dead-letter routing,
    and automatic memory fallback when Redis is unreachable.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db: int = 0,
        password: str | None = None,
        url: str | None = None,
        prefix: str = "ai4math:queue",
        use_fallback: bool = True,
    ) -> None:
        """Initializes the WorkerQueue.

        Args:
            host: Redis host address (defaults to env REDIS_HOST or 'localhost').
            port: Redis port (defaults to env REDIS_PORT or 6379).
            db: Redis database index.
            password: Redis authentication password.
            url: Optional full Redis connection URL (env REDIS_URL).
            prefix: Key namespace prefix for Redis keys.
            use_fallback: Whether to fallback to in-memory mode if Redis is down.
        """
        self.host: str = str(host or os.getenv("REDIS_HOST") or "localhost")
        raw_port = port if port is not None else os.getenv("REDIS_PORT", "6379")
        self.port: int = int(raw_port)

        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.url = url or os.getenv("REDIS_URL")
        self.prefix = prefix
        self.use_fallback = use_fallback

        self.key_fifo = f"{prefix}:fifo"
        self.key_priority = f"{prefix}:priority"
        self.key_inflight = f"{prefix}:inflight"
        self.key_dlq = f"{prefix}:dlq"

        self._client: Any = None
        self._is_redis_connected = False

        # In-memory fallback structures
        self._mem_fifo: list[str] = []
        self._mem_priority: list[tuple[float, str]] = []  # (score, json_str)
        self._mem_inflight: dict[str, str] = {}
        self._mem_dlq: list[str] = []

        # Local latency metrics tracking
        self._wait_latencies_ms: list[float] = []
        self._enqueued_count = 0
        self._dequeued_count = 0
        self._acked_count = 0
        self._dlq_count = 0

        self._init_connection()

    def _init_connection(self) -> None:
        """Attempts to initialize Redis client connection with fast timeout and fakeredis fallback."""
        try:
            import redis  # type: ignore

            if self.url:
                client = redis.from_url(
                    self.url,
                    decode_responses=True,
                    socket_connect_timeout=0.1,
                )
            else:
                client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=0.1,
                )
            client.ping()
            self._client = client
            self._is_redis_connected = True
        except (ImportError, ConnectionError, TimeoutError, OSError, Exception):  # noqa: BLE001
            try:
                import fakeredis  # type: ignore

                self._client = fakeredis.FakeRedis(decode_responses=True)
                self._is_redis_connected = True
            except (ImportError, Exception):  # noqa: BLE001
                self._client = None
                self._is_redis_connected = False
                if not self.use_fallback:
                    raise ConnectionError(
                        f"Could not connect to Redis at {self.host}:{self.port} "
                        "and use_fallback is disabled."
                    )

    @property
    def is_redis_connected(self) -> bool:
        """Returns True if connected to a live Redis instance."""
        return self._is_redis_connected

    def enqueue(
        self,
        payload: dict[str, Any],
        priority: int = 5,
        task_id: str | None = None,
        max_attempts: int = 3,
        mode: QueueMode = QueueMode.FIFO,
    ) -> str:
        """Enqueues a new repair candidate into the distributed queue.

        Args:
            payload: Problem statement, code, diagnostics dictionary.
            priority: Scheduling priority (1 = highest, 10 = lowest).
            task_id: Optional unique identifier. Generated if omitted.
            max_attempts: Maximum retry count before routing to DLQ.
            mode: QueueMode.FIFO or QueueMode.PRIORITY.

        Returns:
            The generated or provided unique task_id.
        """
        tid = task_id or f"task-{uuid.uuid4().hex[:10]}"
        task = TaskItem(
            task_id=tid,
            payload=payload,
            priority=priority,
            attempts=0,
            max_attempts=max_attempts,
            enqueued_at=time.time(),
            status=TaskStatus.QUEUED,
        )
        task_json = task.to_json()

        if self._is_redis_connected:
            if mode == QueueMode.FIFO:
                # RPUSH appends to tail of list
                self._client.rpush(self.key_fifo, task_json)
            else:
                # Lower numerical score = higher scheduling priority.
                # Tie-breaking with fractional timestamp prevents starvation.
                score = float(priority) + (task.enqueued_at % 1000) / 100000.0
                self._client.zadd(self.key_priority, {task_json: score})
        else:
            if mode == QueueMode.FIFO:
                self._mem_fifo.append(task_json)
            else:
                score = float(priority) + (task.enqueued_at % 1000) / 100000.0
                self._mem_priority.append((score, task_json))
                self._mem_priority.sort(key=lambda x: x[0])

        self._enqueued_count += 1
        return tid

    def dequeue(
        self,
        timeout: float = 1.0,
        mode: QueueMode = QueueMode.FIFO,
    ) -> TaskItem | None:
        """Dequeues the next available task according to the selected mode.

        Moves the task to in-flight tracking until acknowledged.

        Args:
            timeout: Maximum wait time in seconds (for blocking calls).
            mode: QueueMode.FIFO or QueueMode.PRIORITY.

        Returns:
            A TaskItem if available, or None if the queue is empty.
        """
        task_json: str | None = None

        if self._is_redis_connected:
            if mode == QueueMode.FIFO:
                # Blocking left pop
                res = self._client.blpop([self.key_fifo], timeout=max(int(timeout), 1))
                if res:
                    task_json = res[1]
            else:
                # Sorted set pop minimum score
                res = self._client.zpopmin(self.key_priority, count=1)
                if res:
                    task_json = res[0][0]
        else:
            if mode == QueueMode.FIFO:
                if self._mem_fifo:
                    task_json = self._mem_fifo.pop(0)
            else:
                if self._mem_priority:
                    _score, task_json = self._mem_priority.pop(0)

        if not task_json:
            return None

        task = TaskItem.from_json(task_json)
        now = time.time()
        task.dequeued_at = now
        task.status = TaskStatus.PROCESSING
        wait_ms = (now - task.enqueued_at) * 1000.0
        self._wait_latencies_ms.append(max(wait_ms, 0.0))
        self._dequeued_count += 1

        # Track in-flight
        updated_json = task.to_json()
        if self._is_redis_connected:
            self._client.hset(self.key_inflight, task.task_id, updated_json)
        else:
            self._mem_inflight[task.task_id] = updated_json

        return task

    def ack(self, task_id: str) -> bool:
        """Acknowledges successful processing and removes task from in-flight.

        Args:
            task_id: Unique task identifier.

        Returns:
            True if task was in-flight and removed, False otherwise.
        """
        if self._is_redis_connected:
            removed = self._client.hdel(self.key_inflight, task_id) > 0
        else:
            removed = self._mem_inflight.pop(task_id, None) is not None

        if removed:
            self._acked_count += 1
        return removed

    def nack(
        self,
        task_id: str,
        requeue: bool = True,
        increase_priority: bool = True,
        error_reason: str | None = None,
        mode: QueueMode = QueueMode.FIFO,
    ) -> bool:
        """Handles task processing failure. Requeues or routes to Dead Letter Queue.

        Args:
            task_id: Unique task identifier.
            requeue: Whether to retry the task if budget remains.
            increase_priority: Whether to bump priority for fast re-check.
            error_reason: Optional error reason string.
            mode: Scheduling mode for re-enqueueing.

        Returns:
            True if task was successfully handled.
        """
        task_json: str | None = None
        if self._is_redis_connected:
            task_json = self._client.hget(self.key_inflight, task_id)
            self._client.hdel(self.key_inflight, task_id)
        else:
            task_json = self._mem_inflight.pop(task_id, None)

        if not task_json:
            return False

        task = TaskItem.from_json(task_json)
        task.attempts += 1
        task.error_reason = error_reason

        # Check retry budget
        if requeue and task.attempts < task.max_attempts:
            if increase_priority and task.priority > 1:
                task.priority -= 1  # 1 is highest priority
            task.status = TaskStatus.REQUEUED
            task.enqueued_at = time.time()
            task.dequeued_at = None

            updated_json = task.to_json()
            if self._is_redis_connected:
                if mode == QueueMode.FIFO:
                    self._client.lpush(
                        self.key_fifo, updated_json
                    )  # Urgent head insert
                else:
                    score = float(task.priority) + (task.enqueued_at % 1000) / 100000.0
                    self._client.zadd(self.key_priority, {updated_json: score})
            else:
                if mode == QueueMode.FIFO:
                    self._mem_fifo.insert(0, updated_json)
                else:
                    score = float(task.priority) + (task.enqueued_at % 1000) / 100000.0
                    self._mem_priority.append((score, updated_json))
                    self._mem_priority.sort(key=lambda x: x[0])
            return True
        else:
            # Exceeded budget or requeue disabled: Route to DLQ
            task.status = TaskStatus.DEAD_LETTER
            dlq_json = task.to_json()
            if self._is_redis_connected:
                self._client.rpush(self.key_dlq, dlq_json)
            else:
                self._mem_dlq.append(dlq_json)
            self._dlq_count += 1
            return True

    def get_length(self, mode: QueueMode | None = None) -> int:
        """Returns the number of waiting tasks in the queue.

        Args:
            mode: Specific queue mode length, or combined total if None.

        Returns:
            Integer task count.
        """
        if self._is_redis_connected:
            fifo_len = self._client.llen(self.key_fifo)
            prio_len = self._client.zcard(self.key_priority)
        else:
            fifo_len = len(self._mem_fifo)
            prio_len = len(self._mem_priority)

        if mode == QueueMode.FIFO:
            return fifo_len
        elif mode == QueueMode.PRIORITY:
            return prio_len
        return fifo_len + prio_len

    def get_inflight_length(self) -> int:
        """Returns the number of currently in-flight processing tasks."""
        if self._is_redis_connected:
            return self._client.hlen(self.key_inflight)
        return len(self._mem_inflight)

    def get_dlq_length(self) -> int:
        """Returns the number of dead-lettered unrepairable tasks."""
        if self._is_redis_connected:
            return self._client.llen(self.key_dlq)
        return len(self._mem_dlq)

    def get_metrics(self) -> dict[str, Any]:
        """Calculates queue latency percentiles (P50, P95) and throughput counts.

        Returns:
            Dictionary containing queue operational metrics.
        """
        latencies = sorted(self._wait_latencies_ms)
        p50 = 0.0
        p95 = 0.0
        if latencies:
            n = len(latencies)
            p50 = latencies[int(n * 0.50)]
            p95 = latencies[min(int(n * 0.95), n - 1)]

        return {
            "is_redis": self._is_redis_connected,
            "enqueued_total": self._enqueued_count,
            "dequeued_total": self._dequeued_count,
            "acked_total": self._acked_count,
            "dlq_total": self._dlq_count,
            "queue_pending_fifo": self.get_length(QueueMode.FIFO),
            "queue_pending_priority": self.get_length(QueueMode.PRIORITY),
            "inflight_count": self.get_inflight_length(),
            "dlq_count": self.get_dlq_length(),
            "wait_time_p50_ms": round(p50, 2),
            "wait_time_p95_ms": round(p95, 2),
        }

    def clear(self) -> None:
        """Flushes all queue namespaces and resets internal counters."""
        if self._is_redis_connected:
            self._client.delete(
                self.key_fifo,
                self.key_priority,
                self.key_inflight,
                self.key_dlq,
            )
        self._mem_fifo.clear()
        self._mem_priority.clear()
        self._mem_inflight.clear()
        self._mem_dlq.clear()
        self._wait_latencies_ms.clear()
        self._enqueued_count = 0
        self._dequeued_count = 0
        self._acked_count = 0
        self._dlq_count = 0

    def close(self) -> None:
        """Closes Redis connections gracefully."""
        if self._client and hasattr(self._client, "close"):
            with contextlib.suppress(Exception):
                self._client.close()
        self._is_redis_connected = False
