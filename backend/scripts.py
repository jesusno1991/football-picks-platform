import argparse
from datetime import date

from app.database import init_db, SessionLocal
from app.services.collection_service import collect_mock_data, upsert_prediction_systems
from app.services.prediction_service import generate_predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "load-mock", "generate-predictions"])
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        if args.command == "init-db":
            print({"status": "ok", "systems": upsert_prediction_systems(db)})
        elif args.command == "load-mock":
            print(collect_mock_data(db, date.today()))
        elif args.command == "generate-predictions":
            print(generate_predictions(db))


if __name__ == "__main__":
    main()
