# Llama Toolboxes Cockpit

A modern Terminal User Interface (TUI) for managing Llama.cpp toolbox containers and GGUF models across multiple AMD GPU platforms.

<!-- TODO: Replace with actual recording -->
![Llama Cockpit Demo](demo.gif)

## Supported Platforms

| Platform | GPU Architecture | Resources |
| :--- | :--- | :--- |
| **AMD Strix Halo** | Ryzen AI Max (gfx1151) | [Website](https://strix-halo-toolboxes.com) · [GitHub](https://github.com/kyuz0/amd-strix-halo-toolboxes) · [Docker Hub](https://hub.docker.com/r/kyuz0/amd-strix-halo-toolboxes) |
| **AMD Radeon R9700** | Radeon AI PRO R9700 (gfx1201) | [GitHub](https://github.com/kyuz0/amd-r9700-ai-toolboxes) · [Docker Hub](https://hub.docker.com/r/kyuz0/amd-r9700-toolboxes) |

Each platform ships its own set of pre-built containers (ROCm + Vulkan backends). The cockpit lets you switch between platforms on the fly — the active choice is persisted across sessions.

## Features

- **Multi-Platform Support**: Switch between AMD hardware platforms from the banner. Each platform has its own registry, toolbox images, and backend configurations.
- **Interactive Toolboxes**: Create, enter, update, or batch-delete Llama.cpp CLI containers via `toolbox` (Fedora/RHEL) or `distrobox` (Ubuntu/Arch). The cockpit auto-detects your OS.
- **Server Mode**: Launch a Llama.cpp OpenAI-compatible inference server directly from a container image — pick engine, image, model, context size, and extra args from the UI.
- **Model Manager**: Scan your local `~/models` directory for GGUF files, download curated models from Hugging Face, and manage sharded multi-file models.
- **Update Checker**: Check Docker Hub for newer image builds and batch-update toolboxes in one action.

## Installation

Install via `pipx` for an isolated environment:

```bash
# If you don't have pipx installed:
# Ubuntu/Debian: sudo apt install pipx
# Fedora: sudo dnf install pipx
# Arch: sudo pacman -S python-pipx

pipx install git+https://github.com/dzltron/llama-toolboxes-cockpit.git
```

## Usage

```bash
llama-cockpit
```

### Configuration

User preferences are stored in `~/.llama-cockpit.conf`:

```json
{
    "active_platform": "strix-halo",
    "models_dir": "~/models"
}
```

### Adding a New Platform

To add support for a new GPU platform, add a new entry to `src/assets/toolboxes.json` under the `platforms` array:

```json
{
  "id": "my-platform",
  "name": "My GPU Platform",
  "description": "Short description of the hardware",
  "registry": "docker.io/username/my-toolboxes",
  "groups": [
    {
      "name": "Official Toolboxes",
      "toolboxes": [
        {
          "name": "my-llama-rocm-7.2.2",
          "tag": "rocm-7.2.2",
          "description": "ROCm 7.2.2 backend",
          "engine_args": ["--device", "/dev/dri", "..."]
        }
      ]
    }
  ]
}
```

No code changes required — the cockpit picks up new platforms automatically.
