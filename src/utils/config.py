"""YAML configuration loader with singleton caching."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Project root: world-game/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


@lru_cache(maxsize=32)
def load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the config/ directory.

    Args:
        filename: Filename relative to config/ dir, e.g. "game.yaml"
    """
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=32)
def load_json_data(filename: str) -> Any:
    """Load a JSON data file from the data/ directory."""
    import json

    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data_dir() -> Path:
    """Return the absolute path to the data/ directory."""
    return DATA_DIR
