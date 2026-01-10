import os
import yaml
import json
import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import output

ResourceData = Dict[str, Any]
ResourceKey = Tuple[str, str]
ResourceIndex = Dict[ResourceKey, ResourceData]

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}

def load_resources(context: str, namespace: str) -> Tuple[ResourceIndex, List[Path]]:
    """
    Load all resources under the sanitize directory.
    Returns: (index dict, file path list)
    """
    paths = utils.get_output_paths(context, namespace)
    sanitize_dir = paths["sanitize"]
    index: ResourceIndex = {}
    paths_list: List[Path] = []

    if not sanitize_dir.exists():
        output.error(f"Sanitize directory {sanitize_dir} does not exist.")
        return {}, []

    output.info(f"Loading resources from {sanitize_dir}...")
    for root, _, files in os.walk(sanitize_dir):
        for file in files:
            if not file.endswith(".yaml"):
                continue
            
            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    docs = list(yaml.safe_load_all(f))
                    for doc in docs:
                        if not doc or not isinstance(doc, dict):
                            continue
                        
                        kind = doc.get("kind")
                        metadata = doc.get("metadata", {})
                        name = metadata.get("name")
                        
                        if kind and name:
                            index[(kind, name)] = doc
                            paths_list.append(file_path)
            except Exception as e:
                output.warning(f"Error loading {file_path}: {e}")

    output.success(f"Loaded {len(index)} resources.")
    return index, paths_list

def match_labels(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
    """Check whether labels satisfy the selector."""
    if not selector or not isinstance(selector, dict):
        return False
    for k, v in selector.items():
        if labels.get(k) != v:
            return False
    return True

def get_pod_template_spec(workload: ResourceData) -> Optional[Dict[str, Any]]:
    """Extract the Pod template spec from a workload."""
    kind = workload.get("kind")
    spec = workload.get("spec", {})

    if kind == "CronJob":
        result = spec.get("jobTemplate", {}).get("spec", {}).get("template")
    else:
        result = spec.get("template")

    if result is None or isinstance(result, dict):
        return result
    return None

def find_associated_resources(
    anchor_key: ResourceKey, 
    anchor_data: ResourceData, 
    index: ResourceIndex
) -> Tuple[List[ResourceKey], Dict[str, List[str]]]:
    """
    Find all resources associated with the anchor.
    """
    associated: List[ResourceKey] = []
    config_usage: Dict[str, List[str]] = {} 
    
    kind, name = anchor_key
    pod_template = get_pod_template_spec(anchor_data)
    if not pod_template:
        return [], {}

    pod_meta = pod_template.get("metadata", {})
    pod_labels = pod_meta.get("labels", {})
    pod_spec = pod_template.get("spec", {})

    spec = anchor_data.get("spec", {})
    selector_dict: Dict[str, str] = {}
    if kind == "CronJob":
        selector_dict = spec.get("jobTemplate", {}).get("spec", {}).get("selector", {}).get("matchLabels", {})
    else:
        selector_obj = spec.get("selector", {})
        if isinstance(selector_obj, dict):
            selector_dict = selector_obj.get("matchLabels", selector_obj)

    for (r_kind, r_name), r_data in index.items():
        if r_kind == "Service":
            s_selector = r_data.get("spec", {}).get("selector", {})
            if s_selector and match_labels(s_selector, pod_labels):
                associated.append((r_kind, r_name))
        elif r_kind == "PodDisruptionBudget":
            p_selector = r_data.get("spec", {}).get("selector", {}).get("matchLabels", {})
            if p_selector and match_labels(p_selector, pod_labels):
                associated.append((r_kind, r_name))
        
        elif r_kind == "Pod":
            r_labels = r_data.get("metadata", {}).get("labels", {})
            if selector_dict and match_labels(selector_dict, r_labels):
                associated.append((r_kind, r_name))
                if ("PodMetrics", r_name) in index:
                    associated.append(("PodMetrics", r_name))

        elif r_kind == "HorizontalPodAutoscaler":
            target = r_data.get("spec", {}).get("scaleTargetRef", {})
            if target.get("kind") == kind and target.get("name") == name:
                associated.append((r_kind, r_name))

    for vol in pod_spec.get("volumes", []):
        if "configMap" in vol:
            cm_name = vol["configMap"].get("name")
            if cm_name:
                key = ("ConfigMap", cm_name)
                if key in index:
                    associated.append(key)
                    config_usage.setdefault(f"ConfigMap/{cm_name}", []).append("Volume")
        
        if "secret" in vol:
            sec_name = vol["secret"].get("secretName")
            if sec_name:
                key = ("Secret", sec_name)
                if key in index:
                    associated.append(key)
                    config_usage.setdefault(f"Secret/{sec_name}", []).append("Volume")

        if "persistentVolumeClaim" in vol:
            pvc_name = vol["persistentVolumeClaim"].get("claimName")
            if pvc_name:
                key = ("PersistentVolumeClaim", pvc_name)
                if key in index:
                    associated.append(key)

    for container in pod_spec.get("containers", []) + pod_spec.get("initContainers", []):
        for env in container.get("env", []):
            val_from = env.get("valueFrom", {})
            if "configMapKeyRef" in val_from:
                cm_name = val_from["configMapKeyRef"].get("name")
                if cm_name:
                    key = ("ConfigMap", cm_name)
                    if key in index:
                        associated.append(key)
                        config_usage.setdefault(f"ConfigMap/{cm_name}", []).append("EnvVar")
            if "secretKeyRef" in val_from:
                sec_name = val_from["secretKeyRef"].get("name")
                if sec_name:
                    key = ("Secret", sec_name)
                    if key in index:
                        associated.append(key)
                        config_usage.setdefault(f"Secret/{sec_name}", []).append("EnvVar")
        
        for env_from in container.get("envFrom", []):
            if "configMapRef" in env_from:
                cm_name = env_from["configMapRef"].get("name")
                if cm_name:
                    key = ("ConfigMap", cm_name)
                    if key in index:
                        associated.append(key)
                        config_usage.setdefault(f"ConfigMap/{cm_name}", []).append("EnvVar")
            if "secretRef" in env_from:
                sec_name = env_from["secretRef"].get("name")
                if sec_name:
                    key = ("Secret", sec_name)
                    if key in index:
                        associated.append(key)
                        config_usage.setdefault(f"Secret/{sec_name}", []).append("EnvVar")

    sa_name = pod_spec.get("serviceAccountName", "default")
    sa_key = ("ServiceAccount", sa_name)
    if sa_key in index:
        associated.append(sa_key)
        for (r_kind, r_name), r_data in index.items():
            if r_kind in ["RoleBinding", "ClusterRoleBinding"]:
                subjects = r_data.get("subjects", [])
                for sub in subjects:
                    if sub.get("kind") == "ServiceAccount" and sub.get("name") == sa_name:
                        associated.append((r_kind, r_name))
                        role_ref = r_data.get("roleRef", {})
                        role_kind = role_ref.get("kind")
                        role_name = role_ref.get("name")
                        if role_kind and role_name:
                            role_key = (role_kind, role_name)
                            if role_key in index:
                                associated.append(role_key)

    associated_services = {name for (k, name) in associated if k == "Service"}
    if associated_services:
        for (r_kind, r_name), r_data in index.items():
            if r_kind == "Ingress":
                rules = r_data.get("spec", {}).get("rules", [])
                for rule in rules:
                    http = rule.get("http", {})
                    paths = http.get("paths", [])
                    for path in paths:
                        backend = path.get("backend", {})
                        svc = backend.get("service", {})
                        svc_name = svc.get("name")
                        if svc_name and svc_name in associated_services:
                            associated.append((r_kind, r_name))
                            break

    for (r_kind, r_name), r_data in index.items():
        if r_kind == "PodMetrics" and (r_kind, r_name) not in associated:
            if r_name.startswith(name + "-"):
                associated.append((r_kind, r_name))

    return list(set(associated)), config_usage

def save_group(
    context: str,
    namespace: str,
    anchor_name: str, 
    resources: List[Tuple[ResourceKey, ResourceData]], 
    config_usage: Dict[str, List[str]]
) -> None:
    paths = utils.get_output_paths(context, namespace)
    group_dir = paths["group"] / anchor_name
    
    if group_dir.exists():
        shutil.rmtree(group_dir)
    group_dir.mkdir(parents=True, exist_ok=True)

    for (kind, name), data in resources:
        file_path = group_dir / f"{kind}_{name}.yaml"
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)

    usage_path = group_dir / "config_usage.json"
    final_usage = {k: list(set(v)) for k, v in config_usage.items()}
    with open(usage_path, 'w', encoding='utf-8') as f:
        json.dump(final_usage, f, indent=2, ensure_ascii=False)

