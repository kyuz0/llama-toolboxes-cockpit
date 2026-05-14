import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
ASSETS_DIR = ROOT_DIR / "assets"
MODELS_JSON = ASSETS_DIR / "models.json"
TOOLBOXES_JSON = ASSETS_DIR / "toolboxes.json"

def load_models() -> list[dict]:
    if MODELS_JSON.exists():
        with open(MODELS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_toolboxes() -> dict:
    if TOOLBOXES_JSON.exists():
        with open(TOOLBOXES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_platforms() -> list[dict]:
    """Returns the list of platform definitions from toolboxes.json."""
    data = load_toolboxes()
    return data.get("platforms", [])

def get_platform(platform_id: str) -> dict | None:
    """Returns a single platform dict by its ID, or None if not found."""
    for p in get_platforms():
        if p.get("id") == platform_id:
            return p
    return None

def get_platform_registry(platform_id: str) -> str:
    """Returns the Docker registry for a given platform ID."""
    platform = get_platform(platform_id)
    if platform:
        return platform.get("registry", "")
    return ""
