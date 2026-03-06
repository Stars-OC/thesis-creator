# -*- coding: utf-8 -*-
"""
thesis-creator 日志工具模块

提供统一的日志记录功能，支持：
- 控制台输出（带颜色）
- 文件输出（logs/ 目录）
- 分级日志（DEBUG, INFO, WARNING, ERROR）
- 会话隔离（每次运行生成独立日志文件）
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


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
        self.log_dir.mkdir(parents=True, exist_ok=True)

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

        # 文件处理器
        log_file = self.log_dir / f"{self.session_name}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 记录日志文件路径
        self.log_file = log_file

        self._initialized = True

        # 写入会话开始标记
        self.logger.info("=" * 60)
        self.logger.info(f"Thesis-Creator Session Started")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Log File: {log_file}")
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
            'start': '▶️',
            'complete': '✅',
            'error': '❌',
            'skip': '⏭️'
        }
        icon = status_icons.get(status, '📌')
        self.logger.info(f"{icon} Step: {step_name} [{status}]")

    def file_operation(self, operation: str, file_path: str, success: bool = True):
        """
        记录文件操作

        Args:
            operation: 操作类型 (read/write/create/delete)
            file_path: 文件路径
            success: 是否成功
        """
        status = "✅" if success else "❌"
        self.logger.info(f"{status} File {operation}: {file_path}")

    def chapter_progress(self, chapter: str, word_count: int, total_words: int):
        """
        记录章节进度

        Args:
            chapter: 章节名称
            word_count: 当前章节字数
            total_words: 总字数
        """
        self.logger.info(f"📝 {chapter} 完成: {word_count} 字 | 累计: {total_words} 字")

    def quality_check(self, check_item: str, passed: bool, details: str = ""):
        """
        记录质量检查结果

        Args:
            check_item: 检查项
            passed: 是否通过
            details: 详细信息
        """
        status = "✅ PASS" if passed else "❌ FAIL"
        msg = f"🔍 {check_item}: {status}"
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
        self.logger.error(f"❌ Error: {type(error).__name__}: {error}")
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

        self.logger.info(f"📊 会话报告已导出: {output_path}")
        return str(output_path)


# 全局日志实例
_logger: Optional[ThesisLogger] = None


def get_logger(
    log_dir: str = "logs",
    session_name: Optional[str] = None
) -> ThesisLogger:
    """
    获取全局日志实例

    Args:
        log_dir: 日志目录
        session_name: 会话名称

    Returns:
        ThesisLogger 实例
    """
    global _logger
    if _logger is None:
        _logger = ThesisLogger(log_dir=log_dir, session_name=session_name)
    return _logger


def init_logger(
    log_dir: str = "logs",
    session_name: Optional[str] = None
) -> ThesisLogger:
    """
    初始化日志（创建新实例）

    Args:
        log_dir: 日志目录
        session_name: 会话名称

    Returns:
        新的 ThesisLogger 实例
    """
    global _logger
    # 重置单例状态
    ThesisLogger._instance = None
    ThesisLogger._initialized = False
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