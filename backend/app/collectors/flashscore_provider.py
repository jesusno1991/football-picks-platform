from __future__ import annotations

from datetime import date, datetime, timezone
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
            "Content-Type": "application/json",
            "x-rapidapi-key": self.settings.rapidapi_key,
            "x-rapidapi-host": self.settings.flashscore_rapidapi_host,
        }
        self._matches_by_date: dict[str, list[dict[str, Any]]] = {}
        self._odds_by_match: dict[str, dict[str, Any]] = {}
        self._history_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._last_error: str | None = None

    def get_competitions(self) -> list[dict[str, Any]]:
        competitions: dict[str, dict[str, Any]] = {}
        for matches in self._matches_by_date.values():
            for match in matches:
                competition = match["competition"]
                competitions[competition["external_id"]] = competition
        return list(competitions.values())

    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        raw = self._fetch_matches(match_date)
        matches = [self._normalize_match(item, match_date) for item in _find_match_nodes(raw)]
        matches = [match for match in matches if match is not None]
        self._odds_by_match = {match["external_id"]: match.get("raw_odds", {}) for match in matches}
        self._matches_by_date[match_date.isoformat()] = matches
        return matches

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        return None

    def get_team_history(self, team_id: str) -> dict[str, Any]:
        return _empty_history()

    def get_team_history_for_match(self, match_id: str, team_id: str) -> dict[str, Any]:
        match_key = match_id.replace("flashscore-", "")
        team_key = team_id.replace("flashscore-team-", "")
        if match_key not in self._history_cache:
            self._history_cache[match_key] = self._load_match_history(match_key)
        return self._history_cache[match_key].get(team_key, _empty_history())

    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        return _as_list(self._safe_get(f"/api/flashscore/v2/matches/match/stats?match_id={match_id}", default=[]))

    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        raw = self._odds_by_match.get(match_id, {})
        odds: list[dict[str, Any]] = []
        mapping = {"1": "home", "X": "draw", "2": "away"}
        if isinstance(raw, dict):
            for source_selection, selection in mapping.items():
                value = raw.get(source_selection)
                if value:
                    odds.append(
                        {
                            "bookmaker": "FlashScore",
                            "market": "result",
                            "selection": selection,
                            "line": None,
                            "odds": float(value),
                        }
                    )
        return odds

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
                response = httpx.get(f"{self.base_url}{path}", headers=self.headers, timeout=20)
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
        paths = [configured.format(date=formatted)] if configured else []
        paths.append(f"/api/flashscore/v2/matches/list-by-date?sport_id=1&date={formatted}&timezone=Europe%2FMadrid")
        paths.append("/api/flashscore/v2/matches/list?sport_id=1&day=0&timezone=Europe%2FMadrid")
        paths.append("/api/flashscore/v2/matches/live?sport_id=1&timezone=Europe%2FMadrid")
        return [path for path in paths if path]

    def _load_match_history(self, match_id: str) -> dict[str, dict[str, Any]]:
        form = self._safe_get(f"/api/flashscore/v2/matches/standings/form?match_id={match_id}&type=overall", default=[])
        over15 = self._safe_get(
            f"/api/flashscore/v2/matches/standings/over-under?match_id={match_id}&type=overall&sub_type=1.5",
            default=[],
        )
        over25 = self._safe_get(
            f"/api/flashscore/v2/matches/standings/over-under?match_id={match_id}&type=overall&sub_type=2.5",
            default=[],
        )
        over35 = self._safe_get(
            f"/api/flashscore/v2/matches/standings/over-under?match_id={match_id}&type=overall&sub_type=3.5",
            default=[],
        )
        rows: dict[str, dict[str, Any]] = {}
        for item in _as_list(over15):
            team_id = str(item.get("team_id") or "")
            if team_id:
                rows.setdefault(team_id, _empty_history()).update(_history_from_over_under(item, "over_1_5_goals_rate"))
        for item in _as_list(over25):
            team_id = str(item.get("team_id") or "")
            if team_id:
                rows.setdefault(team_id, _empty_history()).update(_history_from_over_under(item, "over_2_5_goals_rate"))
        for item in _as_list(over35):
            team_id = str(item.get("team_id") or "")
            if team_id:
                rows.setdefault(team_id, _empty_history()).update(_history_from_over_under(item, "over_3_5_goals_rate"))
        for item in _as_list(form):
            team_id = str(item.get("team_id") or "")
            if team_id:
                rows.setdefault(team_id, _empty_history()).update(_history_from_form(item))
        return rows

    def _safe_get(self, path: str, default: Any) -> Any:
        try:
            response = httpx.get(f"{self.base_url}{path}", headers=self.headers, timeout=20)
            if response.status_code == 200:
                return response.json()
        except httpx.HTTPError:
            pass
        return default

    def _normalize_match(self, item: dict[str, Any], match_date: date) -> dict[str, Any] | None:
        home = _pick_team(item, "home")
        away = _pick_team(item, "away")
        if not home or not away:
            return None

        competition_name = _first_text(
            item,
            ["tournament_name", "league.name", "tournament.name", "competition.name", "category.name"],
            default="Unknown Competition",
        )
        country = _first_text(item, ["country_name", "country.name", "league.country.name"], default="Unknown")
        competition_id = _first_text(
            item,
            ["tournament_id", "league.id", "tournament.id", "competition.id"],
            default=f"flashscore-{country}-{competition_name}",
        )
        external_id = _first_text(
            item,
            ["match_id", "id", "eventId", "matchId", "fixtureId"],
            default=f"{home['external_id']}-{away['external_id']}-{match_date}",
        )
        return {
            "external_id": f"flashscore-{external_id}",
            "competition_external_id": f"flashscore-{competition_id}",
            "competition": {
                "external_id": f"flashscore-{competition_id}",
                "name": competition_name,
                "country": country,
                "season": str(match_date.year),
                "logo_url": _first_text(item, ["tournament_image_path"], default=None),
            },
            "home_team": home,
            "away_team": away,
            "kickoff_at": _parse_datetime(item, match_date),
            "venue": _first_text(item, ["venue.name", "stadium.name"], default=None),
            "round": _first_text(item, ["round.name", "round"], default=None),
            "season": str(match_date.year),
            "raw_odds": item.get("odds") or {},
        }


