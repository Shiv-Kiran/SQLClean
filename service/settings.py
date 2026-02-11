"""Centralized environment-driven settings."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    google_api_key: Optional[str]
    model_name: str
    default_temperature: float
    default_max_retries: int


def _to_float(value: Optional[str], fallback: float) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def _to_int(value: Optional[str], fallback: int) -> int:
    if value is None:
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        model_name=os.getenv("SQLCLEAN_MODEL", "gemini-2.5-flash"),
        default_temperature=_to_float(os.getenv("SQLCLEAN_TEMPERATURE"), 0.1),
        default_max_retries=_to_int(os.getenv("SQLCLEAN_MAX_RETRIES"), 2),
    )

