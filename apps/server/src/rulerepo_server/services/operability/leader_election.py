"""Worker leader election using PostgreSQL advisory locks.

Provides non-blocking leader election so that only one worker instance
executes a given cron job at a time. Uses ``pg_try_advisory_lock`` for
non-blocking acquisition and ``pg_advisory_unlock`` for release.

Usage::

    from rulerepo_server.services.operability.leader_election import leader_election

    async with leader_election.hold(lock_id=1001, worker_id="worker-a"):
        # Only executes if this worker acquired the lock
        await run_daily_digest()

    # Or manually:
    if await leader_election.try_acquire(1001, "worker-a"):
        try:
            await run_daily_digest()
        finally:
            await leader_election.release(1001, "worker-a")
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class LeaderElection:
    """PostgreSQL advisory-lock based leader election.

    Each ``lock_id`` represents a distinct job or resource. Only one
    worker can hold a given lock at a time. The lock is session-scoped
    in PostgreSQL, meaning it is automatically released if the
    connection drops.

    Thread-safe: internal tracking of held locks is protected by a
    mutex so multiple asyncio tasks in the same process can coordinate.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Tracks which (lock_id, worker_id) pairs are held in this process
        self._held: set[tuple[int, str]] = set()

    async def try_acquire(self, lock_id: int, worker_id: str) -> bool:
        """Attempt to acquire an advisory lock without blocking.

        Args:
            lock_id: Unique integer identifier for the job/resource.
            worker_id: Identifier for this worker instance (for logging).

        Returns:
            True if the lock was acquired, False if another worker holds it.
        """
        from rulerepo_server.adapters.postgres.session import get_engine

        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id},
            )
            acquired = result.scalar()

        if acquired:
            with self._lock:
                self._held.add((lock_id, worker_id))
            logger.info(
                "leader_lock_acquired",
                lock_id=lock_id,
                worker_id=worker_id,
            )
            return True

        logger.debug(
            "leader_lock_not_acquired",
            lock_id=lock_id,
            worker_id=worker_id,
        )
        return False

    async def release(self, lock_id: int, worker_id: str) -> None:
        """Release a previously acquired advisory lock.

        Args:
            lock_id: The lock identifier to release.
            worker_id: The worker that holds the lock.
        """
        from rulerepo_server.adapters.postgres.session import get_engine

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id},
            )

        with self._lock:
            self._held.discard((lock_id, worker_id))

        logger.info(
            "leader_lock_released",
            lock_id=lock_id,
            worker_id=worker_id,
        )

    async def is_leader(self, lock_id: int, worker_id: str) -> bool:
        """Check whether this worker currently holds the given lock.

        This is a local check only; it does not query PostgreSQL.
        If the connection was dropped and PostgreSQL released the lock
        automatically, this may return a stale result until the next
        acquire/release cycle.

        Args:
            lock_id: The lock identifier.
            worker_id: The worker identifier.

        Returns:
            True if this process believes it holds the lock.
        """
        with self._lock:
            return (lock_id, worker_id) in self._held

    @asynccontextmanager
    async def hold(self, lock_id: int, worker_id: str) -> AsyncIterator[bool]:
        """Context manager that acquires a lock and releases it on exit.

        The body of the ``async with`` block only executes if the lock
        was successfully acquired. The yielded boolean indicates whether
        the lock was acquired.

        Args:
            lock_id: Unique integer identifier for the job/resource.
            worker_id: Identifier for this worker instance.

        Yields:
            True if the lock was acquired (body executes), False otherwise.

        Example::

            async with leader_election.hold(1001, "worker-a") as acquired:
                if acquired:
                    await do_exclusive_work()
        """
        acquired = await self.try_acquire(lock_id, worker_id)
        try:
            yield acquired
        finally:
            if acquired:
                await self.release(lock_id, worker_id)


# Module-level singleton
leader_election = LeaderElection()