def _empty_history() -> dict[str, Any]:
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


def _history_from_over_under(item: dict[str, Any], key: str) -> dict[str, Any]:
    matches = _to_int(item.get("matches_played")) or 0
    over = _to_int(item.get("over")) or 0
    goals_for, goals_against = _split_goals(item.get("goals"))
    average_goals = _to_float(item.get("average_goals_per_match"))
    return {
        "matches_sample": matches,
        "goals_for_avg": round(goals_for / matches, 3) if matches and goals_for is not None else None,
        "goals_against_avg": round(goals_against / matches, 3) if matches and goals_against is not None else None,
        "first_half_goals_avg": round((average_goals or 0) * 0.43, 3) if average_goals else None,
        "second_half_goals_avg": round((average_goals or 0) * 0.57, 3) if average_goals else None,
        "home_away_sample": matches,
        key: round(over / matches, 4) if matches else None,
    }


def _history_from_form(item: dict[str, Any]) -> dict[str, Any]:
    matches = _to_int(item.get("matches_played")) or 0
    goals_for, goals_against = _split_goals(item.get("goals"))
    return {
        "goals_for_avg": round(goals_for / matches, 3) if matches and goals_for is not None else None,
        "goals_against_avg": round(goals_against / matches, 3) if matches and goals_against is not None else None,
        "home_away_sample": matches,
    }


def _split_goals(value: Any) -> tuple[int | None, int | None]:
    if not isinstance(value, str) or ":" not in value:
        return None, None
    left, right = value.split(":", 1)
    return _to_int(left), _to_int(right)


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _find_match_nodes(payload: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("matches"), list):
            tournament = {
                "tournament_id": payload.get("tournament_id"),
                "tournament_url": payload.get("tournament_url"),
                "tournament_name": payload.get("name"),
                "country_name": payload.get("country_name"),
                "tournament_image_path": payload.get("image_path"),
            }
            for match in payload["matches"]:
                if isinstance(match, dict):
                    nodes.extend(_find_match_nodes({**match, **tournament}))
        if _pick_team(payload, "home") and _pick_team(payload, "away"):
            nodes.append(payload)
        for value in payload.values():
            nodes.extend(_find_match_nodes(value))
    elif isinstance(payload, list):
        for value in payload:
            nodes.extend(_find_match_nodes(value))
    return nodes


def _pick_team(item: dict[str, Any], side: str) -> dict[str, Any] | None:
    for key in (f"{side}Team", f"{side}_team", side, f"{side}Participant", f"{side}Competitor"):
        value = item.get(key)
        if isinstance(value, dict):
            name = _first_text(value, ["name", "shortName", "participantName", "teamName"], default=None)
            if name:
                external_id = _first_text(value, ["id", "teamId", "team_id", "participantId"], default=name)
                return {
                    "external_id": f"flashscore-team-{external_id}",
                    "name": name,
                    "short_name": _first_text(value, ["shortName", "short_name", "abbr"], default=name[:3].upper()),
                    "country": _first_text(value, ["country.name", "country"], default=None),
                    "logo_url": _first_text(value, ["logo", "logoUrl", "image", "small_image_path"], default=None),
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
    raw = _first_text(item, ["timestamp", "startTime", "startTimestamp", "time", "kickoff", "startDate"], default=None)
    if raw:
        try:
            if str(raw).isdigit():
                value = int(raw)
                if value > 10_000_000_000:
                    value = int(value / 1000)
                return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return datetime.combine(match_date, datetime.min.time())
