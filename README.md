[English](README.md) | [简体中文](README.zh.md)

# Kube Audit Kit

> **Kube Audit Kit** is a [Claude Code Skill](https://code.claude.com/docs/en/skills) for non-intrusive security audits of Kubernetes clusters.

Kube Audit Kit exports all resources in a specified Context/Namespace, deeply sanitizes them, groups applications intelligently, and generates a comprehensive security audit report based on the following industry standards:

- [Pod Security Standards (PSS)](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [NSA Kubernetes Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

---

## Features

- **Non-intrusive**: Only `get/list` operations, **no changes** to cluster state
- **Full coverage**: Dynamically discovers all namespaced resource types, with a small exclude list for low-value resources (e.g., events, bindings)
- **Smart grouping**: Associates application resources based on workload topology
- **Dual audit**: Scripted static scan + AI expert deep analysis
- **Type safety**: Full Python type annotations
- **Nice output**: Rich-powered colored console output

## Security Coverage

### 🛡️ Pod Security (Based on PSS/NSA)

Based on [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) and [NSA Kubernetes Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)

| Check Item        | Description                                   |
| :---------------- | :-------------------------------------------- |
| Privileged Mode   | Detect `privileged: true`                     |
| Host Namespaces   | Detect `hostNetwork`, `hostPID`, `hostIPC`    |
| Capabilities      | Detect dangerous capabilities add/drop        |
| Security Context  | Detect `runAsNonRoot`, `readOnlyRootFilesystem` |
| Resource Limits   | Detect CPU/memory requests and limits         |
| Health Checks     | Detect liveness/readiness/startup probes      |
| Image Safety      | Detect `:latest` tag usage                    |

### 🔐 RBAC Audit

Based on [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes) and [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

| Check Item     | Description                                |
| :------------- | :----------------------------------------- |
| Wildcards      | Detect `*` in verbs/resources/apiGroups    |
| High Privilege | Detect cluster-admin/admin/edit/view roles |
| Over-privilege | Analyze Role/ClusterRole rule scope        |

### 🌐 Network Security Audit

Based on [NSA Network Policy Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/) and [CIS NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

| Check Item        | Description                                 |
| :--------------- | :------------------------------------------ |
| NetworkPolicy    | Detect namespace network policy protection  |
| Service Exposure | Detect LoadBalancer/NodePort/externalIPs    |
| Ingress Config   | Detect TLS configuration and exposed hosts  |

### 💾 HostPath Mount Detection

Based on [CIS Kubernetes Benchmark 5.2.3](https://www.cisecurity.org/benchmark/kubernetes) and [NSA Guidelines Section 3.3](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)

| Check Item    | Description                                         |
| :------------ | :-------------------------------------------------- |
| hostPath      | Detect host path mounts                             |
| Dangerous Path| Identify docker.sock, /etc, /root, etc.             |
| Risk Levels   | Rate by Critical/Warning                            |

### 🛡️ Security Policy Checks

Based on [Kubernetes seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/) and [AppArmor Documentation](https://kubernetes.io/docs/tutorials/clusters/apparmor/)

| Check Item | Description                          |
| :-------- | :----------------------------------- |
| seccomp   | Detect seccompProfile configuration  |
| AppArmor  | Detect AppArmor annotation settings  |

### 🔄 High Availability Configuration

Based on [Kubernetes PodDisruptionBudget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) and [CIS Benchmark 5.2.9](https://www.cisecurity.org/benchmark/kubernetes)

| Check Item            | Description                               |
| :------------------- | :---------------------------------------- |
| PodDisruptionBudget  | Detect PDB configuration                  |
| Secret Type          | Detect whether Secret type is appropriate |
| ServiceAccount       | Detect automountServiceAccountToken       |

### 🔍 Sensitive Data Scan

Based on [NSA Guidelines Section 4.2](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/) and [CIS Benchmark Secret Management](https://www.cisecurity.org/benchmark/kubernetes)

| Check Item        | Description                               |
| :---------------- | :---------------------------------------- |
| ConfigMap Scan    | Detect sensitive keywords and high entropy strings |
| Secret Analysis   | Detect non-sensitive data stored in Secret |
| Usage Distinction | Distinguish Volume mounts vs EnvVar refs  |

---

## Installation

### Option 1: Install as a Personal Skill (Recommended)

Install the skill to your personal directory so it is available in all projects:

```bash
git clone https://github.com/crazygit/kube-audit-kit.git ~/.claude/skills/kube-audit-kit
```

### Option 2: Install as a Project Skill

Install the skill in a specific project so it is only available there:

```bash
git clone https://github.com/crazygit/kube-audit-kit.git .claude/skills/kube-audit-kit
```

### After Installation

Verify the skill is loaded using either method:

**Option 1: Use /skills**

```
/skills
```

**Option 2: Ask Claude**

```
What Skills are available?
```

If `kube-audit-kit` appears in the list, the skill is loaded.

> **Note**: The latest Claude Code client supports auto hot-reload, so restart is usually unnecessary. If the skill is missing, try restarting Claude Code.

---

## Usage

A restart is usually unnecessary after installation. If it does not take effect, restart Claude Code.

### Trigger the Skill

Based on SKILL.md, you can trigger the skill with prompts like:

```
"Audit production prod-cluster namespace backend"
"Check payment service in staging cluster staging-cluster"
"Analyze all apps in dev cluster dev-cluster"
```

Or use more general phrasing:

```
"Please audit the my-namespace namespace in my-context"
"Help me audit cluster-1"
```

Claude will detect your intent, use the `kube-audit-kit` skill, and ask for Context and Namespace.

### Full Workflow

The skill executes the following steps:

1. **Export resources** - Use `kubectl get/list` to export all resource types
2. **Sanitize resources** - Remove status fields and noisy metadata
3. **Group apps** - Associate resources based on workload topology
4. **Security audit** - Static analysis + AI deep analysis to generate reports

### Requirements

| Component | Version Requirement          |
| :-------- | :--------------------------- |
| Python    | >= 3.14                      |
| kubectl   | Any version (configured cluster) |
| uv        | Latest (dependency management) |

### Run Scripts Manually

If you want to run scripts without the skill:

```bash
# Install dependencies
uv sync

# Run the audit pipeline
CTX=your-context
NS=your-namespace

uv run python scripts/export.py --context $CTX --namespace $NS
uv run python scripts/sanitize.py --context $CTX --namespace $NS
uv run python scripts/group_apps.py --context $CTX --namespace $NS
uv run python scripts/audit.py --context $CTX --namespace $NS
```

---

## Security Recommendations

### 🔐 Use a Dedicated Audit Account

Create a dedicated service account with strict RBAC controls. If you are concerned about exposing Secret data during the audit, you can omit Secret permissions; other checks will still work normally.

An example audit service account is provided:

```bash
# View example configuration
cat examples/audit-service-account.yaml

# Apply to target namespace (edit Namespace first)
kubectl apply -f examples/audit-service-account.yaml

# Get an audit token (valid for 1 hour)
kubectl -n <namespace> create token audit-service-account --duration=1h

# Configure kubeconfig for the audit context
kubectl config set-credentials audit-service-account --token=<token>
kubectl config set-context audit-context \
  --cluster=<your-cluster> \
  --user=audit-service-account \
  --namespace=<target-namespace>
```

**Permission Notes**:

| Permission                     | Required | Description                      |
| :----------------------------- | :------- | :------------------------------- |
| Pod/Deployment/Workload        | ✅ Yes   | Workload security checks         |
| ConfigMap                      | ✅ Yes   | Sensitive data scan              |
| Service/Ingress/NetworkPolicy  | ✅ Yes   | Network security audit           |
| RBAC Resources                 | ✅ Yes   | RBAC permission audit            |
| **Secret**                     | ⚪ Optional | If not granted, Secret checks are skipped |

**Impact without Secret permissions**:

- ❌ Secret type checks unavailable
- ❌ Cannot detect non-sensitive data stored in Secret
- ✅ All other checks still work (Pod Security, RBAC, network, hostPath, etc.)

**Security Best Practices**:

- ✅ Least privilege - grant only what is needed for auditing
- ✅ Secret optional - decide based on policy
- ✅ Namespace isolation - use Role scoped to a namespace
- ✅ Regular rotation - rotate service account tokens regularly
- ✅ Audit logs - enable Kubernetes audit logs

---

## Documentation Structure

```
kube-audit-kit/
├── SKILL.md                      # Skill entry point (metadata and instructions)
├── README.md                     # English documentation
├── README.zh.md                  # Chinese documentation
├── QUICKSTART.md                 # Quick start guide
├── SETUP.md                      # Environment setup
├── WORKFLOW.md                   # End-to-end workflow details
├── EXAMPLES.md                   # Usage examples
├── audit_report_template.md      # Report template
├── pyproject.toml                # Python project config
├── uv.lock                       # Dependency lockfile (uv)
├── examples/
│   └── audit-service-account.yaml # Audit service account RBAC example
├── scripts/
│   ├── export.py                 # Export Kubernetes resources
│   ├── sanitize.py               # Sanitize YAML files
│   ├── group_apps.py             # Smart application grouping
│   ├── audit.py                  # Security audit
│   ├── output.py                 # Output helpers
│   └── utils.py                  # Utilities
└── tests/                        # Tests
```

---

## Outputs

After the audit completes, reports are stored in **your current working directory** at `output/{context}/{namespace}/audit/`:

```
output/{context}/{namespace}/audit/
├── audit_results.json           # Structured audit results (all checks)
├── configmap_to_secret.csv      # ConfigMap sensitive data findings
├── secret_to_configmap.csv      # Secret non-sensitive data findings
├── rbac_issues.csv              # RBAC audit results
├── network_security.csv         # Network security results
├── hostpath_mounts.csv          # HostPath mount findings
├── security_policies.csv        # seccomp/AppArmor checks
├── pdb_and_secrets.csv          # PDB/Secret/ServiceAccount checks
└── audit_report.md              # Full audit report (AI-generated)
```

> **Note**: The output directory is created in **your working directory** when you invoke the skill, not in the skill installation directory. This is controlled by the `KUBE_AUDIT_OUTPUT` environment variable set in SKILL.md.

---

## FAQ

### Skill not triggering?

Make sure your prompt matches the keywords. Try more explicit phrasing:

```
"Please audit Kubernetes resources"
"Help me audit the production namespace"
```

### Context or Namespace not found?

```bash
# List available contexts
kubectl config get-contexts

# List namespaces in the target context
kubectl get namespaces --context <your-context>
```

---

## Security Notice

> ⚠️ **Important**: The `output/` directory contains Secret data. Delete it securely after the audit.

```bash
# After audit, securely delete the output directory
rm -rf output/<context>/<namespace>
```

---

## License

MIT License

---

## Related Links

- [Claude Code Skills documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [GitHub repository](https://github.com/crazygit/kube-audit-kit)
