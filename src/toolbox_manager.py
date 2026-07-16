import subprocess
import os
import urllib.request
import json
import shutil
import re
import grp
import shlex
from pathlib import Path
from datetime import datetime, timezone

def upgrade_groups_for_podman(engine: str, args: list[str]) -> list[str]:
    """Normalize supplementary group arguments for Podman.
    
    Podman's --group-add with named groups resolves GIDs inside the container,
    which may not match the host's video/render GIDs needed for /dev/kfd access.
    --group-add keep-groups passes through all host supplementary GIDs by number.
    Podman requires keep-groups to be the only --group-add value, so remove
    explicit groups such as rdma once keep-groups is needed.
    Docker does not support keep-groups, so we leave args unchanged for Docker.
    """
    if engine != "podman":
        return list(args)

    group_values = []
    i = 0
    while i < len(args):
        if args[i] == "--group-add" and i + 1 < len(args):
            group_values.append(args[i + 1])
            i += 2
            continue
        if args[i].startswith("--group-add="):
            group_values.append(args[i].split("=", 1)[1])
        i += 1

    use_keep_groups = any(
        group in ("video", "render", "rdma", "keep-groups")
        for group in group_values
    )
    if not use_keep_groups:
        return list(args)

    result = []
    added_keep = False
    i = 0
    while i < len(args):
        if args[i] == "--group-add" and i + 1 < len(args):
            if not added_keep:
                result.extend(["--group-add", "keep-groups"])
                added_keep = True
            i += 2
            continue
        if args[i].startswith("--group-add="):
            if not added_keep:
                result.extend(["--group-add", "keep-groups"])
                added_keep = True
            i += 1
            continue
        result.append(args[i])
        i += 1
    return result

def use_host_group_ids_for_docker(engine: str, args: list[str]) -> list[str]:
    """Use host GIDs for device groups so Docker works across host distros."""
    if engine != "docker":
        return list(args)

    result = []
    i = 0
    while i < len(args):
        if args[i] == "--group-add" and i + 1 < len(args):
            group = args[i + 1]
            try:
                group = str(grp.getgrnam(group).gr_gid)
            except KeyError:
                pass
            result.extend(["--group-add", group])
            i += 2
            continue
        if args[i].startswith("--group-add="):
            group = args[i].split("=", 1)[1]
            try:
                group = str(grp.getgrnam(group).gr_gid)
            except KeyError:
                pass
            result.append(f"--group-add={group}")
            i += 1
            continue
        result.append(args[i])
        i += 1
    return result

def remove_group_add_values(args: list[str], values: set[str]) -> list[str]:
    """Remove selected --group-add values in either supported argument form."""
    result = []
    i = 0
    while i < len(args):
        if args[i] == "--group-add" and i + 1 < len(args):
            if args[i + 1] in values:
                i += 2
                continue
        elif args[i].startswith("--group-add="):
            if args[i].split("=", 1)[1] in values:
                i += 1
                continue
        result.append(args[i])
        i += 1
    return result

def get_interactive_rdma_args(
    toolbox_cmd: str,
    engine: str,
    rdma_path: str = "/dev/infiniband",
) -> list[str]:
    """Return RDMA flags that can be passed through Distrobox."""
    if os.path.basename(toolbox_cmd) != "distrobox" or not os.path.isdir(rdma_path):
        return []

    if engine == "podman":
        return [
            "--device", rdma_path,
            "--group-add", "rdma",
            "--ulimit", "memlock=-1",
        ]

    if engine == "docker":
        args = []
        device_gids = set()
        for device in sorted(Path(rdma_path).iterdir()):
            args.extend(["--device", str(device)])
            try:
                device_gids.add(device.stat().st_gid)
            except OSError:
                pass
        if args:
            if device_gids:
                for gid in sorted(device_gids):
                    args.extend(["--group-add", str(gid)])
            else:
                args.extend(["--group-add", "rdma"])
            args.extend(["--ulimit", "memlock=-1"])
        return args

    return []

def extend_missing_option_pairs(args: list[str], extras: list[str]) -> list[str]:
    """Append missing flag/value pairs without modifying the input list."""
    result = list(args)
    for index in range(0, len(extras), 2):
        flag, value = extras[index:index + 2]
        present = any(
            result[pos] == flag and result[pos + 1] == value
            for pos in range(len(result) - 1)
        )
        if not present:
            result.extend([flag, value])
    return result

def build_toolbox_create_cmd(
    toolbox_cmd: str,
    engine: str,
    name: str,
    image: str,
    args: list[str],
    rdma_path: str = "/dev/infiniband",
) -> list[str]:
    wrapper = os.path.basename(toolbox_cmd)

    if wrapper == "toolbox":
        if engine != "podman":
            raise RuntimeError("Toolbx requires Podman; use Distrobox with Docker.")
        # Current Toolbx does not expose a supported container-argument
        # passthrough. It already creates a privileged container, shares /dev,
        # disables SELinux separation, and inherits host ulimits.
        return [toolbox_cmd, "create", "--image", image, name]

    if wrapper != "distrobox":
        raise RuntimeError(f"Unsupported interactive container wrapper: {toolbox_cmd}")

    resolved_args = remove_group_add_values(args, {"sudo"})
    rdma_args = get_interactive_rdma_args(toolbox_cmd, engine, rdma_path)
    resolved_args = extend_missing_option_pairs(resolved_args, rdma_args)
    resolved_args = upgrade_groups_for_podman(engine, resolved_args)
    resolved_args = use_host_group_ids_for_docker(engine, resolved_args)

    full_cmd = [toolbox_cmd, "create", "--name", name, "--image", image]
    if resolved_args:
        full_cmd.extend(["--additional-flags", shlex.join(resolved_args)])
    return full_cmd

