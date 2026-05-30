"""Configuration management for Agent Monitor."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml

# Default paths
DATA_DIR = Path.home() / ".agent-monitor"
DB_PATH = DATA_DIR / "usage.db"
CONFIG_PATH = DATA_DIR / "config.yaml"

# Package-level config/pricing files
PKG_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = PKG_DIR / "config" / "default.yaml"
PRICING_PATH = PKG_DIR / "config" / "pricing.yaml"


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    """Save data to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


class Config:
    """Application configuration manager."""

    def __init__(self) -> None:
        ensure_data_dir()
        self._defaults = load_yaml(DEFAULT_CONFIG_PATH)
        self._user_config = load_yaml(CONFIG_PATH)
        self._pricing = load_yaml(PRICING_PATH)

    @property
    def db_path(self) -> Path:
        raw = (
            self._user_config.get("database", {}).get("path")
            or self._defaults.get("database", {}).get("path")
            or str(DB_PATH)
        )
        return Path(os.path.expanduser(raw))

    @property
    def monthly_budget(self) -> Optional[float]:
        limit = (
            self._user_config.get("budget", {}).get("monthly_limit")
            or self._defaults.get("budget", {}).get("monthly_limit")
        )
        return float(limit) if limit is not None else None

    @monthly_budget.setter
    def monthly_budget(self, value: Optional[float]) -> None:
        if "budget" not in self._user_config:
            self._user_config["budget"] = {}
        self._user_config["budget"]["monthly_limit"] = value
        save_yaml(CONFIG_PATH, self._user_config)

    @property
    def warn_threshold(self) -> float:
        return (
            self._user_config.get("budget", {}).get("warn_threshold")
            or self._defaults.get("budget", {}).get("warn_threshold")
            or 0.8
        )

    @property
    def pricing(self) -> dict[str, Any]:
        return self._pricing

    @property
    def export_dir(self) -> Path:
        raw = (
            self._user_config.get("export", {}).get("output_dir")
            or self._defaults.get("export", {}).get("output_dir")
            or str(DATA_DIR / "exports")
        )
        return Path(os.path.expanduser(raw))

    def get_model_pricing(
        self, provider: str, model: str
    ) -> Optional[dict[str, float]]:
        """Get pricing for a specific model. Returns dict with 'input' and 'output' per 1M tokens."""
        providers = self._pricing.get("providers", {})
        prov = providers.get(provider.lower(), {})
        models = prov.get("models", {})
        return models.get(model)

    def calculate_cost(
        self, provider: str, model: str, tokens_in: int, tokens_out: int
    ) -> float:
        """Calculate cost for a given token usage."""
        pricing = self.get_model_pricing(provider, model)
        if pricing is None:
            return 0.0
        cost_in = (tokens_in / 1_000_000) * pricing.get("input", 0)
        cost_out = (tokens_out / 1_000_000) * pricing.get("output", 0)
        return round(cost_in + cost_out, 6)

    def list_providers(self) -> list[str]:
        """List all configured providers."""
        return list(self._pricing.get("providers", {}).keys())

    def list_models(self, provider: str) -> list[str]:
        """List all models for a provider."""
        providers = self._pricing.get("providers", {})
        prov = providers.get(provider.lower(), {})
        return list(prov.get("models", {}).keys())
