"""Compatibility shim for build environments with setuptools older than 61.

`pyproject.toml` is the canonical metadata source. Some system Pythons ship a
setuptools too old to read PEP 621 tables, which yields an UNKNOWN-0.0.0 wheel.
This shim keeps `pip install .` working there. `tests/test_packaging.py` checks
that the duplicated name and version stay in sync with pyproject.toml.
"""

from setuptools import find_packages, setup

setup(
    name="still-check",
    version="0.1.0",
    description="Bounded, machine-checkable evidence about what a refactor changed",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={"console_scripts": ["still = still.cli:main"]},
)
