"""Prompt Management — versioned Jinja2 templates loaded from disk."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from app.core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"

_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        _env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
    return _env


def render_prompt(name: str, variables: dict | None = None) -> str:
    """Render a prompt template with variables.

    Args:
        name: Template filename (e.g. 'calculation_v1.j2')
        variables: Dict of template variables

    Returns:
        Rendered prompt string
    """
    env = _get_env()
    try:
        template = env.get_template(name)
        return template.render(**(variables or {}))
    except Exception:
        # Fallback: return raw content if template not found
        return f"[Prompt not found: {name}]"


def get_prompt_content(name: str) -> str | None:
    """Read raw prompt content (without rendering)."""
    env = _get_env()
    try:
        source, _, _ = env.loader.get_source(env, name)
        return source
    except Exception:
        return None


def list_prompts() -> list[str]:
    """List all available prompt templates."""
    if not PROMPTS_DIR.exists():
        return []
    return sorted([f.name for f in PROMPTS_DIR.glob("*.j2")])
