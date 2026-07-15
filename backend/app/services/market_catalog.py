from __future__ import annotations

from dataclasses import dataclass

from app.models import Odds


@dataclass(frozen=True)
class MarketSpec:
    group: str
    family: str
    period: str
    team_scope: str
    selection: str
    line: float | None
    label: str

    @property
    def key(self) -> tuple[str, str, str, str, float | None]:
        return (self.family, self.period, self.team_scope, self.selection, self.line)

    @property
    def prediction_market(self) -> str:
        return f"tipstrr:{self.family}:{self.period}:{self.team_scope}"


SUPPORTED_FAMILIES = {
    "match_result",
    "draw_no_bet",
    "double_chance",
    "asian_handicap",
    "win_btts",
    "total_goals",
    "correct_score",
    "first_goal",
    "qualification",
}


def base_market_catalog() -> list[MarketSpec]:
    specs: list[MarketSpec] = []
    specs.extend(_result_markets("1X2", "match_result", "full_time", "Resultado final"))
    specs.extend(_result_markets("Resultado al descanso", "match_result", "first_half", "Resultado descanso"))
    specs.extend(_draw_no_bet())
    specs.extend(_double_chance())
    specs.extend(_win_btts())
    specs.extend(_totals("Goles partido", "full_time", "all", (1.5, 2.5, 3.0, 3.25)))
    specs.extend(_totals("Goles al descanso", "first_half", "all", (0.5, 1.0, 1.25)))
    specs.extend(_totals("Goles local", "full_time", "home", (1.5, 2.5)))
    specs.extend(_totals("Goles visitante", "full_time", "away", (0.5, 1.5)))
    specs.extend(_totals("1a parte local", "first_half", "home", (0.5,)))
    specs.extend(_totals("1a parte visitante", "first_half", "away", (0.5,)))
    specs.extend(_asian_handicaps("Handicap asiatico", "full_time", ((-1.0, 1.0), (-0.75, 0.75))))
    specs.extend(_asian_handicaps("Handicap asiatico 1a parte", "first_half", ((-0.5, 0.5), (-0.25, 0.25))))
    specs.extend(_correct_scores())
    specs.extend(_first_goal())
    specs.extend(_qualification())
    return specs


def supported_market_specs_from_odds(odds_rows: list[Odds]) -> list[MarketSpec]:
    specs: list[MarketSpec] = []
    for odd in odds_rows:
        family = odd.market_family or _legacy_family(odd.market)
        if family not in SUPPORTED_FAMILIES:
            continue
        period = odd.period or "full_time"
        team_scope = odd.team_scope or "all"
        specs.append(
            MarketSpec(
                group=_group_for(family, period, team_scope),
                family=family,
                period=period,
                team_scope=team_scope,
                selection=odd.selection,
                line=odd.line,
                label=_label_for(family, period, team_scope, odd.selection, odd.line),
            )
        )
    return specs


def merge_market_specs(*collections: list[MarketSpec]) -> list[MarketSpec]:
    merged: dict[tuple[str, str, str, str, float | None], MarketSpec] = {}
    for collection in collections:
        for spec in collection:
            merged.setdefault(spec.key, spec)
    return list(merged.values())


def _result_markets(group: str, family: str, period: str, label_prefix: str) -> list[MarketSpec]:
    return [
        MarketSpec(group, family, period, "all", "home", None, f"{label_prefix}: gana local"),
        MarketSpec(group, family, period, "all", "draw", None, f"{label_prefix}: empate"),
        MarketSpec(group, family, period, "all", "away", None, f"{label_prefix}: gana visitante"),
    ]


def _draw_no_bet() -> list[MarketSpec]:
    return [
        MarketSpec("Empate no apuesta", "draw_no_bet", "full_time", "all", "home", None, "Local empate no apuesta"),
        MarketSpec("Empate no apuesta", "draw_no_bet", "full_time", "all", "away", None, "Visitante empate no apuesta"),
    ]


def _double_chance() -> list[MarketSpec]:
    return [
        MarketSpec("Doble oportunidad", "double_chance", "full_time", "all", "1x", None, "Local o empate"),
        MarketSpec("Doble oportunidad", "double_chance", "full_time", "all", "x2", None, "Empate o visitante"),
        MarketSpec("Doble oportunidad", "double_chance", "full_time", "all", "12", None, "Local o visitante"),
    ]


def _win_btts() -> list[MarketSpec]:
    return [
        MarketSpec("Gana + ambos marcan", "win_btts", "full_time", "all", "home_yes", None, "Local gana y ambos marcan"),
        MarketSpec("Gana + ambos marcan", "win_btts", "full_time", "all", "away_yes", None, "Visitante gana y ambos marcan"),
        MarketSpec("Gana + ambos marcan", "win_btts", "full_time", "all", "draw_yes", None, "Empate y ambos marcan"),
    ]


