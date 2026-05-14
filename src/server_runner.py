import os
from .model_manager import resolve_model_path

import shlex

def build_server_cmd(engine: str, image: str, model_path: str, context_size: int, use_fa: bool, use_no_mmap: bool, custom_args: str, host: str = "localhost", port: str = "8080") -> list[str]:
    models_dir = os.path.expanduser("~/models")
    
    cmd = [
        engine, "run", "--rm", "-it",
        "--device", "/dev/dri",
        "--device", "/dev/kfd",
        "--group-add", "video",
        "--group-add", "render",
        "--security-opt", "seccomp=unconfined"
    ]
    
    # Podman requires these flags to read host volumes without permission issues (SELinux / UID mapping)
    if engine == "podman":
        cmd.extend([
            "--security-opt", "label=disable",
            "--userns=keep-id"
        ])
        
    port_mapping = f"{port}:{port}"
    if host and host != "0.0.0.0":
        bind_ip = "127.0.0.1" if host == "localhost" else host
        port_mapping = f"{bind_ip}:{port}:{port}"

    cmd.extend([
        "-v", f"{models_dir}:/models:ro",
        "-p", port_mapping,
        image
    ])
    
    # Resolve first file if sharded
    actual_file = resolve_model_path(model_path)
    
    # Calculate the inner path based on relative position
    rel_path = os.path.relpath(actual_file, models_dir)
    inner_model_path = f"/models/{rel_path}"

    cmd.extend([
        "llama-server",
        "-m", inner_model_path,
        "-c", str(context_size),
        "--host", "0.0.0.0",
        "--port", str(port)
    ])
    
    if use_no_mmap:
        cmd.append("--no-mmap")
        
    if use_fa:
        cmd.extend(["-fa", "1"])
        
    if custom_args:
        cmd.extend(shlex.split(custom_args))
    
    return cmd
