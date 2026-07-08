"""Prompt loader - Carga prompts versionados desde archivos YAML."""
import os
import yaml
from typing import Dict, Any, Optional

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

_cache: Dict[str, Dict[str, Any]] = {}


def load_prompt(agent_name: str, version: str = "v1") -> Dict[str, Any]:
    """Carga un prompt YAML versionado para un agente específico.
    
    Args:
        agent_name: Nombre del agente (e.g. 'atencion_cliente')
        version: Versión del prompt (default 'v1')
    
    Returns:
        Dict con la configuración del prompt
    """
    cache_key = f"{version}/{agent_name}"
    if cache_key in _cache:
        return _cache[cache_key]

    path = os.path.join(PROMPTS_DIR, version, f"{agent_name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _cache[cache_key] = data
    return data


def get_system_prompt(agent_name: str, version: str = "v1") -> str:
    """Atajo para obtener solo el system_prompt de un agente."""
    data = load_prompt(agent_name, version)
    return data.get("system_prompt", "")


def list_available_prompts(version: str = "v1") -> list:
    """Lista los prompts disponibles para una versión."""
    version_dir = os.path.join(PROMPTS_DIR, version)
    if not os.path.exists(version_dir):
        return []
    return [f.replace(".yaml", "") for f in os.listdir(version_dir) if f.endswith(".yaml")]
