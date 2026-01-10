# Kube Audit Kit - Environment Setup

This document describes the environment preparation needed before using Kube Audit Kit.

## Dependency Management

This project uses **uv** for Python dependency and virtual environment management.

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# or use pip
pip install uv
```

### Install project dependencies

```bash
# Run in the project root
uv sync

# Activate the virtual environment (optional, uv handles this automatically)
source .venv/bin/activate
```

### Verify the environment

```bash
# Check the Python version
python --version  # should be >=3.14

# Check dependencies
uv pip list
```

## Dependency Notes

Core dependencies:

- **pyyaml**: YAML file parsing
- **rich**: terminal output styling
- **kubectl**: Kubernetes CLI (system dependency)

## Kubernetes Permission Requirements

### Recommended setup: dedicated audit service account

Using a dedicated audit account follows the least-privilege principle. See `examples/audit-service-account.yaml`:

- Default uses `Role/RoleBinding` to bind `audit-service-account`
- For cluster-wide RBAC audits, enable `ClusterRole/ClusterRoleBinding` per the comments in the example file

### Apply the audit account configuration

```bash
kubectl apply -f examples/audit-service-account.yaml

# Get the audit token
kubectl -n <namespace> create token audit-service-account --duration=1h

# Configure kubectl context to use this token
kubectl config set-credentials audit-service-account --token=<token>
kubectl config set-context audit-context --cluster=<cluster> --user=audit-service-account
```

### Behavior when permissions are insufficient

If the audit account lacks permission for a resource type (such as Secret):

- ⚠️ Skip exporting that resource type (show a friendly warning)
- ✅ Other resources are exported and audited normally
- ❌ The final report lacks results for that resource type

## kubectl Configuration

### Verify kubectl availability

```bash
kubectl version --client
```

### List available Contexts

```bash
kubectl config get-contexts
```

### Switch Context

```bash
kubectl config use-context <context-name>
```

## Path Conventions

All output paths are computed by `get_output_paths()` in `scripts/utils.py`.

**Base output directory**:

```
{OUTPUT_BASE} = output/{context}/{namespace}
```

**Full directory structure**:

```
output/
└── {context}/
    └── {namespace}/
        ├── export/              # raw export data
        ├── sanitize/            # sanitized data
        ├── sanitize_fields/     # sanitization records
        ├── group/               # application grouping
        │   ├── app-1/
        │   └── app-2/
        ├── ungrouped_resources.txt
        └── audit/               # audit results
            ├── audit_results.json
            ├── configmap_to_secret.csv
            ├── secret_to_configmap.csv
            ├── rbac_issues.csv
            ├── network_security.csv
            ├── hostpath_mounts.csv
            ├── security_policies.csv
            ├── pdb_and_secrets.csv
            └── audit_report.md
```

## How to Run Scripts

### Recommended: use uv run

```bash
uv run python scripts/export.py --context <ctx> --namespace <ns>
```

### Or within the activated virtual environment

```bash
source .venv/bin/activate
python scripts/export.py --context <ctx> --namespace <ns>
```

## Security Notes

**Important**: the `output/` directory contains decrypted Secret data.

**After the audit**:

- ✅ You may keep the audit report (it does not contain sensitive data)
- ⚠️ Other directories should be securely deleted or encrypted
- ❌ Do not commit `output/` to version control

**Suggested cleanup commands**:

```bash
# Clean up sensitive data after the audit
rm -rf output/<context>/<namespace>/export
rm -rf output/<context>/<namespace>/sanitize
rm -rf output/<context>/<namespace>/group
```

Keep the final audit report:

```bash
# Keep only the report
mv output/<context>/<namespace>/audit/audit_report.md .
rm -rf output/<context>/<namespace>
```
