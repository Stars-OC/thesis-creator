import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from chart_generator import ChartGenerator, main
from logger import ThesisLogger, init_logger


class ChartGeneratorMarkdownReplaceTest(unittest.TestCase):
    def setUp(self):
        ThesisLogger._instance = None
        ThesisLogger._initialized = False
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = self.tmp / "thesis-workspace"
        self.workspace.mkdir()
        self.output_dir = self.workspace / "final" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = init_logger(workspace_path=str(self.workspace))
        self.generator = ChartGenerator(output_dir=str(self.output_dir))
        self.generator.logger = self.logger

    def tearDown(self):
        logger = ThesisLogger._instance
        if logger is not None and hasattr(logger, "logger"):
            for handler in list(logger.logger.handlers):
                handler.close()
                logger.logger.removeHandler(handler)
        ThesisLogger._instance = None
        ThesisLogger._initialized = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_replace_image_placeholders_updates_markdown_manifest_and_logs(self):
        image_file = self.output_dir / "图4-1_系统总体架构图.png"
        image_file.write_bytes(b"a" * 2048)
        content = "系统总体设计如 [image_1] 所示。"
        manifest_items = [
            {
                "id": "image_1",
                "title": "图4-1 系统总体架构图",
                "source": "ai",
                "description": "展示系统整体架构",
                "output_path": "images/图4-1_系统总体架构图.png",
                "status": "pending",
            }
        ]

        replaced = self.generator.replace_image_placeholders(content, manifest_items)

        self.assertIn("![图4-1 系统总体架构图](images/图4-1_系统总体架构图.png)", replaced)
        self.assertEqual(manifest_items[0]["status"], "inserted")
        self.assertEqual(manifest_items[0]["output_path"], "images/图4-1_系统总体架构图.png")

        replacement_log = self.workspace / "logs" / self.logger.session_name / "replacements.jsonl"
        self.assertTrue(replacement_log.exists())
        payloads = [json.loads(line) for line in replacement_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(payloads[0]["operation"], "placeholder_replace")
        self.assertEqual(payloads[0]["step"], 8)
        self.assertEqual(payloads[0]["before"], "[image_1]")
        self.assertIn("images/图4-1_系统总体架构图.png", payloads[0]["after"])

    def test_replace_image_placeholders_requires_existing_image_file(self):
        content = "系统总体设计如 [image_1] 所示。"
        manifest_items = [
            {
                "id": "image_1",
                "title": "图4-1 系统总体架构图",
                "source": "user",
                "description": "展示系统整体架构",
                "output_path": "images/图4-1_系统总体架构图.png",
                "status": "pending",
            }
        ]

        with self.assertRaisesRegex(ValueError, "image_1"):
            self.generator.replace_image_placeholders(content, manifest_items)

    def test_replace_image_placeholders_generates_missing_ai_image(self):
        content = "系统总体设计如 [image_1] 所示。"
        manifest_items = [
            {
                "id": "image_1",
                "title": "图4-1 用户登录流程图",
                "source": "ai",
                "description": "1. 输入账号密码 2. 校验格式 3. 查询用户 4. 返回结果",
                "output_path": "images/图4-1_用户登录流程图.png",
                "status": "pending",
            }
        ]

        replaced = self.generator.replace_image_placeholders(content, manifest_items)

        image_path = self.output_dir / "图4-1_用户登录流程图.png"
        self.assertTrue(image_path.exists())
        self.assertGreater(image_path.stat().st_size, 1024)
        self.assertIn("![图4-1 用户登录流程图](images/图4-1_用户登录流程图.png)", replaced)
        self.assertEqual(manifest_items[0]["status"], "inserted")

    def test_replace_image_placeholders_preserves_manifest_subdirectory_path(self):
        content = "系统总体设计如 [image_1] 所示。"
        manifest_items = [
            {
                "id": "image_1",
                "title": "图4-3 用户登录流程图",
                "source": "ai",
                "description": "1. 输入账号密码 2. 校验格式 3. 查询用户 4. 返回结果",
                "output_path": "images/subdir/图4-3_用户登录流程图.png",
                "status": "pending",
            }
        ]

        replaced = self.generator.replace_image_placeholders(content, manifest_items)

        image_path = self.output_dir / "subdir" / "图4-3_用户登录流程图.png"
        self.assertTrue(image_path.exists())
        self.assertGreater(image_path.stat().st_size, 1024)
        self.assertIn("![图4-3 用户登录流程图](images/subdir/图4-3_用户登录流程图.png)", replaced)

    def test_replace_image_placeholders_rejects_unsupported_ai_chart_type(self):
        content = "系统总体设计如 [image_1] 所示。"
        manifest_items = [
            {
                "id": "image_1",
                "title": "图4-4 系统架构图",
                "source": "ai",
                "description": "展示系统总体架构与模块关系",
                "output_path": "images/图4-4_系统架构图.png",
                "status": "pending",
            }
        ]

        with self.assertRaisesRegex(ValueError, "系统架构图"):
            self.generator.replace_image_placeholders(content, manifest_items)

    def test_main_generates_missing_ai_image_from_manifest_workflow(self):
        markdown_path = self.workspace / "generated.md"
        markdown_path.write_text("登录流程如 [image_1] 所示。", encoding="utf-8")
        manifest_dir = self.workspace / "references"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "images.yaml"
        manifest_path.write_text(
            "images:\n  - id: image_1\n    title: 图4-2 用户登录流程图\n    source: ai\n    description: 1. 输入账号密码 2. 校验格式 3. 查询用户 4. 返回结果\n    output_path: images/图4-2_用户登录流程图.png\n",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", [
            "chart_generator.py",
            str(markdown_path),
            "--output",
            str(self.output_dir),
        ]):
            main()

        generated_image = self.output_dir / "图4-2_用户登录流程图.png"
        updated = markdown_path.read_text(encoding="utf-8")
        self.assertTrue(generated_image.exists())
        self.assertGreater(generated_image.stat().st_size, 1024)
        self.assertIn("![图4-2 用户登录流程图](images/图4-2_用户登录流程图.png)", updated)
        self.assertNotIn("[image_1]", updated)

