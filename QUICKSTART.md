# 30-Second Quick Start

This guide helps you complete a Kubernetes security audit in the shortest possible time.

## Pre-checks

```bash
# 1. Confirm Python version >= 3.14
python --version

# 2. Confirm kubectl is configured
kubectl config get-contexts

# 3. Confirm target Context and Namespace
kubectl config current-context
```

## Complete the audit in three steps

### Step 1: Install dependencies (first run)

```bash
uv sync
```

### Step 2: Run the audit workflow

```bash
# Replace <context> and <namespace> with your actual values
export CTX="your-cluster-context"
export NS="your-namespace"

# Set the output directory (important: ensure output goes to current working directory)
export KUBE_AUDIT_OUTPUT="$(pwd)/output"

# 1. Export resources
uv run python scripts/export.py --context $CTX --namespace $NS

# 2. Sanitize resources
uv run python scripts/sanitize.py --context $CTX --namespace $NS

# 3. Group applications
uv run python scripts/group_apps.py --context $CTX --namespace $NS

# 4. Static audit
uv run python scripts/audit.py --context $CTX --namespace $NS
```

### Step 3: View the report

```bash
# After AI deep analysis completes (performed by the Agent), view the final report
cat output/$CTX/$NS/audit/audit_report.md
```

**Done!** 🎉

## One-click script

Create a script `audit-k8s.sh`:

```bash
#!/bin/bash
CTX=${1:-"your-context"}
NS=${2:-"default"}

# Set output directory
export KUBE_AUDIT_OUTPUT="$(pwd)/output"

uv run python scripts/export.py --context $CTX --namespace $NS && \
uv run python scripts/sanitize.py --context $CTX --namespace $NS && \
uv run python scripts/group_apps.py --context $CTX --namespace $NS && \
uv run python scripts/audit.py --context $CTX --namespace $NS && \
echo "✅ Audit complete! Report path: output/$CTX/$NS/audit/audit_report.md"
```

Usage:

```bash
chmod +x audit-k8s.sh
./audit-k8s.sh prod-cluster backend
```

## Expected Output

```
✅ [Export completed] Scanned 32 resource types, exported 150 YAMLs
✅ [Sanitize completed] Sanitized 150 files
✅ [Group completed] Identified 12 applications
✅ [Audit phase 1 completed] Script-based static scan finished
✅ [Audit completed] Static report and AI expert analysis merged
```

## Post-audit Cleanup

```bash
# Keep the report, delete sensitive data
mv output/$CTX/$NS/audit/audit_report.md .
rm -rf output/$CTX/$NS
```

## Need help?

- **Detailed workflow**: [WORKFLOW.md](WORKFLOW.md)
- **Environment setup**: [SETUP.md](SETUP.md)
- **Output examples**: [EXAMPLES.md](EXAMPLES.md)
