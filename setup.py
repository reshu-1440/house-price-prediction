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
    ],
)
