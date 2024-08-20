import logging
import platform
import re
import sys
from pathlib import Path


class ReaderLogger:
    def __init__(self, name: str, log_path: Path):
        self.name = name
        self.log_path = log_path

        # ANSI color codes
        self.CYAN = '\033[96m'
        self.BLUE = '\033[94m'
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.RESET = '\033[0m'

        # 強制 Windows 使用 UTF-8
        if platform.system().lower() == 'windows':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                self.unicode_support = True
            except Exception:
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
                self.unicode_support = True
        else:
            self.unicode_support = True

        # 使用 Unicode 字符
        self.BOX_TOP_LEFT = "╔"
        self.BOX_TOP_RIGHT = "╗"
        self.BOX_BOTTOM_LEFT = "╚"
        self.BOX_BOTTOM_RIGHT = "╝"
        self.BOX_HORIZONTAL = "═"
        self.BOX_VERTICAL = "║"
        self.ARROW = "▶"

        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # clean ANSI formatter (for log file)
        class CleanFormatter(logging.Formatter):
            def format(self, record):
                formatted_msg = super().format(record)
                return re.sub(r'\033\[[0-9;]*m', '', formatted_msg)

        # Set up handlers with UTF-8 encoding
        file_handler = logging.FileHandler(self.log_path / f'{self.name}.log', encoding='utf-8')
        file_handler.setFormatter(CleanFormatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def info_box(self, text: str, color_part: str = None, width: int = 80):
        """
        Create a boxed message with optional colored text

        Args:
            text: Base text format (e.g., "Reading {} RAW DATA from {} to {}")
            color_part: Part of text to be colored (e.g., "RAW DATA")
            width: Box width
        """
        display_text = text.replace(color_part, " " * len(color_part)) if color_part else text

        left_padding = " " * ((width - len(display_text)) // 2)
        right_padding = " " * (width - len(display_text) - len(left_padding))

        content = text.replace(color_part, f"{self.CYAN}{color_part}{self.RESET}") if color_part else text

        __content__ = f"{left_padding}{content}{right_padding}"

        self.info(f"╔{'═' * width}╗")
        self.info(f"║{__content__}║")
        self.info(f"╚{'═' * width}╝")