from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from app.database import SessionLocal, init_db
from app.services.collection_service import collect_deep_data_for_date, collect_schedule_range
from app.services.prediction_service import generate_predictions
from app.services.settlement_service import verify_results
from app.services.statistics_service import overview
from app.services.ultimate_engine import rank_predictions

logger = logging.getLogger("scheduled")


TASK_SCHEDULES = [
    ("collect_upcoming_matches", "cada 6 horas"),
    ("collect_calendar_window", "diario: ultimos 30 dias, hoy y proximos 60 dias"),
    ("update_match_statuses", "cada hora"),
    ("collect_historical_statistics", "una vez al día"),
    ("collect_prematch_odds", "cada 30 minutos"),
    ("generate_predictions_24h", "24 horas antes"),
    ("generate_predictions_6h", "6 horas antes"),
    ("generate_predictions_1h", "1 hora antes"),
    ("close_publication_window", "15 minutos antes"),
    ("verify_results", "después del final"),
    ("recalculate_statistics", "diario"),
]


def run_maintenance(days_back: int = 30, days_forward: int = 60, deep_today: bool = True) -> dict:
    init_db()
    today = date.today()
    result: dict[str, object] = {
        "window": {"date_from": (today - timedelta(days=days_back)).isoformat(), "date_to": (today + timedelta(days=days_forward)).isoformat()},
        "calendar": {},
        "deep_today": {},
        "predictions": {},
        "rankings": {},
        "settlement": {},
        "statistics": {},
    }
    with SessionLocal() as db:
        result["calendar"] = collect_schedule_range(db, today - timedelta(days=days_back), today + timedelta(days=days_forward))
        if deep_today:
            result["deep_today"] = collect_deep_data_for_date(db, today)
        result["predictions"] = generate_predictions(db)
        result["rankings"] = rank_predictions(db)
        result["settlement"] = verify_results(db)
        result["statistics"] = overview(db)
    logger.info("maintenance result=%s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta mantenimiento automatico de The Merlin")
    parser.add_argument("--days-back", type=int, default=30)
    parser.add_argument("--days-forward", type=int, default=60)
    parser.add_argument("--skip-deep-today", action="store_true")
    args = parser.parse_args()
    print(run_maintenance(args.days_back, args.days_forward, not args.skip_deep_today))


if __name__ == "__main__":
    main()
