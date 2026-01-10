"""Tests for utils module."""
from pathlib import Path

import utils


def test_get_output_paths():
    """Test that get_output_paths returns correct paths."""
    context = "test-cluster"
    namespace = "test-ns"

    paths = utils.get_output_paths(context, namespace)

    for key, path in paths.items():
        assert isinstance(path, Path), f"{key} should be a Path object"

    base = Path.cwd() / "output" / context / namespace

    assert paths["export"] == base / "export"
    assert paths["sanitize"] == base / "sanitize"
    assert paths["sanitize_fields"] == base / "sanitize_fields"
    assert paths["group"] == base / "group"

    assert paths["audit_dir"] == base / "audit"
    assert paths["audit"] == paths["audit_dir"] / "audit_report.md"
    assert paths["csv_cm_to_sec"] == paths["audit_dir"] / "configmap_to_secret.csv"
    assert paths["csv_sec_to_cm"] == paths["audit_dir"] / "secret_to_configmap.csv"

    assert paths["orphan"] == base / "ungrouped_resources.txt"


def test_get_output_paths_consistency():
    """Test that multiple calls with same args return same paths."""
    context = "my-cluster"
    namespace = "my-ns"

    paths1 = utils.get_output_paths(context, namespace)
    paths2 = utils.get_output_paths(context, namespace)

    for key in paths1.keys():
        assert paths1[key] == paths2[key], f"{key} path should be consistent"
