# -*- coding: utf-8 -*-
"""
chart_renderer 报告与回写验证测试

覆盖点：
1. render_report 需要识别缺失文件与小于等于 1KB 的 PNG
2. update_markdown 回写后，图片路径应可被报告统计为已引用
"""

import sys
import tempfile
import unittest
from pathlib import Path


scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from chart_renderer import ChartRenderer  # noqa: E402


class DummyLogger:
    def info(self, *args, **kwargs):
        """info"""
        pass

    def warning(self, *args, **kwargs):
        """warning"""
        pass

    def error(self, *args, **kwargs):
        """error"""
        pass


class ChartRendererReportTestCase(unittest.TestCase):
    def test_generate_report_marks_missing_and_small_png(self):
        """test_generate_report_marks_missing_and_small_png"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            renderer = ChartRenderer(output_dir=str(output_dir))
            renderer.logger = DummyLogger()
            renderer.charts = [
                {"id": "图4-1", "start": 0, "end": 0},
                {"id": "图4-2", "start": 0, "end": 0},
            ]
            renderer.rendered_count = 1
            renderer.failed_count = 1

            (output_dir / "图4-1.png").write_bytes(b"x" * 2048)
            (output_dir / "图4-2.png").write_bytes(b"x" * 128)

            report = renderer.generate_report()

            self.assertIn("- 渲染成功: 1", report)
            self.assertIn("- 渲染失败: 1", report)
            self.assertIn("| 图4-1 | [OK] | 图4-1.png |", report)
            self.assertIn("| 图4-2 | [WARN] | 图4-2.png (<=1KB) |", report)

    def test_update_markdown_replaces_code_block_with_image_ref(self):
        """test_update_markdown_replaces_code_block_with_image_ref"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "images"
            output_dir.mkdir(parents=True, exist_ok=True)

            renderer = ChartRenderer(output_dir=str(output_dir))
            renderer.logger = DummyLogger()
            content = """```mermaid
%% 图4-1 系统架构图
graph TD
A-->B
```
"""
            renderer.parse_mermaid_blocks(content)

            output_file = output_dir / "图4-1.png"
            output_file.write_bytes(b"x" * 2048)

            updated = renderer.update_markdown(content, {"图4-1": output_file}, output_dir.parent)

            self.assertIn("![图4-1](images/图4-1.png)", updated)
            self.assertNotIn("```mermaid", updated)


if __name__ == "__main__":
    unittest.main()
