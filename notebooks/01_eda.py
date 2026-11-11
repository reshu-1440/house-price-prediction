"""Standalone EDA runner generating statistical reports and diagnostic figures."""

from __future__ import annotations

from src.data.eda import run_eda
from src.data.load_data import load_raw_data
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def main() -> None:
    """Load the raw dataset and execute the complete EDA pipeline."""
    config = load_config()
    df = load_raw_data()

    reports_dir = resolve_path(config["paths"]["reports_dir"])
    figures_dir = resolve_path(config["paths"]["figures_dir"])

    results = run_eda(df=df, reports_dir=reports_dir, figures_dir=figures_dir)
    logger.info("EDA completed successfully. Markdown report: %s", results["markdown_report"])
    logger.info("Generated %d figures in %s", len(results["figures"]), figures_dir)


if __name__ == "__main__":
    main()
