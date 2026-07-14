from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import httpx

from app.collectors.base import FootballDataProvider
from app.core.config import get_settings


class ApiFootballProvider(FootballDataProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.api_football_key or self.settings.football_api_key
        if not self.api_key:
            raise RuntimeError("API_FOOTBALL_KEY or FOOTBALL_API_KEY is required for API-Football provider")
        self.base_url = self.settings.api_football_base_url.rstrip("/")
        self.headers = {"x-apisports-key": self.api_key}
        self._matches_by_date: dict[str, list[dict[str, Any]]] = {}
        self._competitions: dict[str, dict[str, Any]] = {}
        self._last_error: str | None = None

    def get_competitions(self) -> list[dict[str, Any]]:
        return list(self._competitions.values())

    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        payload = self._request("/fixtures", {"date": match_date.isoformat()})
        matches = [self._normalize_match(item, match_date) for item in _responses(payload)]
        matches = [match for match in matches if match is not None]
        self._matches_by_date[match_date.isoformat()] = matches
        return matches

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        fixture_id = _strip_prefix(match_id, "api-football-")
        rows = _responses(self._request("/fixtures", {"id": fixture_id}))
        return self._normalize_match(rows[0], date.today()) if rows else None

    def get_team_history(self, team_id: str) -> dict[str, Any]:
        api_team_id = _strip_prefix(team_id, "api-football-team-")
        payload = self._request("/fixtures", {"team": api_team_id, "last": 20})
        return _history_from_fixtures(_responses(payload), api_team_id)

    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        fixture_id = _strip_prefix(match_id, "api-football-")
        return _responses(self._request("/fixtures/statistics", {"fixture": fixture_id}))

    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        fixture_id = _strip_prefix(match_id, "api-football-")
        return _odds_from_payload(_responses(self._request("/odds", {"fixture": fixture_id})))

    def get_results(self, match_date: date) -> list[dict[str, Any]]:
        return _responses(self._request("/fixtures", {"date": match_date.isoformat(), "status": "FT-AET-PEN"}))

    def diagnostics(self, match_date: date) -> dict[str, Any]:
        try:
            status = self._request("/status", {})
            fixtures = self._request("/fixtures", {"date": match_date.isoformat()})
            return {
                "provider": "api_football",
                "base_url": self.base_url,
                "ok": True,
                "fixtures": len(_responses(fixtures)),
                "requests": status.get("response", {}).get("requests", {}),
                "last_error": self._last_error,
            }
        except Exception as exc:
            return {
                "provider": "api_football",
                "base_url": self.base_url,
                "ok": False,
                "fixtures": 0,
                "last_error": str(exc),
            }

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}{path}", headers=self.headers, params=params, timeout=25)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self._last_error = str(exc)
            raise RuntimeError(f"API-Football request failed for {path}: {exc}") from exc

        errors = payload.get("errors")
        if errors:
            self._last_error = str(errors)
            raise RuntimeError(f"API-Football returned errors for {path}: {errors}")
        return payload

    def _normalize_match(self, item: dict[str, Any], match_date: date) -> dict[str, Any] | None:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        home_raw = teams.get("home") or {}
        away_raw = teams.get("away") or {}
        fixture_id = fixture.get("id")
        home_id = home_raw.get("id")
        away_id = away_raw.get("id")
        if not fixture_id or not home_id or not away_id:
            return None

        competition_id = f"api-football-league-{league.get('id')}-{league.get('season') or match_date.year}"
        competition = {
            "external_id": competition_id,
            "name": str(league.get("name") or "Unknown Competition"),
            "country": str(league.get("country") or "Unknown"),
            "season": str(league.get("season") or match_date.year),
            "logo_url": league.get("logo"),
        }
        self._competitions[competition_id] = competition

        return {
            "external_id": f"api-football-{fixture_id}",
            "competition_external_id": competition_id,
            "competition": competition,
            "home_team": _team_from_api(home_raw),
            "away_team": _team_from_api(away_raw),
            "kickoff_at": _parse_fixture_datetime(fixture.get("date"), match_date),
            "status": ((fixture.get("status") or {}).get("short") or "scheduled").lower(),
            "venue": (fixture.get("venue") or {}).get("name"),
            "round": league.get("round"),
            "season": str(league.get("season") or match_date.year),
        }


def _responses(payload: Any) -> list[dict[str, Any]]:
    rows = payload.get("response", []) if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _strip_prefix(value: str, prefix: str) -> str:
    return str(value).replace(prefix, "", 1)


