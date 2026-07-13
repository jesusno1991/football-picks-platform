from sqlalchemy.orm import Session

from app.models import Prediction


def verify_results(db: Session) -> dict[str, int]:
    checked = 0
    for prediction in db.query(Prediction).filter(Prediction.status == "published", Prediction.result.is_(None)).all():
        match = prediction.match
        if match.status != "finished":
            continue
        if prediction.market == "corners" and prediction.selection == "over" and prediction.line is not None:
            total = (match.home_corners or 0) + (match.away_corners or 0)
            if total > prediction.line:
                prediction.result = "win"
                prediction.profit = round((prediction.available_odds or 1) * prediction.recommended_stake - prediction.recommended_stake, 2)
            elif total == prediction.line:
                prediction.result = "void"
                prediction.profit = 0
            else:
                prediction.result = "loss"
                prediction.profit = -prediction.recommended_stake
            checked += 1
    db.commit()
    return {"verified": checked}
