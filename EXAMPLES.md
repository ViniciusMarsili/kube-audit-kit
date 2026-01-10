# Kube Audit Kit - Output Examples

This document shows typical outputs of Kube Audit Kit to help you understand the expected results.

## Directory Structure Example

```
output/prod-cluster/backend/
├── export/
│   ├── deployments/
│   │   ├── payment-api.yaml
│   │   └── frontend.yaml
│   ├── services/
│   │   ├── payment-api-svc.yaml
│   │   └── frontend-svc.yaml
│   ├── configmaps/
│   │   └── app-config.yaml
│   └── secrets/
│       └── db-credentials.yaml
├── sanitize/
│   └── [sanitized YAML, same structure as export]
├── sanitize_fields/
│   ├── deployments/
│   │   └── payment-api.txt
│   └── secrets/
│       └── db-credentials.txt
├── group/
│   ├── payment-api/
│   │   ├── Deployment_payment-api.yaml
│   │   ├── Service_payment-api-svc.yaml
│   │   ├── ConfigMap_app-config.yaml
│   │   ├── Secret_db-credentials.yaml
│   │   └── config_usage.json
│   └── frontend/
│       ├── Deployment_frontend.yaml
│       ├── Service_frontend-svc.yaml
│       └── config_usage.json
├── ungrouped_resources.txt
└── audit/
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

## Sanitization Record Example

### sanitize_fields/secrets/db-credentials.txt

```
metadata.uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
metadata.resourceVersion = "12345678"
metadata.creationTimestamp = "2024-01-15T10:30:00Z"
metadata.annotations.kubectl.kubernetes.io/last-applied-configuration = '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"db-credentials","namespace":"backend"},"type":"Opaque","data":{"password":"****","username":"****"}}'
```

## config_usage.json Example

```json
{
  "ConfigMap/app-config": ["EnvVar", "Volume"],
  "Secret/db-credentials": ["EnvVar"],
  "ConfigMap/nginx-conf": ["Volume"]
}
```

**Notes**:
- `["EnvVar"]` - used only as environment variables (sensitive data is scanned)
- `["Volume"]` - used only as volume mounts (not scanned, treated as config files)
- `["EnvVar", "Volume"]` - used in both ways (scanned)

## audit_results.json Example

```json
[
  {
    "AppName": "payment-api",
    "Critical": [
      "[Deployment/payment-api/container:api] privileged mode enabled (privileged: true)",
      "[Deployment/payment-api/container:api] added dangerous Capabilities: ['NET_ADMIN', 'SYS_ADMIN']"
    ],
    "Warning": [
      "[Deployment/payment-api/container:api] missing runAsNonRoot: true",
      "[Deployment/payment-api/container:api] missing readOnlyRootFilesystem: true",
      "[Deployment/payment-api/container:api] capabilities.drop is not [\"ALL\"]"
    ],
    "Info": [
      "[Deployment/payment-api/container:api] incomplete resource Limits/Requests",
      "[Deployment/payment-api/container:api] missing livenessProbe",
      "[Deployment/payment-api/container:api] missing readinessProbe",
      "[Deployment/payment-api/container:api] image uses latest tag"
    ]
  },
  {
    "AppName": "frontend",
    "Critical": [],
    "Warning": [
      "[Deployment/frontend/container:nginx] missing runAsNonRoot: true"
    ],
    "Info": [
      "[Deployment/frontend/container:nginx] missing livenessProbe"
    ]
  }
]
```

## CSV File Examples

### configmap_to_secret.csv

Potential sensitive data found in ConfigMaps:

```csv
AppName,ConfigMap,SensitiveKeys,Usage
payment-api,app-config,db-password,EnvVar
payment-api,app-config,api-secret-key,EnvVar
frontend,app-config,admin-token,EnvVar
```

### secret_to_configmap.csv

Potential non-sensitive data found in Secrets (consider moving to ConfigMaps):

```csv
AppName,Secret,NonSensitiveKeys
payment-api,app-secret,"nginx-conf;log-level"
frontend,theme-config,"css-vars;font-settings"
```

## ungrouped_resources.txt Example

Orphan resources that could not be associated with any application:

```
ConfigMap/global-config
Secret/global-certificates
NetworkPolicy/default-deny
IngressController/nginx-ingress-controller
```

## audit_report.md Structure Example

```markdown
# Kubernetes Security Audit Report

**Cluster**: prod-cluster
**Namespace**: backend
**Audit time**: 2024-01-15 10:30:00 UTC
**Audit scope**: 12 applications, 150 resources

---

## Execution Summary

### Application Stats
- **Total workloads**: 15 (Deployment: 10, StatefulSet: 3, DaemonSet: 2)
- **Total associated resources**: 150
- **Orphan resources**: 5

### Risk Stats
| Level | Count | Severity |
|------|------|----------|
| **Critical** | 8 | 🔴 High - fix immediately |
| **Warning** | 23 | 🟡 Warning - plan to fix |
| **Info** | 45 | 🔵 Recommendation - optimize |

### Sensitive Data Risks
- **Sensitive data found in ConfigMaps**: 3 (see `configmap_to_secret.csv`)
- **Potential non-sensitive data in Secrets**: 2 (see `secret_to_configmap.csv`)

---

## Detailed Audit Report

### 1. payment-api

