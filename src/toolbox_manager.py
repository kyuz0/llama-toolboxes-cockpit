import subprocess
import os
import urllib.request
import json
import shutil

def detect_engines() -> list[str]:
    engines = []
    if shutil.which("podman"):
        engines.append("podman")
    if shutil.which("docker"):
        engines.append("docker")
    return engines

def get_toolbox_engine() -> str:
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            content = f.read().lower()
            if "id=ubuntu" in content or "id=debian" in content or "id=arch" in content or "id_like=arch" in content:
                engines = detect_engines()
                return "podman" if "podman" in engines else "docker"
    return "podman"

def get_os_toolbox_cmd() -> str:
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            content = f.read().lower()
            if "id=ubuntu" in content or "id=debian" in content or "id=arch" in content or "id_like=arch" in content:
                return "distrobox"
    return "toolbox"

def get_installed_toolboxes(registry_match: str, specific_engine: str = None) -> list[dict]:
    """Returns a list of dicts with name, image, status, engine."""
    engines = [specific_engine] if specific_engine else detect_engines()
    toolboxes = []
    
    for engine in engines:
        try:
            res = subprocess.run(
                [engine, "ps", "-a", "--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.CreatedAt}}"], 
                capture_output=True, text=True, check=True
            )
            lines = res.stdout.strip().split('\n')
            for line in lines:
                if not line: continue
                parts = line.split('|')
                if len(parts) >= 3:
                    if len(parts) >= 3:
                        name, image, status = parts[0], parts[1], parts[2]
                        name = name.strip()
                        image = image.strip()
                        status = status.strip()
                        status = status.replace("292 years ago", "Unknown Date")
                        
                        created = ""
                        if len(parts) >= 4:
                            created_raw = parts[3].strip()
                            created = created_raw.split()[0] if created_raw else ""
                        
                        if registry_match and registry_match in image:
                            toolboxes.append({
                                "name": name,
                                "image": image,
                                "status": status,
                                "created": created,
                                "engine": engine
                            })
        except Exception:
            pass
    return toolboxes

def get_all_toolboxes(registry_match: str, config_data: dict) -> dict:
    engine = get_toolbox_engine()
    installed = get_installed_toolboxes(registry_match, engine)
    
    installed_dict = {tb["name"]: tb for tb in installed}
    
    grouped_toolboxes = {}
    
    for group in config_data.get("groups", []):
        group_name = group.get("name", "Unknown Group")
        grouped_toolboxes[group_name] = []
        
        for ctb in group.get("toolboxes", []):
            name = ctb["name"]
            tag = ctb.get("tag", "latest")
            desc = ctb.get("description", "")
            image = f"{registry_match}:{tag}"
            
            if name in installed_dict:
                tb = installed_dict[name]
                tb["args"] = ctb.get("engine_args", [])
                tb["description"] = desc
                tb["group"] = group_name
                grouped_toolboxes[group_name].append(tb)
                del installed_dict[name]
            else:
                grouped_toolboxes[group_name].append({
                    "name": name,
                    "image": image,
                    "description": desc,
                    "status": "Not Installed",
                    "created": "",
                    "engine": engine,
                    "args": ctb.get("engine_args", []),
                    "group": group_name
                })
                
    unsupported = []
    for tb in installed_dict.values():
        tb["args"] = []
        tb["description"] = ""
        tb["group"] = "Unsupported / Legacy"
        if "created" not in tb:
            tb["created"] = ""
        unsupported.append(tb)
        
    if unsupported:
        grouped_toolboxes["Unsupported / Legacy"] = unsupported
        
    return grouped_toolboxes

def create_toolbox(name: str, image: str, args: list[str]):
    cmd = get_os_toolbox_cmd()
    engine = get_toolbox_engine()
    os.environ["DBX_CONTAINER_MANAGER"] = engine
    
    # Pull first
    subprocess.run([engine, "pull", image], check=True)
    
    full_cmd = [cmd, "create", name, "--image", image]
    if args:
        full_cmd.append("--")
        full_cmd.extend(args)
    subprocess.run(full_cmd, check=True)

def delete_toolbox(name: str):
    cmd = get_os_toolbox_cmd()
    os.environ["DBX_CONTAINER_MANAGER"] = get_toolbox_engine()
    subprocess.run([cmd, "rm", "-f", name], check=True)

def get_remote_image_date(image: str) -> str:
    if not ("docker.io" in image or "kyuz0" in image):
        return None
    parts = image.split(':')
    repo = parts[0].replace('docker.io/', '')
    tag = parts[1] if len(parts) > 1 else "latest"
    
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags/{tag}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("last_updated")
    except Exception:
        return None
