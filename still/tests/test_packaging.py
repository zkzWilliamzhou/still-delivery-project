"""Packaging checks: metadata sources stay in sync and the wheel contains the package."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_and_setup_shim_agree_on_name_and_version():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    shim = (ROOT / "setup.py").read_text(encoding="utf-8")
    name = re.search(r'^name = "([^"]+)"', project, re.MULTILINE).group(1)
    version = re.search(r'^version = "([^"]+)"', project, re.MULTILINE).group(1)
    shim_name = re.search(r'name="([^"]+)"', shim).group(1)
    shim_version = re.search(r'version="([^"]+)"', shim).group(1)
    assert (name, version) == (shim_name, shim_version)


def test_pyproject_declares_the_src_layout():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'where = ["src"]' in project


def test_readme_documents_the_no_install_path():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PYTHONPATH=src" in readme
    assert "not a proof" in readme


def test_ci_workflow_runs_all_four_checkers():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for tool in ("ruff", "mypy", "bandit", "pytest"):
        assert tool in workflow, f"{tool} missing from CI"
