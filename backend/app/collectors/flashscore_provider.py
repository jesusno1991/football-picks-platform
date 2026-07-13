from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from app.collectors.base import FootballDataProvider
from app.core.config import get_settings


class FlashScoreRapidApiProvider(FootballDataProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.rapidapi_key:
            raise RuntimeError("RAPIDAPI_KEY is required for FlashScore provider")
        self.base_url = f"https://{self.settings.flashscore_rapidapi_host}"
        self.headers = {
            "x-rapidapi-key": self.settings.rapidapi_key,
            "x-rapidapi-host": self.settings.flashscore_rapidapi_host,
        }
        self._matches_by_date: dict[str, list[dict[str, Any]]] = {}
        self._last_error: str | None = None

    def get_competitions(self) -> list[dict[str, Any]]:
        competitions: dict[str, dict[str, Any]] = {}
        for matches in self._matches_by_date.values():
            for match in matches:
                competition = match["competition"]
                competitions[competition["external_id"]] = competition
        return list(competitions.values())

    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        key = match_date.isoformat()
        raw = self._fetch_matches(match_date)
        matches = [self._normalize_match(item, match_date) for item in _find_match_nodes(raw)]
        matches = [match for match in matches if match is not None]
        self._matches_by_date[key] = matches
        return matches

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        return None

    def get_team_history(self, team_id: str) -> dict[str, Any]:
        # FlashScore history endpoints vary by RapidAPI product. Until a valid endpoint
        # is configured, return an explicit low-sample profile so predictors avoid fake confidence.
        return {
            "matches_sample": 0,
            "goals_for_avg": None,
            "goals_against_avg": None,
            "first_half_goals_avg": None,
            "second_half_goals_avg": None,
            "corners_for_avg": None,
            "corners_against_avg": None,
            "shots_avg": None,
            "shots_on_target_avg": None,
            "xg_avg": None,
            "xga_avg": None,
            "big_chances_avg": None,
            "dangerous_attacks_avg": None,
            "possession_avg": None,
            "over_8_5_corners_rate": None,
            "over_9_5_corners_rate": None,
            "over_10_5_corners_rate": None,
            "btts_rate": None,
            "over_1_5_goals_rate": None,
            "over_2_5_goals_rate": None,
            "over_3_5_goals_rate": None,
            "home_away_sample": 0,
            "h2h_goals_avg": None,
            "h2h_btts_rate": None,
            "clean_sheet_rate": None,
        }

    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        return []

    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        return []

    def get_results(self, match_date: date) -> list[dict[str, Any]]:
        return []

    def diagnostics(self, match_date: date) -> dict[str, Any]:
        try:
            raw = self._fetch_matches(match_date)
            nodes = _find_match_nodes(raw)
            return {
                "provider": "flashscore_rapidapi",
                "host": self.settings.flashscore_rapidapi_host,
                "ok": True,
                "match_nodes": len(nodes),
                "last_error": self._last_error,
            }
        except Exception as exc:
            return {
                "provider": "flashscore_rapidapi",
                "host": self.settings.flashscore_rapidapi_host,
                "ok": False,
                "match_nodes": 0,
                "last_error": str(exc),
            }

    def _fetch_matches(self, match_date: date) -> Any:
        errors: list[str] = []
        for path in self._candidate_match_paths(match_date):
            try:
                response = httpx.get(
                    f"{self.base_url}{path}",
                    headers=self.headers,
                    timeout=20,
                )
                if response.status_code == 200:
                    return response.json()
                errors.append(f"{path}: {response.status_code} {response.text[:160]}")
            except httpx.HTTPError as exc:
                errors.append(f"{path}: {exc}")
        self._last_error = " | ".join(errors[:6])
        raise RuntimeError(f"FlashScore endpoints unavailable: {self._last_error}")

    def _candidate_match_paths(self, match_date: date) -> list[str]:
        formatted = match_date.isoformat()
        configured = self.settings.flashscore_matches_path
        paths = [configured] if configured else []
        paths.extend(
            [
                f"/api/football/matches?date={formatted}",
                f"/api/matches?date={formatted}",
                f"/api/events?date={formatted}",
                f"/matches?date={formatted}",
                f"/events?date={formatted}",
                f"/matches/list-by-date?category=soccer&date={formatted}",
                f"/matches/v2/list-by-date?category=soccer&date={formatted}",
                f"/v2/matches/list-by-date?category=soccer&date={formatted}",
                f"/football/matches?date={formatted}",
            ]
        )
        return [path for path in paths if path]

    def _normalize_match(self, item: dict[str, Any], match_date: date) -> dict[str, Any] | None:
        home = _pick_team(item, "home")
        away = _pick_team(item, "away")
        if not home or not away:
            return None

        competition_name = _first_text(
            item,
            ["league.name", "tournament.name", "competition.name", "category.name", "event.tournament.name"],
            default="Unknown Competition",
        )
        country = _first_text(
            item,
            ["country.name", "league.country.name", "tournament.category.name", "category.country.name"],
            default="Unknown",
        )
        competition_id = _first_text(
            item,
            ["league.id", "tournament.id", "competition.id", "category.id"],
            default=f"flashscore-{country}-{competition_name}",
        )
        external_id = _first_text(item, ["id", "eventId", "matchId", "fixtureId"], default=f"{home['external_id']}-{away['external_id']}-{match_date}")
        kickoff_at = _parse_datetime(item, match_date)

        return {
            "external_id": f"flashscore-{external_id}",
            "competition_external_id": f"flashscore-{competition_id}",
            "competition": {
                "external_id": f"flashscore-{competition_id}",
                "name": competition_name,
                "country": country,
                "season": str(match_date.year),
                "logo_url": None,
            },
            "home_team": home,
            "away_team": away,
            "kickoff_at": kickoff_at,
            "venue": _first_text(item, ["venue.name", "stadium.name"], default=None),
            "round": _first_text(item, ["round.name", "round"], default=None),
            "season": str(match_date.year),
        }


def _find_match_nodes(payload: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        if _pick_team(payload, "home") and _pick_team(payload, "away"):
            nodes.append(payload)
        for value in payload.values():
            nodes.extend(_find_match_nodes(value))
    elif isinstance(payload, list):
        for value in payload:
            nodes.extend(_find_match_nodes(value))
    return nodes


def _pick_team(item: dict[str, Any], side: str) -> dict[str, Any] | None:
    candidates = [
        f"{side}Team",
        f"{side}_team",
        side,
        f"{side}Participant",
        f"{side}Competitor",
    ]
    for key in candidates:
        value = item.get(key)
        if isinstance(value, dict):
            name = _first_text(value, ["name", "shortName", "participantName", "teamName"], default=None)
            if name:
                external_id = _first_text(value, ["id", "teamId", "participantId"], default=name)
                return {
                    "external_id": f"flashscore-team-{external_id}",
                    "name": name,
                    "short_name": _first_text(value, ["shortName", "abbr"], default=name[:3].upper()),
                    "country": _first_text(value, ["country.name", "country"], default=None),
                    "logo_url": _first_text(value, ["logo", "logoUrl", "image"], default=None),
                }
    return None


def _first_text(item: dict[str, Any], paths: list[str], default: Any = "") -> Any:
    for path in paths:
        value: Any = item
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value not in (None, ""):
            return str(value)
    return default


def _parse_datetime(item: dict[str, Any], match_date: date) -> datetime:
    raw = _first_text(item, ["startTime", "startTimestamp", "time", "kickoff", "startDate"], default=None)
    if raw:
        try:
            if str(raw).isdigit():
                value = int(raw)
                if value > 10_000_000_000:
                    value = int(value / 1000)
                return datetime.fromtimestamp(value)
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.combine(match_date, datetime.min.time())
