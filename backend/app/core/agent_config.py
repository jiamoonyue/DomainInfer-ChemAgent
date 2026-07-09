"""Agent Configuration — load Agent definitions from YAML files."""

from pathlib import Path

import yaml

from app.core.config import PROJECT_ROOT

AGENTS_DIR = PROJECT_ROOT / "agents"


def load_agent_config(agent_type: str, domain: str = "chem") -> dict | None:
    """Load an agent YAML config file.

    Args:
        agent_type: Agent type name (e.g. 'calculation', 'safety')
        domain: Domain namespace (e.g. 'chem', 'legal')

    Returns:
        Parsed config dict, or None if not found
    """
    path = AGENTS_DIR / domain / f"{agent_type}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_agents(domain: str = "chem") -> list[dict]:
    """List all agent configs for a domain."""
    domain_dir = AGENTS_DIR / domain
    if not domain_dir.exists():
        return []
    agents = []
    for fp in sorted(domain_dir.glob("*.yaml")):
        with open(fp, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["_file"] = fp.name
            agents.append(data)
    return agents


def list_domains() -> list[str]:
    """List available agent domains."""
    if not AGENTS_DIR.exists():
        return []
    return sorted([
        d.name for d in AGENTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
