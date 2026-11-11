"""Package setup for House Price Prediction."""

from setuptools import find_packages, setup

setup(
    name="house-price-prediction",
    version="0.1.0",
    description="End-to-end Indian residential property price prediction pipeline",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=2.0.0",
        "pandas>=2.2.0",
        "PyYAML>=6.0.0",
        "requests>=2.31.0",
        "matplotlib>=3.9.0",
        "seaborn>=0.13.0",
        "scipy>=1.14.0",
        "scikit-learn>=1.6.0",
        "joblib>=1.4.0",
        "xgboost>=2.1.0",
        "lightgbm>=4.5.0",
        "optuna>=4.0.0",
        "mlflow>=3.0.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.32.0",
        "pydantic>=2.9.0",
    ],
)
