import os
import re
import glob
import json
import fnmatch
from huggingface_hub import HfApi
from pathlib import Path

CONFIG_FILE = Path(os.path.expanduser("~/.llama-cockpit.conf"))

def get_models_dir() -> Path:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                conf = json.load(f)
                if "models_dir" in conf:
                    return Path(os.path.expanduser(conf["models_dir"]))
        except Exception:
            pass
    return Path(os.path.expanduser("~/models"))

def save_models_dir(path_str: str) -> bool:
    conf = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                conf = json.load(f)
        except Exception:
            pass
    
    conf["models_dir"] = path_str
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(conf, f, indent=4)
        
        new_dir = Path(os.path.expanduser(path_str))
        new_dir.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_active_platform() -> str:
    """Reads the active platform ID from config, defaults to 'strix-halo'."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                conf = json.load(f)
                return conf.get("active_platform", "strix-halo")
        except Exception:
            pass
    return "strix-halo"

def save_active_platform(platform_id: str) -> bool:
    """Persists the active platform ID to the config file."""
    conf = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                conf = json.load(f)
        except Exception:
            pass

    conf["active_platform"] = platform_id
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(conf, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def scan_local_models() -> list[dict]:
    models_dir = get_models_dir()
    if not models_dir.exists():
        return []
    
    found = set()
    for root, dirs, files in os.walk(models_dir):
        for f in files:
            if f.endswith(".gguf"):
                path = Path(root) / f
                rel_path = path.relative_to(models_dir)
                
                # Check for sharded models (-0000X-of-0000Y)
                if "-000" in f and "-of-000" in f:
                    grouped_pattern = re.sub(r"-000\d+-of-000\d+\.gguf$", "-*-of-*.gguf", str(rel_path))
                    found.add(grouped_pattern)
                else:
                    found.add(str(rel_path))
                    
    return [{"name": m, "path": str(models_dir / m)} for m in sorted(list(found))]

def is_quant_downloaded(repo: str, quant: str) -> bool:
    models_dir = get_models_dir()
    if not models_dir.exists():
        return False
        
    repo_base = repo.split('/')[-1].replace('-GGUF', '').lower()
    # Normalized form strips hyphens/underscores for flexible comparison
    repo_norm = repo_base.replace('-', '').replace('_', '')
    
    # 1. Exact path match based on standard download dir
    standard_dir = models_dir / repo.split('/')[-1]
    if (standard_dir / quant).exists():
        return True
    
    def _dir_matches_repo(dirpath: str) -> bool:
        """Check if a directory path is related to this specific repo."""
        rel = os.path.relpath(dirpath, models_dir).lower()
        for part in rel.split(os.sep):
            if part == '.':
                continue
            part_norm = part.replace('-', '').replace('_', '')
            # Require repo_base to be IN the dir name (not the reverse),
            # so "qwen3635ba3b" won't match a dir for "qwen3635ba3bmtp"
            if repo_norm in part_norm:
                return True
        return False
        
    # 2. Fuzzy scan across models_dir
    for root, dirs, files in os.walk(models_dir):
        if quant.endswith(".gguf"):
            # Only match files in directories related to this repo
            if not _dir_matches_repo(root):
                continue
            if "*" in quant:
                for f in files:
                    if fnmatch.fnmatch(f, quant):
                        return True
            else:
                if quant in files:
                    return True
        else:
            # quant is a folder name like "BF16"
            if quant in dirs:
                if _dir_matches_repo(root):
                    return True
                try:
                    for f in os.listdir(os.path.join(root, quant)):
                        if repo_base in f.lower():
                            return True
                except OSError:
                    pass
                        
    return False

def resolve_model_path(pattern_path: str) -> str:
    """Resolves a pattern like *-of-*.gguf to the first actual file."""
    actual_files = glob.glob(pattern_path)
    if actual_files:
        actual_files.sort()
        return actual_files[0]
    return pattern_path

def get_hf_quants(repo: str) -> list[str]:
    api = HfApi()
    try:
        files = api.list_repo_files(repo_id=repo, repo_type="model")
    except Exception:
        return []

    quants = set()
    for f in files:
        if f.endswith(".gguf"):
            parts = f.split('/')
            if len(parts) > 1:
                # It's in a subfolder (e.g., "BF16")
                quants.add(parts[0])
            else:
                # Top level file: Check if it's a shard
                if "-000" in f and "-of-000" in f:
                    grouped_pattern = re.sub(r"-000\d+-of-000\d+\.gguf$", "-*-of-*.gguf", f)
                    quants.add(grouped_pattern)
                else:
                    quants.add(f)
    return sorted(list(quants))

def get_download_cmd(repo: str, quant_pattern: str) -> list[str]:
    # Determine the pattern
    if quant_pattern.endswith(".gguf"):
        download_pattern = quant_pattern
    else:
        download_pattern = f"{quant_pattern}/*"
        
    final_dir = str(get_models_dir() / repo.split('/')[-1])
    
    cmd = [
        "hf", "download",
        repo,
        download_pattern,
        "--local-dir", final_dir
    ]
    return cmd
