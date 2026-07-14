from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

from app.database import SessionLocal, init_db
from app.services.collection_service import collect_schedule_data

logger = logging.getLogger("backfill_matches")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_backfill(date_from: date, date_to: date, sleep_seconds: float = 0.2) -> dict[str, int]:
    if date_to < date_from:
        raise ValueError("date_to debe ser mayor o igual que date_from")
    init_db()
    totals = {"days": 0, "competitions": 0, "teams": 0, "matches": 0, "forms": 0, "odds": 0, "errors": 0}
    current = date_from
    with SessionLocal() as db:
        while current <= date_to:
            try:
                result = collect_schedule_data(db, current)
                for key in ("competitions", "teams", "matches", "forms", "odds"):
                    totals[key] += int(result.get(key, 0))
                totals["days"] += 1
                logger.info("processed date=%s result=%s totals=%s", current.isoformat(), result, totals)
            except Exception as exc:
                totals["errors"] += 1
                logger.exception("failed date=%s error=%s", current.isoformat(), exc)
            current += timedelta(days=1)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    logger.info("backfill complete totals=%s", totals)
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar partidos por rango de fechas")
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    args = parser.parse_args()
    totals = run_backfill(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), args.sleep_seconds)
    print(totals)


if __name__ == "__main__":
    main()
