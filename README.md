# Llama Toolboxes Cockpit

A modern Terminal User Interface (TUI) for managing Llama.cpp toolbox containers and GGUF models across multiple AMD GPU platforms.

<!-- TODO: Replace with actual recording -->
![Llama Cockpit Demo](demo.gif)

## Supported Platforms

| Platform | GPU Architecture | Resources |
| :--- | :--- | :--- |
| **AMD Strix Halo** | Ryzen AI Max (gfx1151) | [Website](https://strix-halo-toolboxes.com) · [GitHub](https://github.com/kyuz0/amd-strix-halo-toolboxes) · [Docker Hub](https://hub.docker.com/r/kyuz0/amd-strix-halo-toolboxes) |
| **AMD Radeon R9700** | Radeon AI PRO R9700 (gfx1201) | [GitHub](https://github.com/kyuz0/amd-r9700-ai-toolboxes) · [Docker Hub](https://hub.docker.com/r/kyuz0/amd-r9700-toolboxes) |
| **Intel Arc B70** | Intel Xe-HPG / Battlemage | [GitHub](https://github.com/kyuz0/intel-b70-ai-toolboxes) · [Docker Hub](https://hub.docker.com/r/kyuz0/intel-b70-ai-toolboxes) |

Each platform ships its own set of pre-built containers (ROCm + Vulkan backends). The cockpit lets you switch between platforms on the fly — the active choice is persisted across sessions.

## Features

- **Multi-Platform Support**: Switch between AMD hardware platforms from the banner. Each platform has its own registry, toolbox images, and backend configurations.
- **Interactive Toolboxes**: Create, enter, update, or batch-delete Llama.cpp CLI containers via `toolbox` (Fedora/RHEL) or `distrobox` (Ubuntu/Arch). The cockpit auto-detects your OS.
- **Server Mode**: Launch a Llama.cpp OpenAI-compatible inference server directly from a container image — pick engine, image, model, context size, and extra args from the UI.
- **RDMA/RoCE**: Detect InfiniBand devices for Strix Halo Toolbx and native Podman/Docker server runs.
- **Benchmark Mode**: Measure fixed prefill and generation workloads at identical configurable starting KV depths, saving raw `llama-bench` JSONL and a combined CSV.
- **Model Manager**: Scan your local `~/models` directory for GGUF files, download curated models from Hugging Face, and manage sharded multi-file models.
- **Update Checker**: Check Docker Hub for newer image builds and batch-update toolboxes in one action.

## Installation

Install via `pipx` for an isolated environment:

```bash
# If you don't have pipx installed:
# Ubuntu/Debian: sudo apt install pipx
# Fedora: sudo dnf install pipx
# Arch: sudo pacman -S python-pipx

pipx install git+https://github.com/kyuz0/llama-toolboxes-cockpit.git
```

## Usage

```bash
llama-cockpit
```

### Benchmark methodology

Benchmark mode produces a long-context throughput profile rather than a single
headline score. Here, **depth** means the number of tokens already present in
the KV cache, not model-layer depth.

For every selected model and toolbox, the cockpit runs two `llama-bench`
series over the same configurable starting KV depths:

| Series | Starting state | Timed workload | Default measured span |
| :--- | :--- | :--- | :--- |
| Prefill | `d` tokens already cached | Append a 2,048-token prompt chunk | `d` to `d + 2,048` |
| Generation | `d` tokens already cached | Decode 128 tokens sequentially | `d` to `d + 128` |

With the defaults, `d` is `0, 8192, 16384, ..., 65536`, and each point is
measured three times. `llama-bench` fills or restores the KV cache to `d`
before starting the timer, so that setup work is excluded. A prefill point at
32K therefore answers "how quickly can the next 2,048 prompt tokens be
processed after 32K tokens are already cached?" It does not measure the time
needed to ingest the first 32K tokens. Likewise, a generation point at 32K is
the average throughput while decoding the following 128 tokens.

Plot `starting_depth` on the x-axis and `avg_ts` (average tokens per second) on
the y-axis, with separate lines for `prefill` and `generation`. These curves
show how prompt ingestion and sequential decoding change as the KV cache grows.
The CSV also includes `stddev_ts` and the individual `samples_ts` values.

The benchmark uses synthetic token IDs and measures model execution only. It
does not include model loading, tokenization, sampling, server or network
overhead, streaming, concurrency, or output quality, so it should not be read
as end-to-end chat latency. Also note that the maximum setting is a **starting**
depth: with the defaults, the deepest prefill point ends at 67,584 tokens and
the deepest generation point ends at 65,664 tokens.

Raw results are saved as one JSONL file per model, toolbox, and series. The
cockpit combines them into `curve_summary.csv`; it does not render the graph
itself. Existing non-empty result files are skipped, so use a fresh results
directory when changing depths, workload sizes, repetitions, or extra
`llama-bench` arguments.

### Configuration

User preferences are stored in `~/.llama-cockpit.conf`:

```json
{
    "active_platform": "strix-halo",
    "models_dir": "~/models",
    "benchmark_results_dir": "~/llamacpp_toolboxes_bench_results"
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
