"""Tests for sanitize module."""

import sanitize


class TestCleanMetadataDict:
    """Tests for clean_metadata_dict function."""

    def test_removes_standard_fields(self):
        """Test that standard metadata fields are removed."""
        metadata = {
            "name": "test-pod",
            "uid": "12345678-1234-1234-1234-123456789abc",
            "resourceVersion": "123456",
            "creationTimestamp": "2024-01-01T00:00:00Z",
            "generation": "1",
        }

        removed = sanitize.clean_metadata_dict(metadata, "metadata")

        assert "name" in metadata
        assert "uid" not in metadata
        assert "resourceVersion" not in metadata
        assert "creationTimestamp" not in metadata
        assert "generation" not in metadata
        assert len(removed) == 4

    def test_removes_managed_fields(self):
        """Test that managedFields is removed."""
        metadata = {
            "name": "test-pod",
            "managedFields": [{"manager": "kubectl"}],
        }

        removed = sanitize.clean_metadata_dict(metadata, "metadata")

        assert "managedFields" not in metadata
        assert len(removed) == 1

    def test_removes_specific_annotations(self):
        """Test that specific annotations are removed."""
        metadata = {
            "name": "test-pod",
            "annotations": {
                "kubectl.kubernetes.io/last-applied-configuration": "{}",
                "deployment.kubernetes.io/revision": "1",
                "custom-annotation": "value",
            },
        }

        removed = sanitize.clean_metadata_dict(metadata, "metadata")

        assert "annotations" in metadata
        assert (
            "kubectl.kubernetes.io/last-applied-configuration"
            not in metadata["annotations"]
        )
        assert "deployment.kubernetes.io/revision" not in metadata["annotations"]
        assert "custom-annotation" in metadata["annotations"]
        assert len(removed) == 2

    def test_removes_empty_annotations(self):
        """Test that annotations dict is removed if empty."""
        metadata = {
            "name": "test-pod",
            "annotations": {
                "kubectl.kubernetes.io/last-applied-configuration": "{}",
            },
        }

        removed = sanitize.clean_metadata_dict(metadata, "metadata")

        assert "annotations" not in metadata
        assert len(removed) == 1


class TestRecursiveSanitize:
    """Tests for recursive_sanitize function."""

    def test_sanitizes_root_metadata(self):
        """Test that root-level metadata is sanitized."""
        data = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "test",
                "uid": "12345",
            },
        }

        removed = sanitize.recursive_sanitize(data)

        assert "metadata" in data
        assert "uid" not in data["metadata"]
        assert len(removed) == 1

    def test_sanitizes_nested_metadata(self):
        """Test that nested metadata is sanitized."""
        data = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "template": {
                    "metadata": {
                        "name": "test",
                        "uid": "12345",
                    },
                },
            },
        }

        removed = sanitize.recursive_sanitize(data)

        assert "uid" not in data["spec"]["template"]["metadata"]
        assert len(removed) == 1


class TestSanitizeResource:
    """Tests for sanitize_resource function."""

    def test_removes_status(self):
        """Test that status is removed."""
        data = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test"},
            "spec": {},
            "status": {"phase": "Running"},
        }

        sanitized, removed = sanitize.sanitize_resource(data)

        assert "status" not in sanitized
        assert len(removed) == 1

    def test_removes_nested_status(self):
        """Test that nested status is preserved (only root status is removed)."""
        data = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test"},
            "spec": {},
            "status": {"phase": "Running"},
        }

        sanitized, removed = sanitize.sanitize_resource(data)

        assert "status" not in sanitized
        assert any("status" in r for r in removed)

    def test_preserves_important_fields(self):
        """Test that important fields are preserved."""
        data = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test", "namespace": "default"},
            "spec": {"containers": [{"name": "nginx", "image": "nginx:1.21"}]},
        }

        sanitized, _ = sanitize.sanitize_resource(data)

        assert sanitized["apiVersion"] == "v1"
        assert sanitized["kind"] == "Pod"
        assert sanitized["metadata"]["name"] == "test"
        assert sanitized["metadata"]["namespace"] == "default"
        assert len(sanitized["spec"]["containers"]) == 1
