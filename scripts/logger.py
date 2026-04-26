# -*- coding: utf-8 -*-
"""
thesis-creator 日志工具模块

提供统一的日志记录功能，支持：
- 控制台输出（带颜色）
- 文件输出（logs/ 目录）
- 分级日志（DEBUG, INFO, WARNING, ERROR）
- 会话隔离（每次运行生成独立日志文件）
- 配置开关（thesis-workspace/.thesis-config.yaml）
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

MAX_LOG_FILE_SIZE = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 5


def _normalize_workspace_path(workspace_path: Optional[str]) -> Optional[Path]:
    """规范化工作区路径，兼容传入 thesis-workspace/workspace 的场景"""
    if not workspace_path:
        return None

    p = Path(workspace_path)
    if p.name == "workspace":
        return p.parent
    return p


def _load_config(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 thesis-workspace/.thesis-config.yaml 配置文件

    Returns:
        配置字典，如果文件不存在则返回默认配置
    """
    default_config = {
        'logging': {
            'enabled': True,
            'level': 'INFO',
            'console_level': 'INFO',
            'file_level': 'DEBUG'
        }
    }

    normalized_workspace = _normalize_workspace_path(workspace_path)

    # 搜索配置文件位置
    script_dir = Path(__file__).parent
    possible_paths = []

    if normalized_workspace:
        possible_paths.append(normalized_workspace / ".thesis-config.yaml")

    possible_paths.extend([
        Path.cwd() / "thesis-workspace" / ".thesis-config.yaml",
        script_dir.parent.parent.parent / "thesis-workspace" / ".thesis-config.yaml",
    ])

    for config_path in possible_paths:
        if config_path.exists():
            if YAML_AVAILABLE:
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config:
                            return config
                except Exception:
                    pass
            else:
                # yaml 未安装，尝试手动解析
                try:
                    content = config_path.read_text(encoding='utf-8')
                    # 简单解析 enabled 字段
                    if 'enabled: false' in content.lower():
                        default_config['logging']['enabled'] = False
                    return default_config
                except Exception:
                    pass

    return default_config


def _is_logging_enabled(workspace_path: Optional[str] = None) -> bool:
    """
    检查日志功能是否启用

    Returns:
        True 如果启用，False 如果禁用
    """
    config = _load_config(workspace_path=workspace_path)
    return config.get('logging', {}).get('enabled', True)


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class ThesisLogger:
    """论文创作系统日志管理器"""

    _instance: Optional['ThesisLogger'] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """单例模式，确保全局只有一个日志实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: int = logging.DEBUG,
        console_level: int = logging.INFO,
        session_name: Optional[str] = None
    ):
        """
        初始化日志管理器

        Args:
            log_dir: 日志文件目录
            log_level: 文件日志级别
            console_level: 控制台日志级别
            session_name: 会话名称（用于日志文件名）
        """
        if self._initialized:
            return

        self.log_dir = Path(log_dir)

        # 生成会话 ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name or f"thesis_session_{self.session_id}"

        # 创建日志记录器
        self.logger = logging.getLogger("thesis-creator")
        self.logger.setLevel(log_level)
        self.logger.handlers.clear()  # 清除已有处理器

        # 创建格式化器
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )

        # 控制台处理器（始终可用）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器（失败时优雅降级，仅保留控制台日志）
        log_file = self.log_dir / f"{self.session_name}.log"
        self.log_file = log_file
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=MAX_LOG_FILE_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.log_file = Path("disabled")
            self.logger.warning(f"日志目录不可写，已降级为仅控制台输出: {self.log_dir} | {e}")

        self._initialized = True

        # 写入会话开始标记
        self.logger.info("=" * 60)
        self.logger.info(f"Thesis-Creator Session Started")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Log File: {self.log_file}")
        self.logger.info("=" * 60)


    def debug(self, msg: str, *args, **kwargs):
        """记录调试信息"""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """记录一般信息"""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """记录警告信息"""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """记录错误信息"""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """记录严重错误"""
        self.logger.critical(msg, *args, **kwargs)

    def step(self, step_name: str, status: str = "start"):
        """
        记录工作流步骤

        Args:
            step_name: 步骤名称
            status: 状态 (start/complete/error)
        """
        status_icons = {
            'start': '[>]',
            'complete': '[OK]',
            'error': '[FAIL]',
            'skip': '[>>]'
        }
        icon = status_icons.get(status, '[*]')
        self.logger.info(f"{icon} Step: {step_name} [{status}]")

    def file_operation(self, operation: str, file_path: str, success: bool = True):
        """
        记录文件操作

        Args:
            operation: 操作类型 (read/write/create/delete)
            file_path: 文件路径
            success: 是否成功
        """
        status = "[OK]" if success else "[FAIL]"
        self.logger.info(f"{status} File {operation}: {file_path}")

    def chapter_progress(self, chapter: str, word_count: int, total_words: int):
        """
        记录章节进度

        Args:
            chapter: 章节名称
            word_count: 当前章节字数
            total_words: 总字数
        """
        self.logger.info(f"[章节] {chapter} 完成: {word_count} 字 | 累计: {total_words} 字")

    def quality_check(self, check_item: str, passed: bool, details: str = ""):
        """
        记录质量检查结果

        Args:
            check_item: 检查项
            passed: 是否通过
            details: 详细信息
        """
        status = "[PASS]" if passed else "[FAIL]"
        msg = f"[检查] {check_item}: {status}"
        if details:
            msg += f" | {details}"
        self.logger.info(msg)

    def error_with_context(self, error: Exception, context: dict):
        """
        记录带上下文的错误信息

        Args:
            error: 异常对象
            context: 上下文信息字典
        """
        self.logger.error(f"[ERROR] {type(error).__name__}: {error}")
        for key, value in context.items():
            self.logger.error(f"   └─ {key}: {value}")

    def get_log_content(self) -> str:
        """获取当前日志文件内容"""
        if self.log_file.exists():
            return self.log_file.read_text(encoding='utf-8')
        return ""

    def export_session_report(self, output_path: Optional[str] = None) -> str:
        """
        导出会话报告

        Args:
            output_path: 输出路径（可选）

        Returns:
            报告文件路径
        """
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# Thesis-Creator 会话报告

## 基本信息
- **会话 ID**: {self.session_id}
- **报告时间**: {report_time}
- **日志文件**: {self.log_file}

## 日志内容

```
{self.get_log_content()}
```

---
*此报告由 thesis-creator 自动生成*
"""

        if output_path is None:
            output_path = self.log_dir / f"report_{self.session_id}.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"[统计] 会话报告已导出: {output_path}")
        return str(output_path)