def _totals(group: str, period: str, team_scope: str, lines: tuple[float, ...]) -> list[MarketSpec]:
    specs: list[MarketSpec] = []
    for line in lines:
        specs.append(MarketSpec(group, "total_goals", period, team_scope, "over", line, f"{_scope_label(team_scope, period)} mas de {line:g} goles"))
        specs.append(MarketSpec(group, "total_goals", period, team_scope, "under", line, f"{_scope_label(team_scope, period)} menos de {line:g} goles"))
    return specs


def _asian_handicaps(group: str, period: str, pairs: tuple[tuple[float, float], ...]) -> list[MarketSpec]:
    specs: list[MarketSpec] = []
    for home_line, away_line in pairs:
        period_label = " 1a parte" if period == "first_half" else ""
        specs.append(MarketSpec(group, "asian_handicap", period, "home", "handicap", home_line, f"Local{period_label} {home_line:+.2f}"))
        specs.append(MarketSpec(group, "asian_handicap", period, "away", "handicap", away_line, f"Visitante{period_label} {away_line:+.2f}"))
    return specs


def _correct_scores() -> list[MarketSpec]:
    scores = ("1-0", "0-0", "0-1", "2-0", "1-1", "0-2", "2-1", "1-2", "2-2", "3-0", "0-3", "3-1", "1-3")
    return [MarketSpec("Marcador correcto", "correct_score", "full_time", "all", score, None, score) for score in scores]


def _first_goal() -> list[MarketSpec]:
    return [
        MarketSpec("Primer gol", "first_goal", "full_time", "all", "home", None, "Primer gol local"),
        MarketSpec("Primer gol", "first_goal", "full_time", "all", "away", None, "Primer gol visitante"),
        MarketSpec("Primer gol", "first_goal", "full_time", "all", "no_goal", None, "Sin goles"),
    ]


def _qualification() -> list[MarketSpec]:
    return [
        MarketSpec("Se clasificara", "qualification", "full_time", "all", "home", None, "Local se clasificara"),
        MarketSpec("Se clasificara", "qualification", "full_time", "all", "away", None, "Visitante se clasificara"),
    ]


def _group_for(family: str, period: str, team_scope: str) -> str:
    if family == "match_result" and period == "first_half":
        return "Resultado al descanso"
    if family == "match_result":
        return "1X2"
    if family == "total_goals" and period == "first_half" and team_scope == "all":
        return "Goles al descanso"
    if family == "total_goals" and team_scope == "home":
        return "Goles local"
    if family == "total_goals" and team_scope == "away":
        return "Goles visitante"
    if family == "total_goals":
        return "Goles partido"
    if family == "asian_handicap" and period == "first_half":
        return "Handicap asiatico 1a parte"
    return {
        "draw_no_bet": "Empate no apuesta",
        "double_chance": "Doble oportunidad",
        "asian_handicap": "Handicap asiatico",
        "win_btts": "Gana + ambos marcan",
        "correct_score": "Marcador correcto",
        "first_goal": "Primer gol",
        "qualification": "Se clasificara",
    }.get(family, family)


def _label_for(family: str, period: str, team_scope: str, selection: str, line: float | None) -> str:
    if family == "total_goals" and line is not None:
        direction = "mas de" if selection == "over" else "menos de"
        return f"{_scope_label(team_scope, period)} {direction} {line:g} goles"
    if family == "asian_handicap" and line is not None:
        team = "Local" if team_scope == "home" else "Visitante"
        suffix = " 1a parte" if period == "first_half" else ""
        return f"{team}{suffix} {line:+.2f}"
    labels = {
        "home": "Local",
        "draw": "Empate",
        "away": "Visitante",
        "1x": "Local o empate",
        "x2": "Empate o visitante",
        "12": "Local o visitante",
        "home_yes": "Local gana y ambos marcan",
        "away_yes": "Visitante gana y ambos marcan",
        "draw_yes": "Empate y ambos marcan",
        "no_goal": "Sin goles",
    }
    return labels.get(selection, selection)


def _scope_label(team_scope: str, period: str) -> str:
    period_prefix = "1a parte " if period == "first_half" else ""
    if team_scope == "home":
        return f"{period_prefix}local"
    if team_scope == "away":
        return f"{period_prefix}visitante"
    if period == "first_half":
        return "1a parte"
    return "Partido"


def _legacy_family(market: str) -> str:
    return {"goals": "total_goals", "team_goals": "total_goals", "btts": "btts", "result": "match_result"}.get(market, market)