def _team_from_api(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or "Unknown Team")
    return {
        "external_id": f"api-football-team-{item.get('id')}",
        "name": name,
        "short_name": name[:3].upper(),
        "country": item.get("country"),
        "logo_url": item.get("logo"),
    }


def _parse_fixture_datetime(raw: Any, fallback_date: date) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.combine(fallback_date, datetime.min.time())


def _history_from_fixtures(fixtures: list[dict[str, Any]], team_id: str) -> dict[str, Any]:
    finished = [item for item in fixtures if ((item.get("fixture") or {}).get("status") or {}).get("short") in {"FT", "AET", "PEN"}]
    sample = len(finished)
    if not sample:
        return _empty_history()

    goals_for = goals_against = first_half_goals = second_half_goals = 0
    over_15 = over_25 = over_35 = btts = clean_sheets = 0

    for item in finished:
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}
        score = item.get("score") or {}
        is_home = str((teams.get("home") or {}).get("id")) == team_id
        team_goals = _to_int(goals.get("home" if is_home else "away")) or 0
        opponent_goals = _to_int(goals.get("away" if is_home else "home")) or 0
        total_goals = team_goals + opponent_goals
        halftime = score.get("halftime") or {}
        first_half_total = (_to_int(halftime.get("home")) or 0) + (_to_int(halftime.get("away")) or 0)

        goals_for += team_goals
        goals_against += opponent_goals
        first_half_goals += first_half_total
        second_half_goals += max(total_goals - first_half_total, 0)
        over_15 += int(total_goals > 1.5)
        over_25 += int(total_goals > 2.5)
        over_35 += int(total_goals > 3.5)
        btts += int(team_goals > 0 and opponent_goals > 0)
        clean_sheets += int(opponent_goals == 0)

    return {
        **_empty_history(),
        "matches_sample": sample,
        "goals_for_avg": round(goals_for / sample, 3),
        "goals_against_avg": round(goals_against / sample, 3),
        "first_half_goals_avg": round(first_half_goals / sample, 3),
        "second_half_goals_avg": round(second_half_goals / sample, 3),
        "over_1_5_goals_rate": round(over_15 / sample, 4),
        "over_2_5_goals_rate": round(over_25 / sample, 4),
        "over_3_5_goals_rate": round(over_35 / sample, 4),
        "btts_rate": round(btts / sample, 4),
        "clean_sheet_rate": round(clean_sheets / sample, 4),
        "home_away_sample": sample,
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


def _odds_from_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    odds: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, float | None, str]] = set()
    for fixture_odds in rows:
        fixture_id = str((fixture_odds.get("fixture") or {}).get("id") or "")
        provider_competition_id = str((fixture_odds.get("league") or {}).get("id") or "")
        for bookmaker in fixture_odds.get("bookmakers") or []:
            bookmaker_name = str(bookmaker.get("name") or "API-Football")
            for bet in bookmaker.get("bets") or []:
                bet_name = str(bet.get("name") or "")
                for value in bet.get("values") or []:
                    normalized = _normalize_odd_value(bet_name, value)
                    if not normalized:
                        continue
                    key = (
                        normalized["market_family"],
                        normalized["period"],
                        normalized["team_scope"],
                        normalized["selection"],
                        normalized["line"],
                        bookmaker_name,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    odds.append(
                        {
                            "provider": "api_football",
                            "bookmaker": bookmaker_name,
                            "event_id": fixture_id,
                            "fixture_id": fixture_id,
                            "provider_competition_id": provider_competition_id,
                            "market_name_raw": bet_name,
                            "raw_payload": json.dumps({"bet": bet_name, "value": value}, ensure_ascii=False),
                            "validation_status": "mapped",
                            **normalized,
                        }
                    )
    return odds


def _normalize_odd_value(bet_name: str, value: dict[str, Any]) -> dict[str, Any] | None:
    selection_name = str(value.get("value") or "")
    odd = _to_float(value.get("odd"))
    if not odd or odd <= 1:
        return None

    bet_lower = bet_name.lower()
    selection_lower = selection_name.lower()
    if bet_lower in {"match winner", "1x2", "fulltime result"} or "match winner" in bet_lower or "half time result" in bet_lower:
        selection = {"home": "home", "1": "home", "draw": "draw", "x": "draw", "away": "away", "2": "away"}.get(selection_lower)
        if selection:
            return _odd("result", "match_result", _period_from_bet(bet_lower), "all", selection, None, odd)

    if "double chance" in bet_lower:
        selection = {"1X": "1x", "X2": "x2", "12": "12"}.get(selection_name.upper().replace(" ", ""))
        if selection:
            return _odd("double_chance", "double_chance", "full_time", "all", selection, None, odd)

    if "draw no bet" in bet_lower:
        selection = {"home": "home", "1": "home", "away": "away", "2": "away"}.get(selection_lower)
        if selection:
            return _odd("draw_no_bet", "draw_no_bet", "full_time", "all", selection, None, odd)

    if ("winner" in bet_lower or "result" in bet_lower) and "both teams" in bet_lower:
        compact = selection_lower.replace(" ", "").replace("&", "").replace("+", "")
        selection = {
            "homeyes": "home_yes",
            "1yes": "home_yes",
            "awayyes": "away_yes",
            "2yes": "away_yes",
            "drawyes": "draw_yes",
            "xyes": "draw_yes",
        }.get(compact)
        if selection:
            return _odd("win_btts", "win_btts", _period_from_bet(bet_lower), "all", selection, None, odd)

    if "first goal" in bet_lower or "first team to score" in bet_lower:
        selection = {"home": "home", "1": "home", "away": "away", "2": "away", "no goal": "no_goal", "none": "no_goal"}.get(selection_lower)
        if selection:
            return _odd("first_goal", "first_goal", _period_from_bet(bet_lower), "all", selection, None, odd)

    if "to qualify" in bet_lower or "qualification" in bet_lower:
        selection = {"home": "home", "1": "home", "away": "away", "2": "away"}.get(selection_lower)
        if selection:
            return _odd("qualification", "qualification", "full_time", "all", selection, None, odd)

    if "correct score" in bet_lower:
        if "-" in selection_name:
            return _odd("correct_score", "correct_score", "full_time", "all", selection_name.replace(" ", ""), None, odd)

    if "asian handicap" in bet_lower or bet_lower in {"handicap result", "handicap"}:
        handicap = _handicap_from_selection(selection_name)
        if handicap:
            team_scope, line = handicap
            period = "first_half" if "1st half" in bet_lower or "first half" in bet_lower else "full_time"
            return _odd("asian_handicap", "asian_handicap", period, team_scope, "handicap", line, odd)

    if "both teams" in bet_lower and selection_lower in {"yes", "no", "si", "sí", "sÃ­"}:
        selection = "yes" if selection_lower in {"yes", "si", "sí", "sÃ­"} else "no"
        return _odd("btts", "btts", _period_from_bet(bet_lower), "all", selection, None, odd)

    if "over/under" in bet_lower or "goals over" in bet_lower or "total goals" in bet_lower:
        line = _line_from_selection(selection_name)
        if line is not None and selection_lower.startswith(("over", "under")):
            selection = "over" if selection_lower.startswith("over") else "under"
            team_scope = _team_scope_from_bet(bet_lower)
            legacy_market = "team_goals" if team_scope in {"home", "away"} else "goals"
            return _odd(legacy_market, "total_goals", _period_from_bet(bet_lower), team_scope, selection, line, odd)
    return None


def _odd(
    legacy_market: str,
    market_family: str,
    period: str,
    team_scope: str,
    selection: str,
    line: float | None,
    odds: float,
) -> dict[str, Any]:
    return {
        "market": legacy_market,
        "market_family": market_family,
        "period": period,
        "team_scope": team_scope,
        "selection": selection,
        "line": line,
        "odds": odds,
    }


def _period_from_bet(bet_lower: str) -> str:
    if "1st half" in bet_lower or "first half" in bet_lower or "1st period" in bet_lower:
        return "first_half"
    if "2nd half" in bet_lower or "second half" in bet_lower or "2nd period" in bet_lower:
        return "second_half"
    return "full_time"


def _team_scope_from_bet(bet_lower: str) -> str:
    if "home team" in bet_lower or "home goals" in bet_lower or "team 1" in bet_lower:
        return "home"
    if "away team" in bet_lower or "away goals" in bet_lower or "team 2" in bet_lower:
        return "away"
    return "all"


def _handicap_from_selection(selection_name: str) -> tuple[str, float] | None:
    value = selection_name.replace(",", ".")
    parts = value.split()
    line = None
    for part in parts:
        candidate = _to_float(part)
        if candidate is not None:
            line = candidate
            break
    if line is None:
        return None
    lowered = value.lower()
    if "away" in lowered or lowered.startswith("2 ") or lowered.startswith("2"):
        return "away", line
    return "home", line


def _line_from_selection(value: str) -> float | None:
    for part in value.replace(",", ".").split():
        line = _to_float(part)
        if line is not None:
            return line
    return None


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
