import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_validate_image_integrity_counts_legacy_chart_placeholders(self):
        content = """<!-- 图表占位符：图4-1 用户登录流程图 -->
> **[图表占位符]** 展示用户登录流程
<!-- 图表占位符结束 -->
"""

        integrity = self.generator.validate_image_integrity(content)

        self.assertEqual(integrity["remaining_placeholders"], 1)


if __name__ == "__main__":
    unittest.main()
