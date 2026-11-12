"""解析器接口与自动识别。"""

from __future__ import annotations

import os
from typing import List

from ..models import Transaction, PLATFORM_WECHAT, PLATFORM_ALIPAY


class ParseResult:
    def __init__(self, transactions: List[Transaction], info: dict):
        self.transactions = transactions
        self.info = info  # 如 姓名/账户/起始时间/笔数等


class BaseParser:
    platform = ""

    def parse(self, path: str) -> ParseResult:  # pragma: no cover
        raise NotImplementedError


def detect_platform(path: str) -> str:
    """根据文件名/内容识别平台。"""
    name = os.path.basename(path).lower()
    if "微信" in name or "wechat" in name:
        return PLATFORM_WECHAT
    if "支付宝" in name or "alipay" in name or name.endswith(".csv"):
        return PLATFORM_ALIPAY
    # 兜底：按扩展名
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return PLATFORM_WECHAT
    return PLATFORM_ALIPAY


def parse_file(path: str) -> ParseResult:
    platform = detect_platform(path)
    if platform == PLATFORM_WECHAT:
        from .wechat_parser import WechatParser
        return WechatParser().parse(path)
    from .alipay_parser import AlipayParser
    return AlipayParser().parse(path)


def parse_files(paths) -> List[Transaction]:
    """批量解析多个文件，返回合并后的交易列表。"""
    all_txns: List[Transaction] = []
    for p in paths:
        try:
            res = parse_file(p)
            all_txns.extend(res.transactions)
        except Exception as e:  # noqa: BLE001
            # 单个文件失败不阻断其余文件
            print(f"[parse error] {p}: {e}")
    return all_txns