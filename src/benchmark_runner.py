import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import get_preferred_benchmark_ubatch
from .model_manager import resolve_model_path


@dataclass(frozen=True)
class BenchmarkSettings:
    prefill: str
    generation: str
    contexts: tuple[int | None, ...]
    flash_attention: bool = True
    use_mmap: bool = False
    kv_cache_type: str = ""
    standard_repetitions: int = 5
    long_repetitions: int = 3
    long_prefill: int = 2048
    long_generation: int = 32
    platform_id: str = ""
    rocm_ubatch: int | None = None
    vulkan_ubatch: int | None = None
    extra_args: str = ""


@dataclass(frozen=True)
class BenchmarkJob:
    toolbox_name: str
    model_path: str
    context: int | None
    command: tuple[str, ...]
    output_path: Path


def parse_positive_csv(raw: str, field_name: str) -> str:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values or any(not value.isdigit() or int(value) <= 0 for value in values):
        raise ValueError(f"{field_name} must contain positive integers separated by commas.")
    return ",".join(values)


def parse_contexts(raw: str) -> tuple[int | None, ...]:
    values = [value.strip().lower() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("Contexts must include 'default' or at least one positive integer.")

    contexts = []
    for value in values:
        if value == "default":
            context = None
        elif value.isdigit() and int(value) > 0:
            context = int(value)
        else:
            raise ValueError("Contexts must be 'default' or positive integers separated by commas.")
        if context not in contexts:
            contexts.append(context)
    return tuple(contexts)


def _toolbox_prefix(toolbox_command: str, toolbox_name: str) -> list[str]:
    if os.path.basename(toolbox_command) == "toolbox":
        return [toolbox_command, "run", "-c", toolbox_name, "--"]
    return [toolbox_command, "enter", toolbox_name, "--"]


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "benchmark"


def build_benchmark_jobs(
    toolbox_command: str,
    toolbox_names: list[str],
    model_paths: list[str],
    results_dir: Path,
    settings: BenchmarkSettings,
) -> list[BenchmarkJob]:
    jobs = []
    extra_args = shlex.split(settings.extra_args) if settings.extra_args else []

    for model_pattern in model_paths:
        model_path = resolve_model_path(model_pattern)
        model_name = _safe_filename_part(Path(model_path).stem)

        for toolbox_name in toolbox_names:
            toolbox_part = _safe_filename_part(toolbox_name)
            is_vulkan = "vulkan" in toolbox_name.lower()
            backend = "vulkan" if is_vulkan else "rocm"
            override = settings.vulkan_ubatch if is_vulkan else settings.rocm_ubatch
            ubatch = override or get_preferred_benchmark_ubatch(
                model_path, settings.platform_id, backend
            )

            for context in settings.contexts:
                command = _toolbox_prefix(toolbox_command, toolbox_name)
                command.extend([
                    "llama-bench",
                    "-ngl", "99",
                    "-mmp", "1" if settings.use_mmap else "0",
                    "-m", model_path,
                    "-fa", "1" if settings.flash_attention else "0",
                ])

                suffix = "__fa1" if settings.flash_attention else ""
                if settings.use_mmap:
                    suffix += "__mmap1"
                if settings.kv_cache_type:
                    suffix += f"__kv-{_safe_filename_part(settings.kv_cache_type)}"
                if ubatch:
                    command.extend(["-ub", str(ubatch)])
                    suffix += f"__ub{ubatch}"
                if context is None:
                    command.extend([
                        "-p", settings.prefill,
                        "-n", settings.generation,
                        "-r", str(settings.standard_repetitions),
                    ])
                else:
                    command.extend([
                        "-p", str(settings.long_prefill),
                        "-n", str(settings.long_generation),
                        "-d", str(context),
                        "-r", str(settings.long_repetitions),
                    ])
                    suffix += f"__longctx{context}"

                if settings.kv_cache_type:
                    command.extend([
                        "--cache-type-k", settings.kv_cache_type,
                        "--cache-type-v", settings.kv_cache_type,
                    ])

                command.extend(extra_args)
                output_path = results_dir / f"{model_name}__{toolbox_part}{suffix}.log"
                jobs.append(BenchmarkJob(
                    toolbox_name=toolbox_name,
                    model_path=model_path,
                    context=context,
                    command=tuple(command),
                    output_path=output_path,
                ))

    return jobs


def run_benchmark_job(job: BenchmarkJob) -> tuple[str, int | None]:
    if job.output_path.is_file() and job.output_path.stat().st_size > 0:
        return "skipped", None

    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(job.output_path, "w", encoding="utf-8") as output:
            result = subprocess.run(
                list(job.command),
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if result.returncode != 0:
                output.write(f"\nBenchmark exited with code {result.returncode}\n")
                return "failed", result.returncode
    except KeyboardInterrupt:
        if job.output_path.exists():
            job.output_path.unlink()
        raise
    except Exception:
        if job.output_path.exists() and job.output_path.stat().st_size == 0:
            job.output_path.unlink()
        raise

    return "completed", 0