class NullLogger:
    """
    空日志类 - 当日志功能禁用时使用

    所有方法都是空操作，不产生任何输出
    节省上下文，提高性能
    """

    def __init__(self):
        self.session_id = "disabled"
        self.session_name = "null_logger"
        self.log_file = Path("disabled")
        self.log_dir = Path("disabled")

    def debug(self, msg: str, *args, **kwargs):
        pass

    def info(self, msg: str, *args, **kwargs):
        pass

    def warning(self, msg: str, *args, **kwargs):
        pass

    def error(self, msg: str, *args, **kwargs):
        pass

    def critical(self, msg: str, *args, **kwargs):
        pass

    def step(self, step_name: str, status: str = "start"):
        pass

    def file_operation(self, operation: str, file_path: str, success: bool = True):
        pass

    def chapter_progress(self, chapter: str, word_count: int, total_words: int):
        pass

    def quality_check(self, check_item: str, passed: bool, details: str = ""):
        pass

    def error_with_context(self, error: Exception, context: dict):
        pass

    def get_log_content(self) -> str:
        return ""

    def export_session_report(self, output_path: Optional[str] = None) -> str:
        return ""


# 全局日志实例
_logger: Optional[ThesisLogger] = None
_null_logger: Optional[NullLogger] = None


def _find_workspace_log_dir() -> Path:
    """
    自动查找 thesis-workspace/logs 目录

    搜索顺序：
    1. 当前工作目录下的 thesis-workspace/logs
    2. 脚本所在目录的上级 thesis-workspace/logs
    3. 用户项目根目录下的 thesis-workspace/logs

    Returns:
        找到的 logs 目录路径，如果未找到则返回当前目录下的 logs
    """
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # 可能的 thesis-workspace/logs 位置
    possible_paths = [
        Path.cwd() / "thesis-workspace" / "logs",  # 当前工作目录
        script_dir.parent.parent.parent / "thesis-workspace" / "logs",  # skill 目录的上级
        Path.cwd().parent / "thesis-workspace" / "logs",  # 当前目录的上级
    ]

    for path in possible_paths:
        # 检查 thesis-workspace 是否存在（不要求 logs 存在，会自动创建）
        workspace_dir = path.parent
        if workspace_dir.exists() and workspace_dir.name == "thesis-workspace":
            return path

    # 如果都找不到，返回默认路径
    return Path("logs")


