import argparse
import subprocess
import os
import sys
import yaml
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import output

BLACKLIST_RESOURCES: Set[str] = {
    "events",
    "endpoints",
    "endpointslices",
    "replicasets", 
    "controllerrevisions",
    "tokenreviews",
    "localsubjectaccessreviews",
    "selfsubjectaccessreviews",
    "selfsubjectrulesreviews",
    "subjectaccessreviews",
    "componentstatuses",
    "bindings",
    "events.events.k8s.io"
}

def run_command(command: str, allow_failure: bool = False) -> Optional[str]:
    """
    Run a shell command and return output.
    allow_failure: if True, return None on failure without raising (but log stderr).
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if allow_failure:
            if e.stderr and e.stderr.strip():
                stderr_lower = e.stderr.lower()
                if "forbidden" in stderr_lower or "unauthorized" in stderr_lower:
                    resource = command.split()[-1] if command else "resource"
                    output.warning(f"Permission denied for {resource} - skipping")
                    output.info(f"  Tip: If this is Secret, you can skip it by not granting Secret permissions")
                    output.info(f"  Other security checks will continue normally")
                else:
                    output.warning(f"Command failed: {command}")
                    output.info(f"Error: {e.stderr.strip()}")
            return None
        else:
            output.error(f"Critical command failed: {command}")
            if e.stderr:
                output.info(f"Error: {e.stderr.strip()}")
            raise e

def validate_context(context: str) -> bool:
    """
    Validate that the Kubernetes context exists.
    """
    cmd = "kubectl config get-contexts -o name"
    try:
        result = run_command(cmd)
        if result is None:
            return False
        contexts = result.splitlines()
        if context not in contexts:
            output.error(f"Context '{context}' not found.")
            output.info("Available contexts:")
            for ctx in contexts:
                output.info(f"  - {ctx}")
            return False
        return True
    except subprocess.CalledProcessError:
        output.error("Failed to list Kubernetes contexts.")
        return False

def validate_namespace(context: str, namespace: str) -> bool:
    """
    Validate that the Kubernetes namespace exists.
    """
    cmd = f"kubectl get namespace {namespace} --context {context} -o name"
    try:
        result = run_command(cmd, allow_failure=True)
        if result is None:
            output.error(f"Namespace '{namespace}' not found in context '{context}'.")
            output.info("Available namespaces:")
            list_cmd = f"kubectl get namespaces --context {context} -o jsonpath='{{.items[*].metadata.name}}'"
            ns_result = run_command(list_cmd, allow_failure=True)
            if ns_result:
                for ns in ns_result.split():
                    output.info(f"  - {ns}")
            return False
        return True
    except subprocess.CalledProcessError:
        output.error(f"Failed to validate namespace '{namespace}'.")
        return False

def get_namespaced_resources(context: str) -> List[str]:
    """Fetch namespaced resource types."""
    output.info(f"Discovering API resources in context '{context}'...")
    cmd = f"kubectl api-resources --verbs=list --namespaced -o name --context {context}"

    try:
        result = run_command(cmd)
    except subprocess.CalledProcessError:
        output.error("Failed to list API resources. Please check connectivity and permissions.")
        sys.exit(1)

    if result is None:
        return []

    resources: List[str] = result.splitlines()
    valid_resources: List[str] = []

    for r in resources:
        name = r.split('.')[0]
        if name not in BLACKLIST_RESOURCES and r not in BLACKLIST_RESOURCES:
            valid_resources.append(r)

    output.success(f"Found {len(valid_resources)} valid resource types to scan.")
    return valid_resources

def export_resources(context: str, namespace: str, resources: List[str]) -> int:
    paths = utils.get_output_paths(context, namespace)
    base_dir = paths["export"]
    total_exported = 0
    
    for resource_type in resources:
        cmd = f"kubectl get {resource_type} -n {namespace} --context {context} -o yaml"
        
        yaml_output = run_command(cmd, allow_failure=True)
        
        if not yaml_output:
            continue
            
        try:
            data: Dict[str, Any] = yaml.safe_load(yaml_output)
        except yaml.YAMLError as e:
            output.warning(f"Failed to parse YAML for {resource_type}: {e}")
            continue
            
        items: List[Dict[str, Any]] = data.get("items", [])
        if not items:
            continue

        dir_name = resource_type
        save_dir = os.path.join(base_dir, dir_name)

        os.makedirs(save_dir, exist_ok=True)
        output.info(f"Exporting {len(items)} {resource_type}...")
        
        for item in items:
            metadata: Dict[str, Any] = item.get("metadata", {})
            name: Optional[str] = metadata.get("name")
            
            if not name:
                continue
            
            if "apiVersion" not in item and "apiVersion" in data:
                item["apiVersion"] = data["apiVersion"]
            
            file_path = os.path.join(save_dir, f"{name}.yaml")
            with open(file_path, "w") as f:
                yaml.dump(item, f, default_flow_style=False, sort_keys=False)
            
            total_exported += 1
                
    return total_exported

def main() -> None:
    parser = argparse.ArgumentParser(description="Export K8s resources using kubectl.")
    parser.add_argument("--context", required=True, help="K8s context")
    parser.add_argument("--namespace", required=True, help="K8s namespace")
    
    args = parser.parse_args()

    try:
        run_command("kubectl version --client")
    except subprocess.CalledProcessError:
        output.error("kubectl not found or not working.")
        sys.exit(1)

    if not validate_context(args.context):
        sys.exit(1)

    if not validate_namespace(args.context, args.namespace):
        sys.exit(1)

    resources = get_namespaced_resources(args.context)

    output.header(f"Starting export for namespace '{args.namespace}'")
    count = export_resources(args.context, args.namespace, resources)

    console = output.console
    console.print()
    output.success(f"Export complete! Total files: {count}")
    paths = utils.get_output_paths(args.context, args.namespace)
    output.info(f"Data saved to: {paths['export']}")

if __name__ == "__main__":
    main()
