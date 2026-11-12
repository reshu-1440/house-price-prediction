"""Thread-safe model loading and FastAPI dependency helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import HTTPException, status

from src.pipeline.inference_pipeline import load_pipeline
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


class ModelRegistryState:
    """Singleton state holding the active serialized pipeline and sidecar metadata."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.pipeline: Any | None = None
        self.metadata: dict[str, Any] = {}
        self.model_path: Path | None = None

    def _resolve_model_path(self, explicit_path: str | Path | None = None) -> Path:
        if explicit_path is not None:
            return Path(explicit_path)
        env_path = os.getenv("MODEL_PATH")
        if env_path:
            return Path(env_path)
        cfg = load_config()
        models_dir = resolve_path(cfg["paths"].get("models_dir", "models"))
        return models_dir / "house_price_pipeline.joblib"

    def load(self, model_path: str | Path | None = None) -> bool:
        """Load pipeline and metadata from disk; returns True if successful."""
        target = self._resolve_model_path(model_path)
        with self._lock:
            if not target.exists():
                logger.warning("Model artifact not found at %s; API starting in degraded mode", target)
                self.pipeline = None
                self.metadata = {}
                self.model_path = target
                return False

            self.pipeline = load_pipeline(target)
            self.model_path = target
            meta_path = target.parent / "metadata.json"
            if meta_path.exists():
                self.metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            else:
                self.metadata = {"model_name": "lightgbm", "model_version": "0.1.0"}
            logger.info(
                "Loaded model artifact '%s' (version=%s)",
                self.metadata.get("model_name"),
                self.metadata.get("model_version"),
            )
            return True

    def set_model(self, pipeline: Any, metadata: dict[str, Any] | None = None) -> None:
        """Inject an in-memory pipeline (primarily for deterministic testing)."""
        with self._lock:
            self.pipeline = pipeline
            self.metadata = metadata or {"model_name": "test_model", "model_version": "0.0.1"}

    def clear(self) -> None:
        """Reset loaded model state."""
        with self._lock:
            self.pipeline = None
            self.metadata = {}


model_state = ModelRegistryState()


def get_model_state() -> ModelRegistryState:
    """FastAPI dependency returning active ``ModelRegistryState`` or raising 503."""
    if model_state.pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model artifact is not loaded. Run training pipeline before inference.",
        )
    return model_state
