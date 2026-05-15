from pathlib import Path
from typing import Optional

import yaml


def load_format_config(config_path: Optional[str] = None) -> dict:
    default = {
        "table_font": "黑体",
        "image_width": 12,
        "max_image_width": 14,
        "max_image_height": 18,
    }

    candidates = []
    if config_path:
        candidates.append(Path(config_path))

    candidates.extend([
        Path.cwd() / "thesis-workspace" / ".thesis-config.yaml",
        Path.cwd() / ".thesis-config.yaml",
        Path(__file__).resolve().parents[4] / "thesis-workspace" / ".thesis-config.yaml",
    ])

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                export_cfg = data.get("export", {})
                if isinstance(export_cfg, dict):
                    default.update({k: v for k, v in export_cfg.items() if v is not None})
                format_cfg = data.get("format", {})
                if isinstance(format_cfg, dict):
                    default.update({k: v for k, v in format_cfg.items() if v is not None})
                return default
        except Exception:
            continue

    return default


FORMAT_CONFIG = load_format_config()
