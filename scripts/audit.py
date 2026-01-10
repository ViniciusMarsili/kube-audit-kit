import os
import yaml
import json
import csv
import argparse
import sys
from typing import Dict, Any, List, Set

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import output

SENSITIVE_KEYWORDS = [
    "password",
    "token",
    "secret",
    "key",
    "auth",
    "access",
    "credential",
]
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}
RBAC_KINDS = {"Role", "ClusterRole", "RoleBinding", "ClusterRoleBinding"}
NETWORK_KINDS = {"NetworkPolicy", "Service", "Ingress"}
SEC_CONFIG_KINDS = {"PodDisruptionBudget", "ServiceAccount"}


class Auditor:
    def __init__(self, context: str, namespace: str) -> None:
        self.context = context
        self.namespace = namespace
        self.paths = utils.get_output_paths(context, namespace)
        self.group_dir = self.paths["group"]
        self.audit_report: List[Dict[str, Any]] = []
        self.cm_to_secret_rows: List[Dict[str, str]] = []
        self.secret_to_cm_rows: List[Dict[str, str]] = []
        self.global_config_usage: Dict[str, Set[str]] = {}

        self.rbac_issues: List[Dict[str, str]] = []
        self.network_findings: List[Dict[str, str]] = []
        self.hostpath_mounts: List[Dict[str, str]] = []
        self.security_policies: List[Dict[str, str]] = []
        self.pdb_and_secrets: List[Dict[str, str]] = []

    def run(self) -> None:
        if not self.group_dir.exists():
            output.error(f"Group directory {self.group_dir} does not exist.")
            return

        output.info(f"Starting security audit for {self.context}/{self.namespace}...")

        self.audit_configs()

        self.audit_workloads()

        self.audit_rbac()

        self.audit_network_security()

        self.audit_host_mounts()

        self.audit_security_policies()

        self.audit_pod_disruption_and_secrets()

        self.save_reports()

    def audit_configs(self) -> None:
        """Audit ConfigMap and Secret usage and contents."""
        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            usage_path = app_dir / "config_usage.json"
            if usage_path.exists():
                with open(usage_path, "r") as f:
                    usage = json.load(f)
                    for res_id, types in usage.items():
                        self.global_config_usage.setdefault(res_id, set()).update(types)

        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data:
                        continue

                    kind = data.get("kind")
                    name = data.get("metadata", {}).get("name")
                    res_id = f"{kind}/{name}"

                    if kind == "ConfigMap":
                        self.check_configmap(app_dir.name, name, data, res_id)
                    elif kind == "Secret":
                        self.check_secret(app_dir.name, name, data, res_id)

    def check_configmap(
        self, app_name: str, name: str, data: Dict[str, Any], res_id: str
    ) -> None:
        usage = self.global_config_usage.get(res_id, set())
        if usage == {"Volume"}:
            return

        found_sensitive = []
        content = data.get("data", {}) or {}
        for key, value in content.items():
            if any(kw in key.lower() for kw in SENSITIVE_KEYWORDS):
                found_sensitive.append(key)
            elif isinstance(value, str) and self.is_high_entropy(value):
                found_sensitive.append(f"{key} (high entropy)")

        if found_sensitive:
            self.cm_to_secret_rows.append(
                {
                    "AppName": app_name,
                    "ConfigMap": name,
                    "SensitiveKeys": ", ".join(found_sensitive),
                    "Usage": ", ".join(list(usage)) if usage else "Orphan",
                }
            )

    def check_secret(self, app_name: str, name: str, data: Dict[str, Any], res_id: str) -> None:
        content = data.get("data", {}) or {}
        non_sensitive_keys = []
        for key in content.keys():
            if not any(kw in key.lower() for kw in SENSITIVE_KEYWORDS):
                non_sensitive_keys.append(key)

        if len(non_sensitive_keys) > 0:
            self.secret_to_cm_rows.append(
                {
                    "AppName": app_name,
                    "Secret": name,
                    "NonSensitiveKeys": ", ".join(non_sensitive_keys),
                }
            )

    def is_high_entropy(self, text: str) -> bool:
        if len(text) < 20:
            return False
        has_upper = any(c.isupper() for c in text)
        has_lower = any(c.islower() for c in text)
        has_digit = any(c.isdigit() for c in text)
        return has_upper and has_lower and has_digit

    def audit_workloads(self) -> None:
        """Audit workload security configuration."""
        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            app_findings: Dict[str, Any] = {
                "AppName": app_dir.name,
                "Critical": [],
                "Warning": [],
                "Info": [],
            }

            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data or data.get("kind") not in WORKLOAD_KINDS:
                        continue

                    self.check_workload_security(data, app_findings)

            if (
                app_findings["Critical"]
                or app_findings["Warning"]
                or app_findings["Info"]
            ):
                self.audit_report.append(app_findings)

    def check_workload_security(
        self, data: Dict[str, Any], findings: Dict[str, List[str]]
    ) -> None:
        kind = data.get("kind")
        name = data.get("metadata", {}).get("name")
        spec = data.get("spec", {})

        if kind == "CronJob":
            pod_template = (
                spec.get("jobTemplate", {}).get("spec", {}).get("template", {})
            )
        else:
            pod_template = spec.get("template", {})

        pod_spec = pod_template.get("spec", {})
        containers = pod_spec.get("containers", []) + pod_spec.get("initContainers", [])

        for field in ["hostNetwork", "hostPID", "hostIPC"]:
            if pod_spec.get(field) is True:
                findings["Critical"].append(f"[{kind}/{name}] enabled {field}")

        for container in containers:
            c_name = container.get("name")
            sc = container.get("securityContext", {})

            if sc.get("privileged") is True:
                findings["Critical"].append(
                    f"[{kind}/{name}/container:{c_name}] privileged mode enabled (privileged: true)"
                )

            caps = sc.get("capabilities", {})
            if "add" in caps:
                findings["Critical"].append(
                    f"[{kind}/{name}/container:{c_name}] added dangerous Capabilities: {caps['add']}"
                )
            if caps.get("drop") != ["ALL"] and caps.get("drop") != ["all"]:
                findings["Warning"].append(
                    f"[{kind}/{name}/container:{c_name}] did not drop ALL capabilities"
                )

            if (
                pod_spec.get("securityContext", {}).get("runAsNonRoot") is not True
                and sc.get("runAsNonRoot") is not True
            ):
                findings["Warning"].append(
                    f"[{kind}/{name}/container:{c_name}] missing runAsNonRoot: true"
                )

            if sc.get("readOnlyRootFilesystem") is not True:
                findings["Warning"].append(
                    f"[{kind}/{name}/container:{c_name}] missing readOnlyRootFilesystem: true"
                )

            resources = container.get("resources", {})
            if not resources.get("limits") or not resources.get("requests"):
                findings["Info"].append(
                    f"[{kind}/{name}/container:{c_name}] incomplete resource Limits/Requests"
                )

            probes = ["livenessProbe", "readinessProbe", "startupProbe"]
            for p in probes:
                if p not in container:
                    findings["Info"].append(
                        f"[{kind}/{name}/container:{c_name}] missing {p}"
                    )

            image = container.get("image", "")
            if ":" not in image or image.endswith(":latest"):
                findings["Info"].append(
                    f"[{kind}/{name}/container:{c_name}] image tag not pinned ({image})"
                )

    def audit_rbac(self) -> None:
        """Audit RBAC permissions and check for over-privilege."""
        roles: Dict[str, Dict[str, Any]] = {}
        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data or data.get("kind") not in {"Role", "ClusterRole"}:
                        continue
                    name = data.get("metadata", {}).get("name")
                    kind = data.get("kind")
                    key = f"{kind}/{name}"
                    roles[key] = {
                        "app": app_dir.name,
                        "kind": kind,
                        "name": name,
                        "rules": data.get("rules", []),
                    }

        for key, role_info in roles.items():
            for rule in role_info["rules"]:
                verbs = rule.get("verbs", [])
                resources = rule.get("resources", [])
                api_groups = rule.get("apiGroups", [])
                non_resource_urls = rule.get("nonResourceURLs", [])

                issues = []

                if "*" in verbs:
                    issues.append("verbs include wildcard [*]")
                if "*" in resources:
                    issues.append("resources include wildcard [*]")
                if "*" in api_groups:
                    issues.append("apiGroups include wildcard [*]")
                if "*" in non_resource_urls:
                    issues.append("nonResourceURLs include wildcard [*]")

                if role_info["kind"] == "ClusterRole" and role_info["name"] in [
                    "cluster-admin",
                    "admin",
                    "edit",
                    "view",
                ]:
                    issues.append(f"uses high-privilege system role [{role_info['name']}]")

                if issues:
                    self.rbac_issues.append(
                        {
                            "AppName": role_info["app"],
                            "Kind": role_info["kind"],
                            "Name": role_info["name"],
                            "Issues": "; ".join(issues),
                            "Resources": ", ".join(resources) if resources else "N/A",
                            "Verbs": ", ".join(verbs) if verbs else "N/A",
                        }
                    )

    def audit_network_security(self) -> None:
        """Audit network security: NetworkPolicy, Service, Ingress."""
        apps_with_policies: Set[str] = set()
        all_apps: Set[str] = set()

        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            all_apps.add(app_dir.name)
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data:
                        continue

                    kind = data.get("kind")
                    name = data.get("metadata", {}).get("name")

                    if kind == "NetworkPolicy":
                        apps_with_policies.add(app_dir.name)
                        spec = data.get("spec", {})
                        pod_selector = spec.get("podSelector", {})

                        if not pod_selector:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "NetworkPolicy",
                                    "Name": name,
                                    "Issue": "PodSelector is empty and may affect all Pods",
                                    "Severity": "Warning",
                                }
                            )

                        ingress = spec.get("ingress", [])
                        egress = spec.get("egress", [])

                        if not ingress and not egress:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "NetworkPolicy",
                                    "Name": name,
                                    "Issue": "no ingress or egress rules",
                                    "Severity": "Warning",
                                }
                            )

                    elif kind == "Service":
                        spec = data.get("spec", {})
                        svc_type = spec.get("type", "ClusterIP")

                        if svc_type in ["LoadBalancer", "NodePort"]:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "Service",
                                    "Name": name,
                                    "Issue": f"Service type is {svc_type}, directly exposed to external network",
                                    "Severity": "Warning",
                                    "Details": f"Ports: {spec.get('ports', [])}",
                                }
                            )

                        external_ips = spec.get("externalIPs", [])
                        if external_ips:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "Service",
                                    "Name": name,
                                    "Issue": f"externalIPs configured: {external_ips}",
                                    "Severity": "Warning",
                                }
                            )

                    elif kind == "Ingress":
                        spec = data.get("spec", {})
                        rules = spec.get("rules", [])
                        tls = spec.get("tls", [])

                        hosts = [r.get("host", "") for r in rules if r.get("host")]

                        if hosts and not tls:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "Ingress",
                                    "Name": name,
                                    "Issue": f"hosts exposed without TLS: {hosts}",
                                    "Severity": "Warning",
                                }
                            )

                        if hosts:
                            self.network_findings.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "Ingress",
                                    "Name": name,
                                    "Issue": f"exposed externally: {', '.join(hosts)}",
                                    "Severity": "Info",
                                }
                            )

        apps_without_policies = all_apps - apps_with_policies
        for app in apps_without_policies:
            self.network_findings.append(
                {
                    "AppName": app,
                    "Type": "NetworkPolicy",
                    "Name": "N/A",
                    "Issue": "application has no NetworkPolicy protection",
                    "Severity": "Warning",
                }
            )

    def audit_host_mounts(self) -> None:
        """Detect hostPath mounts."""
        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data or data.get("kind") not in WORKLOAD_KINDS:
                        continue

                    kind = data.get("kind")
                    name = data.get("metadata", {}).get("name")

                    spec = data.get("spec", {})
                    if kind == "CronJob":
                        pod_spec = (
                            spec.get("jobTemplate", {})
                            .get("spec", {})
                            .get("template", {})
                            .get("spec", {})
                        )
                    else:
                        pod_spec = spec.get("template", {}).get("spec", {})

                    volumes = pod_spec.get("volumes", [])

                    for vol in volumes:
                        if "hostPath" in vol:
                            host_path = vol["hostPath"]
                            path = host_path.get("path", "")
                            path_type = host_path.get("type", "")

                            severity = "Critical"
                            if any(
                                dangerous in path.lower()
                                for dangerous in [
                                    "var/run/docker.sock",
                                    "var/lib/kubelet",
                                    "var/lib/docker",
                                    "etc",
                                    "root",
                                ]
                            ):
                                severity = "Critical"
                            elif path_type in ["Socket", "BlockDevice"]:
                                severity = "Critical"
                            else:
                                severity = "Warning"

                            self.hostpath_mounts.append(
                                {
                                    "AppName": app_dir.name,
                                    "Workload": f"{kind}/{name}",
                                    "VolumeName": vol.get("name", ""),
                                    "HostPath": path,
                                    "Type": path_type,
                                    "Severity": severity,
                                }
                            )

    def audit_security_policies(self) -> None:
        """Check seccomp/AppArmor security policy configuration."""
        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data or data.get("kind") not in WORKLOAD_KINDS:
                        continue

                    kind = data.get("kind")
                    name = data.get("metadata", {}).get("name")
                    annotations = data.get("metadata", {}).get("annotations", {})

                    spec = data.get("spec", {})
                    if kind == "CronJob":
                        pod_spec = (
                            spec.get("jobTemplate", {})
                            .get("spec", {})
                            .get("template", {})
                            .get("spec", {})
                        )
                    else:
                        pod_spec = spec.get("template", {}).get("spec", {})

                    pod_sc = pod_spec.get("securityContext", {})

                    seccomp_profile = pod_sc.get("seccompProfile", {})
                    if seccomp_profile:
                        profile_type = seccomp_profile.get("type", "")
                        if profile_type == "Unconfined":
                            self.security_policies.append(
                                {
                                    "AppName": app_dir.name,
                                    "Workload": f"{kind}/{name}",
                                    "PolicyType": "seccomp",
                                    "Status": "Unconfined",
                                    "Severity": "Warning",
                                }
                            )
                        elif profile_type == "RuntimeDefault":
                            self.security_policies.append(
                                {
                                    "AppName": app_dir.name,
                                    "Workload": f"{kind}/{name}",
                                    "PolicyType": "seccomp",
                                    "Status": "RuntimeDefault",
                                    "Severity": "OK",
                                }
                            )
                    else:
                        has_seccomp = any(
                            k.startswith("seccomp.security.beta.kubernetes.io/")
                            for k in annotations.keys()
                        )
                        if has_seccomp:
                            self.security_policies.append(
                                {
                                    "AppName": app_dir.name,
                                    "Workload": f"{kind}/{name}",
                                    "PolicyType": "seccomp (legacy)",
                                    "Status": "Configured via annotation",
                                    "Severity": "OK",
                                }
                            )
                        else:
                            self.security_policies.append(
                                {
                                    "AppName": app_dir.name,
                                    "Workload": f"{kind}/{name}",
                                    "PolicyType": "seccomp",
                                    "Status": "Not configured",
                                    "Severity": "Warning",
                                }
                            )

                    apparmor_key = "container.apparmor.security.beta.kubernetes.io/"
                    has_apparmor = any(
                        k.startswith(apparmor_key) for k in annotations.keys()
                    )
                    if has_apparmor:
                        for k, v in annotations.items():
                            if k.startswith(apparmor_key):
                                container = k.replace(apparmor_key, "")
                                if v == "unconfined":
                                    self.security_policies.append(
                                        {
                                            "AppName": app_dir.name,
                                            "Workload": f"{kind}/{name}",
                                            "PolicyType": f"AppArmor ({container})",
                                            "Status": "Unconfined",
                                            "Severity": "Warning",
                                        }
                                    )
                                else:
                                    self.security_policies.append(
                                        {
                                            "AppName": app_dir.name,
                                            "Workload": f"{kind}/{name}",
                                            "PolicyType": f"AppArmor ({container})",
                                            "Status": v,
                                            "Severity": "OK",
                                        }
                                    )
                    else:
                        self.security_policies.append(
                            {
                                "AppName": app_dir.name,
                                "Workload": f"{kind}/{name}",
                                "PolicyType": "AppArmor",
                                "Status": "Not configured",
                                "Severity": "Info",
                            }
                        )

    def audit_pod_disruption_and_secrets(self) -> None:
        """Check PodDisruptionBudget and Secret/ServiceAccount configuration."""
        apps_with_workloads: Set[str] = set()
        apps_with_pdb: Set[str] = set()

        for app_dir in self.group_dir.iterdir():
            if not app_dir.is_dir():
                continue
            for yaml_file in app_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    try:
                        data = yaml.safe_load(f)
                    except Exception:
                        continue
                    if not data:
                        continue

                    kind = data.get("kind")
                    name = data.get("metadata", {}).get("name")

                    if kind in WORKLOAD_KINDS:
                        apps_with_workloads.add(app_dir.name)

                    elif kind == "PodDisruptionBudget":
                        apps_with_pdb.add(app_dir.name)
                        spec = data.get("spec", {})
                        min_available = spec.get("minAvailable")
                        max_unavailable = spec.get("maxUnavailable")

                        if min_available:
                            self.pdb_and_secrets.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "PDB",
                                    "Name": name,
                                    "Check": "minAvailable",
                                    "Value": str(min_available),
                                    "Severity": "OK",
                                }
                            )
                        elif max_unavailable:
                            self.pdb_and_secrets.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "PDB",
                                    "Name": name,
                                    "Check": "maxUnavailable",
                                    "Value": str(max_unavailable),
                                    "Severity": "OK",
                                }
                            )

                    elif kind == "Secret":
                        secret_type = data.get("type", "Opaque")

                        issues = []
                        if secret_type == "Opaque":
                            content = data.get("data", {}) or {}
                            for key in content.keys():
                                if "docker" in key.lower() or "registry" in key.lower():
                                    issues.append(
                                        "consider using kubernetes.io/dockerconfigjson type"
                                    )
                                    break

                        self.pdb_and_secrets.append(
                            {
                                "AppName": app_dir.name,
                                "Type": "Secret",
                                "Name": name,
                                "Check": "Type",
                                "Value": secret_type,
                                "Severity": "OK" if not issues else "Warning",
                                "Notes": "; ".join(issues) if issues else "",
                            }
                        )

                    elif kind == "ServiceAccount":
                        automount_token = data.get("automountServiceAccountToken")
                        if automount_token is False:
                            self.pdb_and_secrets.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "ServiceAccount",
                                    "Name": name,
                                    "Check": "automountServiceAccountToken",
                                    "Value": "false",
                                    "Severity": "OK",
                                }
                            )
                        elif automount_token is True:
                            self.pdb_and_secrets.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "ServiceAccount",
                                    "Name": name,
                                    "Check": "automountServiceAccountToken",
                                    "Value": "true",
                                    "Severity": "Warning",
                                    "Notes": "explicitly enabled token automount",
                                }
                            )
                        else:
                            self.pdb_and_secrets.append(
                                {
                                    "AppName": app_dir.name,
                                    "Type": "ServiceAccount",
                                    "Name": name,
                                    "Check": "automountServiceAccountToken",
                                    "Value": "default",
                                    "Severity": "Info",
                                }
                            )

        apps_needing_pdb = apps_with_workloads - apps_with_pdb
        for app in apps_needing_pdb:
            self.pdb_and_secrets.append(
                {
                    "AppName": app,
                    "Type": "PDB",
                    "Name": "N/A",
                    "Check": "Missing",
                    "Value": "No PodDisruptionBudget",
                    "Severity": "Info",
                    "Notes": "recommend configuring a PDB for stateful workloads",
                }
            )

    def save_reports(self) -> None:
        if "audit_dir" in self.paths:
            self.paths["audit_dir"].mkdir(parents=True, exist_ok=True)

        with open(self.paths["csv_cm_to_sec"], "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["AppName", "ConfigMap", "SensitiveKeys", "Usage"]
            )
            writer.writeheader()
            writer.writerows(self.cm_to_secret_rows)

        with open(self.paths["csv_sec_to_cm"], "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["AppName", "Secret", "NonSensitiveKeys"]
            )
            writer.writeheader()
            writer.writerows(self.secret_to_cm_rows)

        if self.rbac_issues:
            with open(self.paths["csv_rbac"], "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["AppName", "Kind", "Name", "Issues", "Resources", "Verbs"],
                )
                writer.writeheader()
                writer.writerows(self.rbac_issues)

        if self.network_findings:
            fieldnames_set: set[str] = set()
            for row in self.network_findings:
                fieldnames_set.update(row.keys())
            fieldnames = sorted(fieldnames_set)
            with open(self.paths["csv_network"], "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.network_findings)

        if self.hostpath_mounts:
            with open(self.paths["csv_hostpath"], "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "AppName",
                        "Workload",
                        "VolumeName",
                        "HostPath",
                        "Type",
                        "Severity",
                    ],
                )
                writer.writeheader()
                writer.writerows(self.hostpath_mounts)

        if self.security_policies:
            with open(self.paths["csv_secpol"], "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["AppName", "Workload", "PolicyType", "Status", "Severity"],
                )
                writer.writeheader()
                writer.writerows(self.security_policies)

        if self.pdb_and_secrets:
            with open(self.paths["csv_pdb_sec"], "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "AppName",
                        "Type",
                        "Name",
                        "Check",
                        "Value",
                        "Severity",
                        "Notes",
                    ],
                )
                writer.writeheader()
                writer.writerows(self.pdb_and_secrets)

        json_path = self.paths["audit_dir"] / "audit_results.json"
        extended_report = []
        for app_report in self.audit_report:
            app_name = app_report.get("AppName")
            extended = app_report.copy()
            extended["RBAC_Issues"] = [
                r for r in self.rbac_issues if r.get("AppName") == app_name
            ]
            extended["Network_Findings"] = [
                r for r in self.network_findings if r.get("AppName") == app_name
            ]
            extended["Host_Mounts"] = [
                r for r in self.hostpath_mounts if r.get("AppName") == app_name
            ]
            extended["Security_Policies"] = [
                r for r in self.security_policies if r.get("AppName") == app_name
            ]
            extended["PDB_and_Secrets"] = [
                r for r in self.pdb_and_secrets if r.get("AppName") == app_name
            ]
            extended_report.append(extended)

        with open(json_path, "w") as f:
            json.dump(extended_report, f, indent=2, ensure_ascii=False)

        console = output.console
        console.print()
        output.success("Audit complete!")
        output.info(f"  - JSON Report: {json_path}")
        output.info(f"  - CM to Secret: {self.paths['csv_cm_to_sec']}")
        output.info(f"  - Secret to CM: {self.paths['csv_sec_to_cm']}")
        if self.rbac_issues:
            output.info(f"  - RBAC Issues: {self.paths['csv_rbac']}")
        if self.network_findings:
            output.info(f"  - Network Security: {self.paths['csv_network']}")
        if self.hostpath_mounts:
            output.info(f"  - HostPath Mounts: {self.paths['csv_hostpath']}")
        if self.security_policies:
            output.info(f"  - Security Policies: {self.paths['csv_secpol']}")
        if self.pdb_and_secrets:
            output.info(f"  - PDB and Secrets: {self.paths['csv_pdb_sec']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Security audit for K8s resources.")
    parser.add_argument("--context", required=True, help="K8s context")
    parser.add_argument("--namespace", required=True, help="K8s namespace")
    args = parser.parse_args()

    auditor = Auditor(args.context, args.namespace)
    auditor.run()


if __name__ == "__main__":
    main()
