# Kube Audit Kit - Detailed Workflow

This document describes the full workflow and implementation details of Kube Audit Kit.

## Workflow Overview

When a user initiates an audit request, the system executes the following four steps in order:

```
Export → Sanitize → Group → Audit
```

## Step 1: Dynamic Discovery and Full Export

**Script**: `scripts/export.py`

**Command format**:

```bash
# Set the output directory environment variable (ensure output goes to the user's working directory)
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/export.py --context <context> --namespace <namespace>
```

> **Important**: the `KUBE_AUDIT_OUTPUT` environment variable ensures output files are generated in the user's working directory rather than the SKILL installation directory. Every command must set this variable.

### Execution Flow

1. **Pre-check**: verify `kubectl` is available
2. **Dynamic discovery**: call `kubectl api-resources` to get all namespaced resources
3. **Exclude list filtering**: remove resources with no persistence value:
   - `events`, `endpoints`, `endpointslices`
   - `replicasets`, `controllerrevisions`
   - `*review` resources (tokenreviews, localsubjectaccessreviews, etc.)
   - `bindings`, `componentstatuses`, `events.events.k8s.io`
4. **Batch export**: run `kubectl get -o yaml` for each resource type
5. **Parse and save**: save each resource as an individual YAML file

### Output Structure

```
{OUTPUT_BASE}/export/
├── pods/
│   ├── pod-a.yaml
│   └── pod-b.yaml
├── deployments/
│   └── deployment-x.yaml
└── ... (other resource types)
```

### Fault Tolerance

- **Permission errors**: skip unauthorized resource types, warn but continue
- **Single resource failures**: log errors without aborting the overall export

## Step 2: Deep Resource Sanitization

**Script**: `scripts/sanitize.py`

**Command format**:

```bash
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/sanitize.py --context <context> --namespace <namespace>
```

### Sanitization Rules

Recursively remove the following fields:

1. **status**: root-level `status` field
2. **metadata**:
   - `uid`, `resourceVersion`, `creationTimestamp`, `generation`
   - `managedFields`, `ownerReferences`, `selfLink`
3. **annotations**:
   - `kubectl.kubernetes.io/last-applied-configuration`
   - `deployment.kubernetes.io/revision`

### Output Structure

```
{OUTPUT_BASE}/
├── sanitize/           # sanitized YAML
│   ├── pods/
│   └── deployments/
└── sanitize_fields/    # sanitization records
    ├── pods/
    └── deployments/
```

## Step 3: Intelligent Application Grouping

**Script**: `scripts/group_apps.py`

**Command format**:

```bash
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/group_apps.py --context <context> --namespace <namespace>
```

### Grouping Logic

1. **Anchor resources**: Deployment, StatefulSet, DaemonSet, CronJob, Job
2. **Association rules**:
   - **Service**: match via label selector
   - **Pod/PodMetrics**: match via labels
   - **Ingress**: reference via Service name
   - **ConfigMap/Secret**: parse from Pod spec and mark usage type
     - `volumes` → mark as **"Volume"**
     - `env`/`envFrom` → mark as **"EnvVar"**
   - **PVC**: match via volume claim name
   - **ServiceAccount**: match via `serviceAccountName`
   - **RBAC**: associate via RoleBinding/ClusterRoleBinding
   - **HPA**: match via `scaleTargetRef`
   - **PDB**: match via selector

### Output Structure

```
{OUTPUT_BASE}/group/
├── app-1/                    # named by Workload
│   ├── Deployment_app-1.yaml
│   ├── Service_app-1-svc.yaml
│   ├── ConfigMap_*.yaml
│   ├── Secret_*.yaml
│   └── config_usage.json     # usage type record
└── ungrouped_resources.txt   # orphaned resources
```

## Step 4: Dual-Layer Security Audit

### Phase 1: Script-based Static Scan

**Script**: `scripts/audit.py`

**Command format**:

```bash
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/audit.py --context <context> --namespace <namespace>
```

### Scan Rules

**1. Sensitive data scan**

- **Skip logic**: skip ConfigMap/Secret when only used as Volume (treated as internal files)
- **Targets**: EnvVar references or orphaned resources
- **Keywords**: `password`, `token`, `secret`, `key`, `auth`, `access`, `credential`

**2. Workload security baseline**