def main() -> None:
    parser = argparse.ArgumentParser(description="Smart group K8s resources into applications.")
    parser.add_argument("--context", required=True, help="K8s context")
    parser.add_argument("--namespace", required=True, help="K8s namespace")
    args = parser.parse_args()
    
    context = args.context
    namespace = args.namespace
    
    index, _ = load_resources(context, namespace)
    if not index: return
    grouped_keys: Set[ResourceKey] = set()
    anchors: List[ResourceKey] = []
    for key in index.keys():
        if key[0] in WORKLOAD_KINDS:
            anchors.append(key)
    for anchor_key in anchors:
        anchor_kind, anchor_name = anchor_key
        anchor_data = index[anchor_key]
        assoc_keys, config_usage = find_associated_resources(anchor_key, anchor_data, index)
        assoc_keys.append(anchor_key)
        group_resources: List[Tuple[ResourceKey, ResourceData]] = []
        for key in set(assoc_keys):
            group_resources.append((key, index[key]))
            grouped_keys.add(key)
        save_group(context, namespace, anchor_name, group_resources, config_usage)
    all_keys = set(index.keys())
    orphan_keys = all_keys - grouped_keys
    
    paths = utils.get_output_paths(context, namespace)
    orphan_file = paths["orphan"]
    orphan_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(orphan_file, 'w', encoding='utf-8') as f:
        for kind, name in sorted(list(orphan_keys)):
            f.write(f"{kind}/{name}\n")
    console = output.console
    console.print()
    output.success(f"Grouping complete. Apps: {len(anchors)}, Orphans: {len(orphan_keys)}")

if __name__ == "__main__":
    main()
