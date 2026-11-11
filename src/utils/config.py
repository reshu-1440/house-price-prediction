"""Configuration loading, path resolution, and logging utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_REL_PATH = Path("config") / "config.yaml"


def get_project_root() -> Path:
    """Return the repository root directory resolved relative to this module."""
    return Path(__file__).resolve().parent.parent.parent


def resolve_path(path_value: str | Path, base_dir: Path | None = None) -> Path:
    """Resolve a relative path against ``base_dir`` (defaulting to project root)."""
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    root = base_dir if base_dir is not None else get_project_root()
    return (root / candidate).resolve()


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML configuration from ``config_path`` or the default project config."""
    target_path = (
        resolve_path(config_path)
        if config_path is not None
        else get_project_root() / DEFAULT_CONFIG_REL_PATH
    )
    if not target_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {target_path}")

    with target_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    if not isinstance(config, dict):
        raise ValueError(f"Expected mapping in config file {target_path}, got {type(config).__name__}")
    return config


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create or retrieve a formatted console logger without duplicate handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
    logger.propagate = False
    return logger