def detect_engines() -> list[str]:
    engines = []
    if shutil.which("podman"):
        engines.append("podman")
    if shutil.which("docker"):
        engines.append("docker")
    return engines

def _get_host_os_ids() -> set[str]:
    ids = set()
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            for line in f:
                key, separator, value = line.partition("=")
                if not separator or key.lower() not in ("id", "id_like"):
                    continue
                ids.update(value.strip().strip("\"'").lower().split())
    return ids

def _preferred_distrobox_engine(engines: list[str]) -> str:
    configured = os.environ.get("DBX_CONTAINER_MANAGER", "")
    configured = os.path.basename(configured)
    if configured in engines:
        return configured
    if "podman" in engines:
        return "podman"
    if "docker" in engines:
        return "docker"
    return ""

def get_toolbox_backend() -> tuple[str, str]:
    """Return the compatible interactive wrapper and its container engine."""
    engines = detect_engines()
    distrobox_engine = _preferred_distrobox_engine(engines)
    has_toolbox = bool(shutil.which("toolbox") and "podman" in engines)
    has_distrobox = bool(shutil.which("distrobox") and distrobox_engine)
    prefers_distrobox = bool(
        _get_host_os_ids().intersection({"ubuntu", "debian", "arch"})
    )

    # An explicit Distrobox engine selection takes priority when possible.
    configured = os.path.basename(os.environ.get("DBX_CONTAINER_MANAGER", ""))
    if configured in engines and has_distrobox:
        return "distrobox", configured

    if prefers_distrobox:
        if has_distrobox:
            return "distrobox", distrobox_engine
        if has_toolbox:
            return "toolbox", "podman"
    else:
        if has_toolbox:
            return "toolbox", "podman"
        if has_distrobox:
            return "distrobox", distrobox_engine

    return "", ""

def get_toolbox_engine() -> str:
    return get_toolbox_backend()[1]

def get_os_toolbox_cmd() -> str:
    wrapper, engine = get_toolbox_backend()
    if wrapper == "distrobox":
        os.environ["DBX_CONTAINER_MANAGER"] = engine
    return wrapper

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
                            # Keep the complete timestamp for update comparisons. The UI
                            # truncates it to a date when displaying it.
                            created = parts[3].strip()
                        
                        # Normalize by stripping docker.io/ prefix for robust matching
                        r_norm = registry_match.replace("docker.io/", "") if registry_match else ""
                        i_norm = image.replace("docker.io/", "")
                        if r_norm and r_norm in i_norm:
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
    cmd, engine = get_toolbox_backend()
    if not cmd or not engine:
        raise RuntimeError(
            "No compatible interactive container backend found. "
            "Install Podman with Toolbx, or install Distrobox with Podman/Docker."
        )
    if os.path.basename(cmd) == "distrobox":
        os.environ["DBX_CONTAINER_MANAGER"] = engine

    if os.path.isdir("/dev/infiniband"):
        if os.path.basename(cmd) == "distrobox":
            print(f"🔎 InfiniBand/RDMA detected — enabling RDMA for Distrobox with {engine}.")
        else:
            print("🔎 InfiniBand/RDMA detected — using Toolbx host device and ulimit integration.")
    else:
        print("ℹ️  No InfiniBand devices detected — RDMA not enabled.")
    
    # Pull first
    subprocess.run([engine, "pull", image], check=True)
    
    full_cmd = build_toolbox_create_cmd(cmd, engine, name, image, args)
    subprocess.run(full_cmd, check=True)

def delete_toolbox(name: str):
    cmd, engine = get_toolbox_backend()
    if not cmd or not engine:
        raise RuntimeError("No compatible interactive container backend found.")
    if os.path.basename(cmd) == "distrobox":
        os.environ["DBX_CONTAINER_MANAGER"] = engine
    subprocess.run([cmd, "rm", "-f", name], check=True)

def enter_toolbox(name: str):
    cmd, engine = get_toolbox_backend()
    if not cmd or not engine:
        raise RuntimeError("No compatible interactive container backend found.")
    if os.path.basename(cmd) == "distrobox":
        os.environ["DBX_CONTAINER_MANAGER"] = engine
    subprocess.call([cmd, "enter", name])

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

def _parse_timestamp(value: str) -> datetime | None:
    """Parse ISO and container-engine timestamps into timezone-aware datetimes."""
    if not value:
        return None

    normalized = value.strip()
    # Docker/Podman may append a timezone abbreviation after the numeric offset.
    normalized = re.sub(r"\s+[A-Za-z]{2,5}$", "", normalized)
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def is_remote_image_newer(remote_updated: str, container_created: str) -> bool:
    """Return whether a registry image was updated after a container was created."""
    remote_time = _parse_timestamp(remote_updated)
    created_time = _parse_timestamp(container_created)
    return bool(remote_time and created_time and remote_time > created_time)
