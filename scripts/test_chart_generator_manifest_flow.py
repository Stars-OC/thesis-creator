import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from chart_generator import ChartGenerator


class ChartGeneratorManifestFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.generator = ChartGenerator(output_dir=str(self.base_dir / "images"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_image_placeholders_extracts_image_ids_in_order(self):
        markdown = """
        第一张图见 [image_1]。
        第二张图见 [image_2]。
        再次引用 [image_1] 不应重复统计。
        """

        placeholders = self.generator.parse_image_placeholders(markdown)

        self.assertEqual(placeholders, ["image_1", "image_2"])

    def test_load_image_manifest_reads_yaml_records(self):
        manifest_path = self.base_dir / "references" / "images.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "images": [
                        {"id": "image_1", "title": "图4-1", "source": "ai", "description": "系统架构图"},
                        {"id": "image_2", "title": "图4-2", "source": "user", "description": "运行截图"},
                    ]
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        manifest = self.generator.load_image_manifest(manifest_path)

        self.assertEqual(manifest[0]["id"], "image_1")
        self.assertEqual(manifest[1]["source"], "user")

    def test_validate_image_manifest_raises_when_placeholder_missing_in_manifest(self):
        placeholders = ["image_1", "image_2"]
        manifest = [
            {"id": "image_1", "title": "图4-1", "source": "ai", "description": "系统架构图"}
        ]

        with self.assertRaisesRegex(ValueError, "image_2"):
            self.generator.validate_image_manifest(placeholders, manifest)

    def test_validate_image_manifest_requires_description_for_ai_source(self):
        placeholders = ["image_1"]
        manifest = [
            {"id": "image_1", "title": "图4-1", "source": "ai", "description": ""}
        ]

        with self.assertRaisesRegex(ValueError, "description"):
            self.generator.validate_image_manifest(placeholders, manifest)

    def test_validate_image_manifest_accepts_user_source_without_generation_fields(self):
        placeholders = ["image_1"]
        manifest = [
            {"id": "image_1", "title": "图4-1", "source": "user", "description": "用户提供截图"}
        ]

        validated = self.generator.validate_image_manifest(placeholders, manifest)

        self.assertEqual(validated[0]["source"], "user")


if __name__ == "__main__":
    unittest.main()
