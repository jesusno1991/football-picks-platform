from datetime import date, datetime, time, timedelta
from typing import Any

from app.collectors.base import FootballDataProvider


class MockFootballDataProvider(FootballDataProvider):
    def get_competitions(self) -> list[dict[str, Any]]:
        return [
            {"external_id": "mock-epl", "name": "Premier Demo", "country": "England", "season": "2026", "logo_url": None},
            {"external_id": "mock-liga", "name": "Liga Demo", "country": "Spain", "season": "2026", "logo_url": None},
        ]

    def get_matches(self, match_date: date) -> list[dict[str, Any]]:
        base = datetime.combine(match_date, time(hour=18))
        return [
            {
                "external_id": f"mock-ars-che-{match_date.isoformat()}",
                "competition_external_id": "mock-epl",
                "home_team": {"external_id": "mock-ars", "name": "Arsenal Demo", "short_name": "ARS", "country": "England"},
                "away_team": {"external_id": "mock-che", "name": "Chelsea Demo", "short_name": "CHE", "country": "England"},
                "kickoff_at": base + timedelta(hours=1),
                "venue": "North London Stadium",
                "round": "Round 12",
                "season": "2026",
            },
            {
                "external_id": f"mock-bar-mad-{match_date.isoformat()}",
                "competition_external_id": "mock-liga",
                "home_team": {"external_id": "mock-bar", "name": "Barcelona Demo", "short_name": "BAR", "country": "Spain"},
                "away_team": {"external_id": "mock-mad", "name": "Madrid Demo", "short_name": "MAD", "country": "Spain"},
                "kickoff_at": base + timedelta(hours=3),
                "venue": "Mediterranean Arena",
                "round": "Round 10",
                "season": "2026",
            },
        ]

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        return None

    def get_team_history(self, team_id: str) -> dict[str, Any]:
        profiles = {
            "mock-ars": (20, 2.05, 1.05, 6.2, 4.1, 14.2, 5.4, 1.95, 1.05, 58.0, 0.86, 0.64),
            "mock-che": (20, 1.72, 1.28, 5.4, 5.0, 12.5, 4.8, 1.62, 1.34, 53.0, 0.78, 0.58),
            "mock-bar": (20, 2.25, 0.95, 7.0, 3.8, 16.8, 6.1, 2.18, 0.92, 62.0, 0.90, 0.71),
            "mock-mad": (20, 2.10, 1.10, 6.7, 4.3, 15.4, 5.9, 2.02, 1.08, 59.0, 0.88, 0.68),
        }
        sample, gf, ga, corners_for, corners_against, shots, sot, xg, xga, possession, over15, over95 = profiles.get(
            team_id, (4, 1.0, 1.0, 4.0, 4.0, 9.0, 3.0, 1.0, 1.0, 50.0, 0.55, 0.45)
        )
        return {
            "matches_sample": sample,
            "goals_for_avg": gf,
            "goals_against_avg": ga,
            "first_half_goals_avg": round((gf + ga) * 0.42, 2),
            "second_half_goals_avg": round((gf + ga) * 0.58, 2),
            "corners_for_avg": corners_for,
            "corners_against_avg": corners_against,
            "shots_avg": shots,
            "shots_on_target_avg": sot,
            "xg_avg": xg,
            "xga_avg": xga,
            "big_chances_avg": round(sot * 0.55, 2),
            "dangerous_attacks_avg": round(shots * 4.2, 2),
            "possession_avg": possession,
            "over_8_5_corners_rate": min(0.95, over95 + 0.1),
            "over_9_5_corners_rate": over95,
            "over_10_5_corners_rate": max(0.1, over95 - 0.12),
            "btts_rate": 0.62 if gf > 1.5 and ga > 1.0 else 0.48,
            "over_1_5_goals_rate": over15,
            "over_2_5_goals_rate": max(0.32, over15 - 0.22),
            "over_3_5_goals_rate": max(0.18, over15 - 0.44),
            "home_away_sample": max(5, int(sample / 2)),
            "h2h_goals_avg": round(gf + ga, 2),
            "h2h_btts_rate": 0.58,
            "clean_sheet_rate": 0.28,
        }

    def get_match_statistics(self, match_id: str) -> list[dict[str, Any]]:
        return []

    def get_odds(self, match_id: str) -> list[dict[str, Any]]:
        return [
            {"bookmaker": "MockBook", "market": "goals", "selection": "over", "line": 1.5, "odds": 1.52},
            {"bookmaker": "MockBook", "market": "goals", "selection": "over", "line": 2.5, "odds": 1.90},
            {"bookmaker": "MockBook", "market": "goals", "selection": "over", "line": 3.5, "odds": 3.10},
            {"bookmaker": "MockBook", "market": "btts", "selection": "yes", "line": None, "odds": 1.82},
            {"bookmaker": "MockBook", "market": "corners", "selection": "over", "line": 9.5, "odds": 1.95},
        ]

    def get_results(self, match_date: date) -> list[dict[str, Any]]:
        return []
