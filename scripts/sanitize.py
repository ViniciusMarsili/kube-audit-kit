import os
import yaml
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import output

METADATA_FIELDS_TO_REMOVE: List[str] = [
    "uid", "resourceVersion", "creationTimestamp", "generation",
    "managedFields", "ownerReferences", "selfLink"
]

ANNO_FIELDS_TO_REMOVE: List[str] = [
    "kubectl.kubernetes.io/last-applied-configuration",
    "deployment.kubernetes.io/revision"
]

def clean_metadata_dict(metadata: Dict[str, Any], path_prefix: str) -> List[str]:
    """
    Sanitize a single metadata dict and return removed field logs.
    """
    removed_logs: List[str] = []
    
    for field in METADATA_FIELDS_TO_REMOVE:
        if field in metadata:
            val = metadata.pop(field)
            removed_logs.append(f"{path_prefix}.{field} = {val}")

    if "annotations" in metadata:
        annotations = metadata["annotations"]
        if isinstance(annotations, dict):
            for field in ANNO_FIELDS_TO_REMOVE:
                if field in annotations:
                    val = annotations.pop(field)
                    removed_logs.append(f"{path_prefix}.annotations.{field} = {val}")
            
            if not annotations:
                metadata.pop("annotations")
        elif annotations is None:
            metadata.pop("annotations")

    return removed_logs

def recursive_sanitize(data: Any, path: str = "") -> List[str]:
    """
    Recursively traverse and sanitize all 'metadata' keys.
    """
    logs: List[str] = []

    if isinstance(data, dict):
        if "metadata" in data and isinstance(data["metadata"], dict):
            current_path = f"{path}.metadata" if path else "metadata"
            logs.extend(clean_metadata_dict(data["metadata"], current_path))
        
        for key, value in data.items():
            if key == "metadata":
                continue
            
            new_path = f"{path}.{key}" if path else key
            logs.extend(recursive_sanitize(value, new_path))

    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_path = f"{path}[{idx}]"
            logs.extend(recursive_sanitize(item, new_path))

    return logs

def sanitize_resource(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Sanitize a K8s resource.
    """
    removed_fields: List[str] = []

    if "status" in data:
        removed_fields.append(f"status = {data.pop('status')}")

    removed_fields.extend(recursive_sanitize(data))

    return data, removed_fields

def process_directory(context: str, namespace: str) -> None:
    paths = utils.get_output_paths(context, namespace)
    export_dir = paths["export"]
    sanitize_dir = paths["sanitize"]
    records_dir = paths["sanitize_fields"]

    if not export_dir.exists():
        output.error(f"Export directory {export_dir} does not exist.")
        return

    count: int = 0
    for root, dirs, files in os.walk(export_dir):
        for file in files:
            if not file.endswith(".yaml"):
                continue
            
            rel_path: Path = Path(root).relative_to(export_dir)
            source_file: Path = Path(root) / file
            
            with open(source_file, 'r', encoding='utf-8') as f:
                try:
                    docs: List[Any] = list(yaml.safe_load_all(f))
                except Exception as e:
                    output.error(f"Error reading {source_file}: {e}")
                    continue

            sanitized_docs: List[Dict[str, Any]] = []
            all_removed_fields: List[str] = []

            for doc in docs:
                if not doc: continue
                if isinstance(doc, dict):
                    sanitized_doc, removed = sanitize_resource(doc)
                    sanitized_docs.append(sanitized_doc)
                    all_removed_fields.extend(removed)
                else:
                    output.warning(f"Skipping non-dict document in {source_file}")

            target_yaml_path: Path = sanitize_dir / rel_path / file
            target_record_path: Path = records_dir / rel_path / file.replace(".yaml", ".txt")

            target_yaml_path.parent.mkdir(parents=True, exist_ok=True)
            target_record_path.parent.mkdir(parents=True, exist_ok=True)

            with open(target_yaml_path, 'w', encoding='utf-8') as f:
                if len(sanitized_docs) == 1:
                    yaml.dump(sanitized_docs[0], f, sort_keys=False, allow_unicode=True)
                else:
                    yaml.dump_all(sanitized_docs, f, sort_keys=False, allow_unicode=True)

            with open(target_record_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(all_removed_fields))

            count += 1
            output.info(f"Sanitized: {rel_path}/{file}")

    console = output.console
    console.print()
    output.success(f"Total processed: {count} files.")

def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize exported K8s resources.")
    parser.add_argument("--context", required=True, help="K8s context")
    parser.add_argument("--namespace", required=True, help="K8s namespace")
    
    args = parser.parse_args()
    process_directory(args.context, args.namespace)

if __name__ == "__main__":
    main()
