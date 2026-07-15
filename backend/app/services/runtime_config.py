from __future__ import annotations

from app.core.config import get_settings

_pick_safety_mode_override: str | None = None

VALID_PICK_SAFETY_MODES = {"conservative", "normal", "aggressive"}


def get_pick_safety_mode() -> str:
    if _pick_safety_mode_override:
        return _pick_safety_mode_override
    mode = (get_settings().pick_safety_mode or "normal").strip().lower()
    return mode if mode in VALID_PICK_SAFETY_MODES else "normal"


def set_pick_safety_mode(mode: str) -> str:
    global _pick_safety_mode_override
    normalized = mode.strip().lower()
    if normalized not in VALID_PICK_SAFETY_MODES:
        raise ValueError(f"Modo no valido: {mode}")
    _pick_safety_mode_override = normalized
    return normalized

