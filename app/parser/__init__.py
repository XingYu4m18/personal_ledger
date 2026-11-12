"""解析器模块。"""

from .base import BaseParser, ParseResult, parse_file, parse_files, detect_platform
from .wechat_parser import WechatParser
from .alipay_parser import AlipayParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "parse_file",
    "parse_files",
    "detect_platform",
    "WechatParser",
    "AlipayParser",
]