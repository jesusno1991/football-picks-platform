from __future__ import annotations

import argparse
import logging
import time
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.collectors.factory import get_provider
from app.database import SessionLocal, init_db
from app.models import HistoricalSyncWindow
from app.services.collection_service import collect_schedule_data
from app.utils.time import utc_now_naive

logger = logging.getLogger("backfill_matches")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_backfill(date_from: date, date_to: date, sleep_seconds: float = 0.2, retries: int = 2, resume: bool = True) -> dict[str, int]:
    if date_to < date_from:
        raise ValueError("date_to debe ser mayor o igual que date_from")
    init_db()
    totals = {
        "days": 0,
        "skipped": 0,
        "competitions": 0,
        "teams": 0,
        "matches": 0,
        "forms": 0,
        "odds": 0,
        "errors": 0,
        "failed": 0,
    }
    current = date_from
    provider_name = get_provider().__class__.__name__
    with SessionLocal() as db:
        while current <= date_to:
            window = _get_or_create_window(db, provider_name, current)
            if resume and window.status == "success":
                totals["skipped"] += 1
                logger.info("skipped completed date=%s", current.isoformat())
                current += timedelta(days=1)
                continue
            attempt = 0
            while attempt <= retries:
                attempt += 1
                try:
                    window.status = "running"
                    window.last_attempt_at = utc_now_naive()
                    db.commit()
                    result = collect_schedule_data(db, current)
                    for key in ("competitions", "teams", "matches", "forms", "odds"):
                        totals[key] += int(result.get(key, 0))
                    totals["days"] += 1
                    window.status = "success"
                    window.completed_at = utc_now_naive()
                    window.notes = str(result)
                    db.commit()
                    logger.info("processed date=%s attempt=%s result=%s totals=%s", current.isoformat(), attempt, result, totals)
                    break
                except Exception as exc:
                    totals["errors"] += 1
                    window.status = "failed"
                    window.notes = str(exc)[:1000]
                    db.commit()
                    logger.exception("failed date=%s attempt=%s error=%s", current.isoformat(), attempt, exc)
                    if attempt > retries:
                        totals["failed"] += 1
                    elif sleep_seconds > 0:
                        time.sleep(max(sleep_seconds, 1.0))
            current += timedelta(days=1)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    logger.info("backfill complete totals=%s", totals)
    return totals


def _get_or_create_window(db, provider: str, target_date: date) -> HistoricalSyncWindow:
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    window = db.scalar(
        select(HistoricalSyncWindow).where(
            HistoricalSyncWindow.provider == provider,
            HistoricalSyncWindow.scope == "fixtures",
            HistoricalSyncWindow.date_from == start,
            HistoricalSyncWindow.date_to == end,
        )
    )
    if window:
        return window
    window = HistoricalSyncWindow(
        provider=provider,
        scope="fixtures",
        date_from=start,
        date_to=end,
        status="pending",
        priority=100,
    )
    db.add(window)
    db.commit()
    return window


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar partidos por rango de fechas")
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    totals = run_backfill(
        date.fromisoformat(args.date_from),
        date.fromisoformat(args.date_to),
        args.sleep_seconds,
        args.retries,
        not args.no_resume,
    )
    print(totals)


if __name__ == "__main__":
    main()