def get_logger(
    log_dir: str = None,
    session_name: Optional[str] = None,
    use_workspace: bool = True,
    check_config: bool = True,
    workspace_path: Optional[str] = None
):
    """
    获取全局日志实例

    Args:
        log_dir: 日志目录（如果为 None 且 use_workspace=True，则自动检测 thesis-workspace/logs）
        session_name: 会话名称
        use_workspace: 是否优先使用 thesis-workspace/logs 目录
        check_config: 是否检查配置文件中的 enabled 开关（默认 True）
        workspace_path: 显式工作区路径（优先于自动检测）

    Returns:
        ThesisLogger 实例（如果启用）或 NullLogger 实例（如果禁用）
    """
    global _logger, _null_logger

    normalized_workspace = _normalize_workspace_path(workspace_path)

    # 检查配置是否启用日志
    if check_config and not _is_logging_enabled(workspace_path=str(normalized_workspace) if normalized_workspace else None):
        if _null_logger is None:
            _null_logger = NullLogger()
        return _null_logger

    if _logger is None:
        # 自动检测 log_dir
        if log_dir is None:
            if normalized_workspace:
                log_dir = str(normalized_workspace / "logs")
            elif use_workspace:
                log_dir = str(_find_workspace_log_dir())
            else:
                log_dir = "logs"
        _logger = ThesisLogger(log_dir=log_dir, session_name=session_name)
    return _logger


def init_logger(
    log_dir: str = None,
    session_name: Optional[str] = None,
    use_workspace: bool = True,
    check_config: bool = True,
    force_enable: bool = False,
    workspace_path: Optional[str] = None
):
    """
    初始化日志（创建新实例）

    Args:
        log_dir: 日志目录（如果为 None 且 use_workspace=True，则自动检测 thesis-workspace/logs）
        session_name: 会话名称
        use_workspace: 是否优先使用 thesis-workspace/logs 目录
        check_config: 是否检查配置文件中的 enabled 开关（默认 True）
        force_enable: 强制启用日志（忽略配置，默认 False）
        workspace_path: 显式工作区路径（优先于自动检测）

    Returns:
        新的 ThesisLogger 实例（如果启用）或 NullLogger 实例（如果禁用）
    """
    global _logger, _null_logger

    normalized_workspace = _normalize_workspace_path(workspace_path)

    # 检查配置是否启用日志（除非强制启用）
    if not force_enable and check_config and not _is_logging_enabled(workspace_path=str(normalized_workspace) if normalized_workspace else None):
        ThesisLogger._instance = None
        ThesisLogger._initialized = False
        _logger = None
        _null_logger = NullLogger()
        return _null_logger

    # 自动检测 log_dir
    if log_dir is None:
        if normalized_workspace:
            log_dir = str(normalized_workspace / "logs")
        elif use_workspace:
            log_dir = str(_find_workspace_log_dir())
        else:
            log_dir = "logs"

    # 重置单例状态
    ThesisLogger._instance = None
    ThesisLogger._initialized = False
    _null_logger = None
    _logger = ThesisLogger(log_dir=log_dir, session_name=session_name)
    return _logger


if __name__ == "__main__":
    # 测试日志功能
    logger = init_logger(session_name="test_session")

    logger.step("Step 1: 环境准备", "start")
    logger.info("检查工作目录...")
    logger.file_operation("create", "workspace/outline.md")
    logger.step("Step 1: 环境准备", "complete")

    logger.step("Step 2: 生成大纲", "start")
    logger.chapter_progress("第1章 绪论", 2500, 2500)
    logger.chapter_progress("第2章 技术综述", 4000, 6500)

    logger.quality_check("国内外研究现状", True, "约500字")
    logger.quality_check("流程图", False, "缺少占位符")

    logger.warning("技术综述章节篇幅过长，建议精简")

    try:
        raise ValueError("测试错误")
    except Exception as e:
        logger.error_with_context(e, {
            "file": "test.py",
            "line": 100,
            "operation": "parse_reference"
        })

    logger.step("Step 2: 生成大纲", "complete")
    logger.info("会话结束")

    # 导出报告
    logger.export_session_report()