**Resource type**: Deployment
**Pod replicas**: 3

#### Automated Scan Results

**🔴 Critical risks (2)**:
- `[container:api] privileged mode enabled (privileged: true)`
- `[container:api] added dangerous Capabilities: ['NET_ADMIN', 'SYS_ADMIN']`

**🟡 Warning risks (3)**:
- `[container:api] missing runAsNonRoot: true`
- `[container:api] missing readOnlyRootFilesystem: true`
- `[container:api] capabilities.drop is not ["ALL"]`

**🔵 Info recommendations (4)**:
- `[container:api] incomplete resource Limits/Requests`
- `[container:api] missing livenessProbe`
- `[container:api] missing readinessProbe`
- `[container:api] image uses latest tag`

#### RBAC Permission Audit

✅ Using dedicated ServiceAccount: `payment-api-sa`
⚠️ Bound to ClusterRole `cluster-admin` (excessive permissions)

#### Network Security Audit

✅ NetworkPolicy configured
⚠️ All egress traffic allowed

#### Host Mount Detection

✅ No hostPath mounts

#### Security Policy Checks

❌ seccomp profile not configured
❌ AppArmor profile not configured

#### High Availability Configuration

❌ PodDisruptionBudget not configured
✅ HPA configured (min: 3, max: 10)

#### AI Deep Analysis

**Business logic risks**:
- 🔴 Secret `db-credentials` injects database password via environment variables; consider using External Secrets Operator
- 🔴 ConfigMap `app-config` contains `api-secret-key` that may be a JWT secret, move to Secret

**Architecture risks**:
- 🟡 Service uses LoadBalancer; for internal environments, consider ClusterIP
- 🟡 Missing Pod anti-affinity; replicas may schedule on the same node

**Configuration drift risks**:
- 🔴 Image tag uses `latest`, risk of inconsistent versions and rollbacks
- 🟡 Resource limits not set, risk of resource exhaustion

---

## Comprehensive Remediation Plan

### P0 Priority (fix immediately)

1. **Remove privileged mode** - payment-api
   - Remove `privileged: true`
   - Remove `NET_ADMIN` and `SYS_ADMIN` capabilities

2. **Move sensitive config** - payment-api
   - Move sensitive data in ConfigMaps to Secrets
   - Consider External Secrets Operator

3. **Fix image tags** - all apps
   - Use semantic version tags instead of `latest`

### P1 Priority (fix this week)

1. **Configure security contexts** - all apps
   - Set `runAsNonRoot: true`
   - Set `readOnlyRootFilesystem: true`

2. **Configure health checks** - all apps
   - Add `livenessProbe`
   - Add `readinessProbe`

3. **Set resource limits** - all apps
   - Configure `resources.requests`
   - Configure `resources.limits`

### P2 Priority (planned improvements)

1. **Configure seccomp/AppArmor** - high-risk apps
2. **Optimize RBAC permissions** - remove cluster-admin binding
3. **Configure PodDisruptionBudget** - critical apps
4. **Add Pod anti-affinity** - multi-replica apps

---

## Appendix

### Related Files
- **Full audit results**: `audit_results.json`
- **Sensitive data list**: `configmap_to_secret.csv`
- **Config optimization suggestions**: `secret_to_configmap.csv`
- **Orphan resources**: `ungrouped_resources.txt`

### Audit Methodology
- **Static scan**: automated checks based on PSS/NSA standards
- **AI analysis**: deep analysis of business logic and architecture risks

### Reference Standards
- Pod Security Standards (PSS)
- NSA/CISA Kubernetes Hardening Guidance
- CIS Kubernetes Benchmark

---

**Audit tool**: [Kube Audit Kit](https://github.com/crazygit/kube-audit-kit)
**Audit version**: v1.0.0
```

## Typical Scenario Outputs

### Scenario 1: Healthy application

**audit_results.json**:
```json
{
  "AppName": "healthy-app",
  "Critical": [],
  "Warning": [],
  "Info": [
    "[Deployment/healthy-app/container:app] consider adding startupProbe"
  ]
}
```

**Conclusion**: ✅ Application configuration is good, only minor improvements needed

### Scenario 2: High-risk application

**audit_results.json**:
```json
{
  "AppName": "legacy-app",
  "Critical": [
    "[Deployment/legacy-app/container:main] privileged: true",
    "[Deployment/legacy-app/container:main] hostNetwork: true",
    "[Deployment/legacy-app/container:main] hostPID: true"
  ],
  "Warning": [
    "[Deployment/legacy-app/container:main] missing runAsNonRoot"
  ],
  "Info": []
}
```

**Conclusion**: 🔴 Severe security risk, disable and refactor immediately

### Scenario 3: Configuration confusion

**configmap_to_secret.csv**:
```csv
AppName,ConfigMap,SensitiveKeys,Usage
legacy-app,app-config,"password;api-key;secret-key",EnvVar
```

**secret_to_configmap.csv**:
```csv
AppName,Secret,NonSensitiveKeys
legacy-app,app-secret,"nginx-conf;log-level;debug-mode"
```

**Conclusion**: 🟡 ConfigMap/Secret usage is reversed and should be swapped

## Related Docs

- **Quick start**: [QUICKSTART.md](QUICKSTART.md)
- **Workflow**: [WORKFLOW.md](WORKFLOW.md)
