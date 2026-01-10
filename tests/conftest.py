"""Pytest configuration and fixtures."""

import sys
import tempfile
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_kubectl_output():
    """Mock kubectl command output."""
    return {
        "contexts": "prod-cluster\nstaging-cluster\ndev-cluster",
        "namespaces": "default\nkube-system\nbackend\nfrontend",
        "api_resources": """pods
deployments
services
configmaps
secrets
ingresses""",
        "get_pods": """apiVersion: v1
kind: PodList
items:
- apiVersion: v1
  kind: Pod
  metadata:
    name: test-pod
    namespace: backend
  spec:
    containers:
    - name: nginx
      image: nginx:1.21
- apiVersion: v1
  kind: Pod
  metadata:
    name: another-pod
    namespace: backend
  spec:
    containers:
    - name: redis
      image: redis:6.2
""",
    }


@pytest.fixture
def sample_pod_yaml():
    """Sample Pod YAML for testing."""
    return """apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: backend
  labels:
    app: myapp
  uid: "12345678-1234-1234-1234-123456789abc"
  resourceVersion: "123456"
  creationTimestamp: "2024-01-01T00:00:00Z"
  managedFields:
  - manager: kubectl
    operation: Update
spec:
  containers:
  - name: nginx
    image: nginx:1.21
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "200m"
status:
  phase: Running
"""


@pytest.fixture
def sample_deployment_yaml():
    """Sample Deployment YAML for testing."""
    return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
  namespace: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
"""


@pytest.fixture
def sample_configmap_yaml():
    """Sample ConfigMap YAML for testing."""
    return """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
  namespace: backend
data:
  config.yaml: |
    key: value
  database-url: "postgresql://localhost/mydb"
"""


@pytest.fixture
def sample_secret_yaml():
    """Sample Secret YAML for testing."""
    return """apiVersion: v1
kind: Secret
metadata:
  name: test-secret
  namespace: backend
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
  api-key: YXBpLWtleS12YWx1ZQ==
"""
