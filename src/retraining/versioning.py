"""Semantic model versioning and rollback management."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from src.utils.config import get_logger

logger = get_logger(__name__)


def _parse_semver(version: str) -> tuple[int, int, int]:
    cleaned = version.strip().lstrip("v")
    parts = cleaned.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid semantic version '{version}'. Expected 'X.Y.Z'.")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_semver(current_version: str | None, bump: str = "minor") -> str:
    """Increment a semantic version string (``major``, ``minor``, or ``patch``)."""
    if not current_version:
        return "0.1.0"
    major, minor, patch = _parse_semver(current_version)
    kind = bump.strip().lower()
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump level '{bump}'. Choose major, minor, or patch.")


def _load_registry(versions_dir: Path) -> dict[str, Any]:
    reg_path = versions_dir / "registry.json"
    if reg_path.exists():
        return json.loads(reg_path.read_text(encoding="utf-8"))
    return {"active_version": None, "versions": []}


def _save_registry(versions_dir: Path, registry: dict[str, Any]) -> None:
    versions_dir.mkdir(parents=True, exist_ok=True)
    reg_path = versions_dir / "registry.json"
    reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def list_model_versions(versions_dir: Path) -> list[dict[str, Any]]:
    """Return recorded semantic model versions ordered oldest to newest."""
    registry = _load_registry(versions_dir)
    entries = list(registry.get("versions", []))
    return sorted(entries, key=lambda item: _parse_semver(item["version"]))


def version_model(
    pipeline: Any,
    metadata: dict[str, Any],
    versions_dir: Path,
    bump: str = "minor",
    explicit_version: str | None = None,
) -> dict[str, Any]:
    """Persist an immutable semantic-versioned snapshot under ``versions_dir/vX.Y.Z``."""
    versions_dir.mkdir(parents=True, exist_ok=True)
    registry = _load_registry(versions_dir)
    existing = list_model_versions(versions_dir)
    latest_ver = existing[-1]["version"] if existing else None

    new_version = (
        explicit_version.lstrip("v")
        if explicit_version is not None
        else (
            "0.1.0"
            if latest_ver is None and metadata.get("model_version") in (None, "0.1.0")
            else bump_semver(latest_ver or str(metadata.get("model_version", "0.1.0")), bump=bump)
        )
    )

    version_dir = versions_dir / f"v{new_version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    model_file = version_dir / "pipeline.joblib"
    meta_file = version_dir / "metadata.json"

    enriched_meta = {
        **metadata,
        "model_version": new_version,
        "versioned_at_utc": datetime.now(UTC).isoformat(),
    }
    joblib.dump(pipeline, model_file, compress=3)
    meta_file.write_text(json.dumps(enriched_meta, indent=2), encoding="utf-8")

    entry = {
        "version": new_version,
        "path": str(model_file),
        "metadata_path": str(meta_file),
        "created_at_utc": enriched_meta["versioned_at_utc"],
        "metrics": enriched_meta.get("metrics", {}),
    }
    versions_list = [v for v in registry.get("versions", []) if v.get("version") != new_version]
    versions_list.append(entry)
    registry["versions"] = versions_list
    registry["active_version"] = new_version
    _save_registry(versions_dir, registry)

    logger.info("Saved model version v%s to %s", new_version, version_dir)
    return entry


def rollback_model(
    target_version: str,
    versions_dir: Path,
    production_path: Path,
) -> dict[str, Any]:
    """Restore a previously versioned model snapshot to ``production_path`` atomically."""
    clean_ver = target_version.strip().lstrip("v")
    version_dir = versions_dir / f"v{clean_ver}"
    src_model = version_dir / "pipeline.joblib"
    src_meta = version_dir / "metadata.json"

    if not src_model.exists():
        raise FileNotFoundError(f"Model version v{clean_ver} not found at {src_model}")

    production_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_model = production_path.with_suffix(".joblib.tmp")
    shutil.copy2(src_model, tmp_model)
    os.replace(tmp_model, production_path)

    prod_meta_path = production_path.parent / "metadata.json"
    meta_payload: dict[str, Any] = {}
    if src_meta.exists():
        meta_payload = json.loads(src_meta.read_text(encoding="utf-8"))
        meta_payload["rolled_back_at_utc"] = datetime.now(UTC).isoformat()
        tmp_meta = prod_meta_path.with_suffix(".json.tmp")
        tmp_meta.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")
        os.replace(tmp_meta, prod_meta_path)

    registry = _load_registry(versions_dir)
    registry["active_version"] = clean_ver
    _save_registry(versions_dir, registry)

    logger.info("Rolled back production model to v%s (%s)", clean_ver, production_path)
    return {
        "active_version": clean_ver,
        "production_path": str(production_path),
        "metadata": meta_payload,
    }
