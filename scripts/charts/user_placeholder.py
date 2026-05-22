# -*- coding: utf-8 -*-
"""
用户图片占位生成器（User Image Placeholder Generator）

当 images.yaml 中 source=user 的图片尚未由用户提供真实文件时，
本脚本生成白底"请由用户提供"占位 PNG，避免 Step 9 导出 Word 时缺图。

>>> 重要：占位图仅作为可视化提示，正式交付前必须替换为真实截图！

使用方法：
    # 为单张图片生成占位
    python scripts/charts/user_placeholder.py --output workspace/final/images/image_1.png --title "系统整体架构图"

    # 批量为 images.yaml 中所有 source=user 且 render_status != rendered 的图片生成占位
    python scripts/charts/user_placeholder.py --manifest workspace/references/images.yaml --root .

    # 只生成未存在 PNG 的占位（已有真实图片不覆盖）
    python scripts/charts/user_placeholder.py --manifest workspace/references/images.yaml --root . --skip-existing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

try:
    from .schemas import ImageItem, load_manifest
except ImportError:
    from schemas import ImageItem, load_manifest


def _try_load_font(size: int):
    """尝试加载常见中文字体；找不到时退化为 PIL 默认字体。"""
    from PIL import ImageFont

    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size=size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_placeholder(output: Path, title: str = "请由用户提供", subtitle: str = "", width: int = 1280, height: int = 720) -> None:
    """生成白底、中文占位 PNG。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装，请运行: pip install Pillow") from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 边框
    border_color = (200, 200, 200)
    draw.rectangle([(8, 8), (width - 8, height - 8)], outline=border_color, width=3)

    # 主标题
    title_font = _try_load_font(48)
    subtitle_font = _try_load_font(28)
    hint_font = _try_load_font(22)

    def _draw_centered(text: str, font, y: int, color=(80, 80, 80)) -> None:
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width = draw.textsize(text, font=font)[0]
        draw.text(((width - text_width) // 2, y), text, fill=color, font=font)

    main_text = title or "请由用户提供"
    _draw_centered(main_text, title_font, height // 2 - 80, color=(60, 60, 60))

    if subtitle:
        _draw_centered(subtitle, subtitle_font, height // 2 - 10, color=(120, 120, 120))

    _draw_centered("（此为占位图，正式交付前请替换为真实截图）", hint_font, height // 2 + 60, color=(160, 160, 160))

    image.save(output, format="PNG")


def _is_user_image(item: ImageItem) -> bool:
    return (item.source or "").strip().lower() == "user"


def batch_generate(manifest_path: Path, root: Path, skip_existing: bool = True) -> List[Path]:
    """根据 images.yaml 批量生成所有用户图片占位。"""
    items = load_manifest(manifest_path)
    generated: List[Path] = []
    for item in items:
        if not _is_user_image(item):
            continue
        if not item.output_file:
            continue
        output = root / item.output_file if not Path(item.output_file).is_absolute() else Path(item.output_file)
        if skip_existing and output.exists():
            continue
        subtitle = f"{item.chapter or ''} {item.section or ''}".strip()
        generate_placeholder(output, title=item.title or item.id, subtitle=subtitle)
        generated.append(output)
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="生成用户图片占位 PNG")
    parser.add_argument("--output", help="单图模式：输出 PNG 路径")
    parser.add_argument("--title", default="请由用户提供", help="单图模式：占位标题")
    parser.add_argument("--subtitle", default="", help="单图模式：占位副标题")
    parser.add_argument("--manifest", help="批量模式：images.yaml 路径")
    parser.add_argument("--root", default=".", help="批量模式：解析相对路径的根目录")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="批量模式：已存在 PNG 时跳过（默认开启）")
    parser.add_argument("--force-overwrite", action="store_true", help="批量模式：强制覆盖已有 PNG")
    args = parser.parse_args()

    if args.manifest:
        skip = not args.force_overwrite
        generated = batch_generate(Path(args.manifest), Path(args.root), skip_existing=skip)
        print(f"[OK] 批量占位生成完成，共 {len(generated)} 张：")
        for path in generated:
            print(f"  - {path}")
        return

    if args.output:
        generate_placeholder(Path(args.output), title=args.title, subtitle=args.subtitle)
        print(f"[OK] 已生成占位图: {args.output}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
