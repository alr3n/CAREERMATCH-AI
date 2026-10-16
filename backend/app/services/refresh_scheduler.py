"""Periodic job refresh inside the API process.

Runs ``job_service.refresh_jobs`` every ``AUTO_REFRESH_MINUTES`` on a daemon
thread. Per-source cooldowns and each provider's own minimum interval are
stored in the database, so several API workers running this loop still fetch
each source at most as often as its rules allow; the refresh lock makes a
concurrent run in the same process a no-op. Set ``AUTO_REFRESH_MINUTES=0`` to
disable it and schedule ``python -m app.cli refresh-jobs`` with cron instead.
"""

from __future__ import annotations

import logging
import threading

from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class RefreshScheduler:
    def __init__(self, settings: Settings, initial_delay_seconds: float = 30.0) -> None:
        self.interval = settings.auto_refresh_minutes * 60
        self.initial_delay = initial_delay_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.interval <= 0 or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="job-refresh", daemon=True)
        self._thread.start()
        logger.info("Automatic job refresh every %d minutes", self.interval // 60)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        from app.services import job_service  # imported late to avoid a cycle at startup

        delay = self.initial_delay
        while not self._stop.wait(delay):
            delay = self.interval
            try:
                with SessionLocal() as db:
                    results = job_service.refresh_jobs(db)
                failed = [f"{r.provider}/{r.identifier}" for r in results if r.status in {"error", "rate_limited"}]
                if failed:
                    logger.warning("Scheduled refresh: %d source(s) failed: %s", len(failed), ", ".join(failed))
            except AppError as exc:  # e.g. a manual refresh is already running
                logger.info("Scheduled refresh skipped: %s", exc)
            except Exception:  # never let the loop die
                logger.exception("Scheduled refresh failed")
