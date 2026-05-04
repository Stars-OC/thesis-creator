import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from chart_generator import ChartGenerator


class ChartGeneratorImageValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.output_dir = self.base_dir / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = ChartGenerator(output_dir=str(self.output_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_image_integrity_counts_remaining_image_placeholders(self):
        content = "保留占位符 [image_1]，并且已经插入 ![图4-2](images/image_2.png)"
        (self.output_dir / "image_2.png").write_bytes(b"a" * 2048)

        integrity = self.generator.validate_image_integrity(content)

        self.assertEqual(integrity["remaining_placeholders"], 1)
        self.assertEqual(integrity["referenced_images"], 1)
        self.assertEqual(integrity["missing_files"], 0)

    def test_validate_image_integrity_counts_chapter_prefixed_placeholders(self):
        content = "保留占位符 [image_4_1]，并且已经插入 ![图4-2](images/image_2.png)"
        (self.output_dir / "image_2.png").write_bytes(b"a" * 2048)

        integrity = self.generator.validate_image_integrity(content)

        self.assertEqual(integrity["remaining_placeholders"], 1)
        self.assertEqual(integrity["referenced_images"], 1)
        self.assertEqual(integrity["missing_files"], 0)

    def test_validate_image_integrity_counts_legacy_chart_placeholders(self):
        content = """<!-- 图表占位符：图4-1 用户登录流程图 -->
> **[图表占位符]** 展示用户登录流程
<!-- 图表占位符结束 -->
"""

        integrity = self.generator.validate_image_integrity(content)

        self.assertEqual(integrity["remaining_placeholders"], 1)


    def test_replace_image_placeholders_keeps_pending_user_screenshots(self):
        content = "第5章界面占位 [image_5_1] 待用户补图。"
        manifest_items = [{
            "id": "image_5_1",
            "title": "知识库管理界面截图",
            "source": "user",
            "diagram_type": "screenshot",
            "status": "pending_user",
            "description": "用户后续补充系统实际运行截图",
        }]

        updated = self.generator.replace_image_placeholders(content, manifest_items)

        self.assertEqual(content, updated)
        self.assertIn("[image_5_1]", updated)


if __name__ == "__main__":
    unittest.main()
