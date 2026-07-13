from app.predictors.corners_over_95 import CornersOver95Predictor
from app.predictors.goals import goals_predictors


def get_predictors():
    return [*goals_predictors(), CornersOver95Predictor()]
