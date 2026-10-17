from __future__ import annotations

import codecs
import logging
import os
import platform
import re
import sys
from pathlib import Path


class ReaderLogger:
    def __init__(self, name: str, log_path: Path, log_level: str = 'INFO', quiet: bool = False):
        self.name = name
        self.log_path = log_path
        self._log_level = getattr(logging, log_level)
        self.quiet = quiet
        #: Console-bound records, held back during a read and rendered as one
        #: grouped summary at the end (``core.console_summary``). The log file
        #: still gets every record as it happens.
        self.records: list[logging.LogRecord] = []

        # 檢查是否支持顏色輸出
        self.color_support = self._check_color_support()

        # 設置顏色代碼
        if self.color_support:
            self.CYAN = '\033[96m'
            self.BLUE = '\033[94m'
            self.GREEN = '\033[92m'
            self.YELLOW = '\033[93m'
            self.RED = '\033[91m'
            self.RESET = '\033[0m'
        else:
            self.CYAN = ''
            self.BLUE = ''
            self.GREEN = ''
            self.YELLOW = ''
            self.RED = ''
            self.RESET = ''

        # 檢查 Unicode 支持
        self.unicode_support = self._check_unicode_support()

        # 設置框架字符
        if self.unicode_support:
            self.BOX_TOP_LEFT = "╭"
            self.BOX_TOP_RIGHT = "╮"
            self.BOX_BOTTOM_LEFT = "╰"
            self.BOX_BOTTOM_RIGHT = "╯"
            self.BOX_HORIZONTAL = "─"
            self.BOX_VERTICAL = "│"
            self.ARROW = "▶"
        else:
            self.BOX_TOP_LEFT = "+"
            self.BOX_TOP_RIGHT = "+"
            self.BOX_BOTTOM_LEFT = "+"
            self.BOX_BOTTOM_RIGHT = "+"
            self.BOX_HORIZONTAL = "-"
            self.BOX_VERTICAL = "|"
            self.ARROW = ">"

        self.logger = self._setup_logger()

    def _check_color_support(self) -> bool:
        """檢查環境是否支持顏色輸出"""
        # 檢查是否在 Spyder 或其他 IDE 中運行
        if any(IDE in os.environ.get('PYTHONPATH', '') for IDE in ['spyder', 'jupyter']):
            return False

        # 檢查是否強制啟用或禁用顏色
        if 'FORCE_COLOR' in os.environ:
            return os.environ['FORCE_COLOR'].lower() in ('1', 'true', 'yes')

        # Windows 檢查
        if platform.system().lower() == 'windows':
            return ('ANSICON' in os.environ or
                    'WT_SESSION' in os.environ or  # Windows Terminal
                    'ConEmuANSI' in os.environ or
                    os.environ.get('TERM_PROGRAM', '').lower() == 'vscode')

        # 其他系統檢查
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def _check_unicode_support(self) -> bool:
        """設置 Unicode 支持"""
        if platform.system().lower() == 'windows':
            try:
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8')
                elif hasattr(sys.stdout, 'buffer'):
                    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
                else:
                    return False
                return True
            except Exception:
                return False
        return True

    def _setup_logger(self) -> logging.Logger:
        """設置logger"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self._log_level)

        # 移除現有的 handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # 清理 ANSI 格式化器
        class CleanFormatter(logging.Formatter):
            def format(self, record):
                formatted_msg = super().format(record)
                return re.sub(r'\033\[[0-9;]*m', '', formatted_msg)

        # 設置檔案處理器
        try:
            log_dir = Path(self.log_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f'{self.name}.log',
                encoding='utf-8',
                errors='replace'
            )
            file_handler.setFormatter(
                CleanFormatter('%(asctime)s - %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')
            )
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")

        # 設置控制台處理器（quiet 模式下不加）
        # 控制台:不即時印出,先收集起來,讀完後由 console_summary 統一排版
        # (quiet 模式下不收集)。`file_info` records go to the log file only.
        if not self.quiet:
            collector = _CollectingHandler(self.records)
            collector.addFilter(lambda record: not getattr(record, 'file_only', False))
            logger.addHandler(collector)

        return logger

    def _safe_print(self, text: str) -> str:
        """安全打印，處理編碼問題"""
        if not self.unicode_support:
            text = text.encode('ascii', 'replace').decode('ascii')
        return text

    def debug(self, msg: str):
        self.logger.debug(self._safe_print(msg))

    # `notice` keywords (group=, item=, detail=) let the end-of-read summary
    # fold many per-file messages into one line per kind; the log file still
    # gets the full message. See `core.console_summary` for the groups.
    def info(self, msg: str, **notice):
        self.logger.info(self._safe_print(msg), extra=_extra(notice))

    def file_info(self, msg: str):
        """INFO to the log file only — for detail the console already shows
        another way (e.g. ``Saved: ...``, which the end-of-read output list
        covers)."""
        self.logger.info(self._safe_print(msg), extra={'file_only': True})

    def warning(self, msg: str, **notice):
        self.logger.warning(self._safe_print(msg), extra=_extra(notice))

    def error(self, msg: str, **notice):
        self.logger.error(self._safe_print(msg), extra=_extra(notice))

    def info_box(self, text: str, color_part: str = None, width: int = 80):
        """創建帶框的消息，可選擇性地為部分文本著色"""
        # 處理文本
        display_text = text.replace(color_part, " " * len(color_part)) if color_part else text

        # 計算padding
        left_padding = " " * ((width - len(display_text)) // 2)
        right_padding = " " * (width - len(display_text) - len(left_padding))

        # 處理顏色
        if color_part and self.color_support:
            content = text.replace(color_part, f"{self.CYAN}{color_part}{self.RESET}")
        else:
            content = text

        __content__ = f"{left_padding}{content}{right_padding}"

        # 使用當前設置的框架字符
        self.info(f"{self.BOX_TOP_LEFT}{self.BOX_HORIZONTAL * width}{self.BOX_TOP_RIGHT}")
        self.info(f"{self.BOX_VERTICAL}{__content__}{self.BOX_VERTICAL}")
        self.info(f"{self.BOX_BOTTOM_LEFT}{self.BOX_HORIZONTAL * width}{self.BOX_BOTTOM_RIGHT}")


def _extra(notice: dict) -> dict | None:
    return {'notice': notice} if notice else None


class _CollectingHandler(logging.Handler):
    """Holds console-bound records instead of printing them as they come."""

    def __init__(self, sink: list):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.append(record)
