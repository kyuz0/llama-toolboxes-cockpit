import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import is_rocmfpx_ref
from src.server_runner import build_server_cmd


class RocmFpxRefTest(unittest.TestCase):
    def test_rocmfp4_spelling_matches(self):
        self.assertTrue(is_rocmfpx_ref("raulvidis/Ling-3.0-flash-ROCmFP4-STRIX-MTP-GGUF"))

    def test_rocmfpx_spelling_matches(self):
        self.assertTrue(is_rocmfpx_ref("kyuz0/amd-strix-halo-toolboxes:rocm-7.2.4-rocmfpx"))
        self.assertTrue(is_rocmfpx_ref("kyuz0/amd-strix-halo-toolboxes:vulkan-rocmfpx"))

    def test_non_rocmfpx_values_do_not_match(self):
        self.assertFalse(is_rocmfpx_ref("kyuz0/amd-strix-halo-toolboxes:rocm-7.14"))
        self.assertFalse(is_rocmfpx_ref("kyuz0/amd-strix-halo-toolboxes:vulkan-radv"))
        self.assertFalse(is_rocmfpx_ref(""))
        self.assertFalse(is_rocmfpx_ref(None))


class RocmFpxServerCommandTest(unittest.TestCase):
    def _build(self, image: str):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model.gguf"
            model.touch()
            with patch("src.model_manager.get_models_dir", return_value=Path(temporary)):
                return build_server_cmd(
                    engine="podman",
                    image=image,
                    model_path=str(model),
                    context_size=65536,
                    use_fa=False,
                    use_no_mmap=False,
                    custom_args="",
                    platform_id="strix-halo",
                    engine_args=[],
                )

    def test_rocmfpx_toolbox_tag_gets_fpx_env(self):
        cmd = self._build("kyuz0/amd-strix-halo-toolboxes:rocm-7.2.4-rocmfpx")
        self.assertIn("HSA_OVERRIDE_GFX_VERSION=11.5.1", cmd)
        self.assertIn("GGML_HIP_ENABLE_UNIFIED_MEMORY=1", cmd)

    def test_rocmfp4_spelling_image_gets_fpx_env(self):
        cmd = self._build("kyuz0/amd-strix-halo-toolboxes:rocm-7.2.4-rocmfp4")
        self.assertIn("HSA_OVERRIDE_GFX_VERSION=11.5.1", cmd)
        self.assertIn("GGML_HIP_ENABLE_UNIFIED_MEMORY=1", cmd)

    def test_plain_rocm_image_does_not_get_fpx_env(self):
        cmd = self._build("kyuz0/amd-strix-halo-toolboxes:rocm-7.14")
        self.assertNotIn("HSA_OVERRIDE_GFX_VERSION=11.5.1", cmd)
        self.assertNotIn("GGML_HIP_ENABLE_UNIFIED_MEMORY=1", cmd)


if __name__ == "__main__":
    unittest.main()
