"""Command-line utilities.

    python -m app.cli refresh-jobs [--force]     # fetch listings from configured providers
    python -m app.cli sources                     # show configured sources and status
    python -m app.cli import-evaluation PATH      # record an evaluation report in the database

Suitable for cron / a scheduler, e.g. refreshing listings every few hours.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.db.session import SessionLocal
from app.models import EvaluationRun
from app.services import job_service


def _refresh(force: bool) -> int:
    with SessionLocal() as db:
        results = job_service.refresh_jobs(db, force=force)
    failed = 0
    for r in results:
        print(f"{r.provider}/{r.identifier}: {r.status} fetched={r.fetched} created={r.created} "
              f"updated={r.updated} expired={r.expired} invalid={r.skipped_invalid}"
              + (f" — {r.message}" if r.message else ""))
        failed += r.status in {"error", "rate_limited"}
    if not results:
        print("No providers configured. Set GREENHOUSE_BOARDS / LEVER_SITES or ENABLE_DEMO_PROVIDER=true.")
    return 1 if failed else 0


def _sources() -> int:
    with SessionLocal() as db:
        info = job_service.list_sources(db)
    for p in info.providers:
        print(f"{p.name}: {'configured ' + ', '.join(p.sources) if p.configured else 'not configured'} ({p.config_variable})")
    for s in info.sources:
        print(f"  {s.provider}/{s.identifier}: status={s.last_status} active={s.active_listings} "
              f"last_fetched={s.last_fetched_at}")
    print(f"Demo provider: {'enabled' if info.demo_enabled else 'disabled'}")
    return 0


def _import_evaluation(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        for run in report.get("runs", []):
            db.add(EvaluationRun(
                dataset_name=report["dataset"]["name"],
                dataset_version=report["dataset"]["version"],
                split=run.get("split", report["dataset"].get("split", "test")),
                metrics=run["metrics"],
                config={"model": run["model"], "seed": report.get("seed")},
                notes=run.get("notes"),
                evaluated_at=datetime.fromisoformat(report["evaluated_at"]),
            ))
        db.commit()
    print(f"Imported {len(report.get('runs', []))} evaluation runs from {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    refresh = sub.add_parser("refresh-jobs", help="Fetch listings from configured providers")
    refresh.add_argument("--force", action="store_true", help="Ignore the per-source cooldown")
    sub.add_parser("sources", help="Show provider configuration and status")
    imp = sub.add_parser("import-evaluation", help="Record an evaluation report in the database")
    imp.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "refresh-jobs":
        return _refresh(args.force)
    if args.command == "sources":
        return _sources()
    return _import_evaluation(args.path)


if __name__ == "__main__":
    sys.exit(main())
