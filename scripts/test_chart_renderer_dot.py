# -*- coding: utf-8 -*-

import os
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
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class ChartRendererDotTestCase(unittest.TestCase):
    def setUp(self):
        self.dot_bin = Path(r"D:/Program Files (x86)/Graphviz/bin")
        if self.dot_bin.exists():
            os.environ["PATH"] = str(self.dot_bin) + os.pathsep + os.environ.get("PATH", "")

    def test_parse_dot_blocks_extracts_chart_id(self):
        renderer = ChartRenderer(output_dir=str(Path(tempfile.gettempdir()) / "chart_renderer_dot"))
        renderer.logger = DummyLogger()
        content = """```dot
// 图4-21 用户概念ER图
graph ER {
  \"用户\" [shape=box];
}
```
"""

        charts = renderer.parse_dot_blocks(content)

        self.assertEqual(1, len(charts))
        self.assertEqual("图4-21", charts[0]["id"])
        self.assertEqual("dot", charts[0]["type"])

    def test_render_all_renders_dot_png_without_preconfigured_path(self):
        if not self.dot_bin.exists():
            self.skipTest("Graphviz dot.exe 未安装，跳过 DOT 渲染测试")

        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(
            segment for segment in original_path.split(os.pathsep)
            if "Graphviz" not in segment
        )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                renderer = ChartRenderer(output_dir=tmpdir)
                renderer.logger = DummyLogger()
                content = """```dot
// 图4-23 交易记录概念ER图
graph ER {
  rankdir=LR;
  splines=line;
  node [fontname=\"Microsoft YaHei\"];
  \"交易记录\" [shape=box];
  \"编号​1\" [shape=ellipse];
  \"编号​1\" -- \"交易记录\";
  \"金额​1\" [shape=ellipse];
  \"交易记录\" -- \"金额​1\";
}
```
"""

                results = renderer.render_all(content, method="auto")

                self.assertIn("图4-23", results)
                output_path = results["图4-23"]
                self.assertTrue(output_path.exists())
                self.assertGreater(output_path.stat().st_size, 1024)
        finally:
            os.environ["PATH"] = original_path



if __name__ == "__main__":
    unittest.main()
