import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.benchmark_runner import BenchmarkSettings, build_benchmark_jobs
from src.server_runner import build_server_cmd


class UbatchCommandsTest(unittest.TestCase):
    def test_benchmark_uses_calibrated_ubatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model.gguf"
            model.touch()
            with patch(
                "src.benchmark_runner.get_preferred_benchmark_ubatch",
                return_value=1024,
            ):
                jobs = build_benchmark_jobs(
                    "toolbox",
                    ["llama-rocm-7.14"],
                    [str(model)],
                    Path(temporary),
                    BenchmarkSettings(platform_id="strix-halo"),
                )
            self.assertEqual(len(jobs), 2)
            for job in jobs:
                index = job.command.index("-ub")
                self.assertEqual(job.command[index + 1], "1024")

    def test_server_uses_calibration_but_respects_explicit_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model.gguf"
            model.touch()
            kwargs = dict(
                engine="podman",
                image="docker.io/example/llama-rocm:latest",
                model_path=str(model),
                context_size=65536,
                use_fa=True,
                use_no_mmap=True,
                platform_id="strix-halo",
                engine_args=[],
            )
            with (
                patch("src.model_manager.get_models_dir", return_value=Path(temporary)),
                patch("src.server_runner.get_preferred_ubatch", return_value=1024),
            ):
                automatic = build_server_cmd(custom_args="", **kwargs)
                explicit = build_server_cmd(custom_args="-ub 256", **kwargs)

            auto_index = automatic.index("-ub")
            self.assertEqual(automatic[auto_index + 1], "1024")
            self.assertEqual(explicit.count("-ub"), 1)
            explicit_index = explicit.index("-ub")
            self.assertEqual(explicit[explicit_index + 1], "256")


if __name__ == "__main__":
    unittest.main()