| Level    | Check                   | Path                                     |
| -------- | ----------------------- | ---------------------------------------- |
| Critical | privileged              | `securityContext.privileged`             |
| Critical | capabilities.add        | `securityContext.capabilities.add`       |
| Critical | hostNetwork             | `hostNetwork`                            |
| Critical | hostPID                 | `hostPID`                                |
| Critical | hostIPC                 | `hostIPC`                                |
| Warning  | capabilities.drop       | `securityContext.capabilities.drop`      |
| Warning  | runAsNonRoot            | `securityContext.runAsNonRoot`           |
| Warning  | readOnlyRootFilesystem  | `securityContext.readOnlyRootFilesystem` |
| Info     | resources               | `resources.requests/limits`              |
| Info     | probes                  | `livenessProbe/readinessProbe`           |
| Info     | image tag               | `image` (checks latest)                  |

### Output Structure

```
{OUTPUT_BASE}/audit/
├── audit_results.json           # structured audit results
├── configmap_to_secret.csv      # ConfigMap sensitive data
├── secret_to_configmap.csv      # Secret non-sensitive data
├── rbac_issues.csv              # RBAC audit results
├── network_security.csv         # network security audit results
├── hostpath_mounts.csv          # hostPath mount findings
├── security_policies.csv        # seccomp/AppArmor results
└── pdb_and_secrets.csv          # PDB/Secret/ServiceAccount results
```

### Phase 2: AI Expert Deep Review

**Review principle**: AI **independently reviews** the original YAML files without relying on phase 1 results.

**Execution flow**:

1. **Independent analysis**: traverse each application directory and read all YAML files
2. **Deep review**: identify risks not covered by scripts (business logic, architecture, configuration drift)
3. **Supplement findings**: if the script missed sensitive data, append to the CSV files
4. **Report summary**: combine phase 1 (script findings) with phase 2 (AI analysis) into the final report

**Output file**: `{OUTPUT_BASE}/audit/audit_report.md`

## Full Execution Example

```bash
# 1. Environment setup
uv sync

# 2. Export resources
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/export.py --context prod-cluster --namespace backend

# 3. Sanitize resources
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/sanitize.py --context prod-cluster --namespace backend

# 4. Group applications
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/group_apps.py --context prod-cluster --namespace backend

# 5. Static audit
export KUBE_AUDIT_OUTPUT="$(pwd)/output" && \
uv run python scripts/audit.py --context prod-cluster --namespace backend

# 6. AI deep analysis (performed by the Agent)
# The Agent reads YAML and audit results to produce the final report
```

> **Note**: every command must set the `KUBE_AUDIT_OUTPUT` environment variable to ensure output goes to the current working directory.

## Console Output Conventions

### Planning Phase

```
Received. Target: Context `{ctx}`, Namespace `{ns}`.

Execution plan:
1. Set the output directory environment variable: export KUBE_AUDIT_OUTPUT="$(pwd)/output"
2. [Export] Dynamic discovery and full resource export → scripts/export.py
3. [Sanitize] Remove metadata and status fields → scripts/sanitize.py
4. [Group] Associate applications by workload topology → scripts/group_apps.py
5. [Audit] Dual-layer security audit (static scan + AI expert review) → scripts/audit.py

Output directory: $(pwd)/output/{ctx}/{ns}/

Start?
```

### Execution Phase

```
✅ [Export completed] Scanned 32 resource types, exported 150 YAMLs
   Output: output/{ctx}/{ns}/export/

✅ [Sanitize completed] Sanitized 150 files, records saved
   Output: output/{ctx}/{ns}/sanitize/, output/{ctx}/{ns}/sanitize_fields/

✅ [Group completed] Identified 12 apps, generated reference map, 5 orphan resources
   Output: output/{ctx}/{ns}/group/, output/{ctx}/{ns}/ungrouped_resources.txt

✅ [Audit phase 1 completed] Script-based static scan finished
   Output: output/{ctx}/{ns}/audit/audit_results.json
```

### Results Phase

```
✅ [Audit completed] Static report and AI expert analysis merged

📊 Audit stats:
- Applications: 12
- Critical risks: X
- Warning risks: Y
- Info recommendations: Z

📁 Output directory: output/{ctx}/{ns}/
📄 Full audit report: output/{ctx}/{ns}/audit/audit_report.md

⚠️ Security reminder: the output/ directory contains decrypted Secret data. Please delete it securely after the audit!
```
