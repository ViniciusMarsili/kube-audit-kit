from pathlib import Path
from typing import Dict
import os

def get_output_paths(context: str, namespace: str) -> Dict[str, Path]:
    """
    Get output paths for all stages.
    Output structure: output/{context}/{namespace}/{stage}/

    Output path priority:
    1. KUBE_AUDIT_OUTPUT env var (set by SKILL.md)
    2. Current working directory (Path.cwd())
    """
    # Use env var if set (SKILL.md sets this to user's working directory)
    if "KUBE_AUDIT_OUTPUT" in os.environ:
        base = Path(os.environ["KUBE_AUDIT_OUTPUT"])
    else:
        # Fallback to current working directory
        base = Path.cwd() / "output"

    base_output = base / context / namespace

    return {
        "export": base_output / "export",
        "sanitize": base_output / "sanitize",
        "sanitize_fields": base_output / "sanitize_fields",
        "group": base_output / "group",
        "orphan": base_output / "ungrouped_resources.txt",
        "audit_dir": base_output / "audit",
        "audit": base_output / "audit" / "audit_report.md",
        "csv_cm_to_sec": base_output / "audit" / "configmap_to_secret.csv",
        "csv_sec_to_cm": base_output / "audit" / "secret_to_configmap.csv",
        "csv_rbac": base_output / "audit" / "rbac_issues.csv",
        "csv_network": base_output / "audit" / "network_security.csv",
        "csv_hostpath": base_output / "audit" / "hostpath_mounts.csv",
        "csv_secpol": base_output / "audit" / "security_policies.csv",
        "csv_pdb_sec": base_output / "audit" / "pdb_and_secrets.csv",
    }
