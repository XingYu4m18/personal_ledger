"""支付宝交易明细（.csv）解析器。"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import List

from .base import BaseParser, ParseResult
from ..models import (
    Transaction,
    PLATFORM_ALIPAY,
    DIRECTION_EXPENSE,
    DIRECTION_INCOME,
    DIRECTION_NEUTRAL,
)

_HEADER_MARK = "交易时间"
_COL_MAP = {
    "交易时间": "time",
    "交易分类": "original_category",
    "交易对方": "counterparty",
    "对方账号": "account",
    "商品说明": "goods",
    "收/支": "direction",
    "金额": "amount",
    "收/付款方式": "payment_method",
    "交易状态": "status",
    "交易订单号": "txn_id",
    "商家订单号": "merchant_id",
    "原交易单号": "original_order_id",
    "原交易订单号": "original_order_id",
    "原支付订单号": "original_order_id",
    "退款单号": "refund_id",
    "退款订单号": "refund_id",
    "备注": "remark",
}


def _decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


class AlipayParser(BaseParser):
    platform = PLATFORM_ALIPAY

    def parse(self, path: str) -> ParseResult:
        with open(path, "rb") as f:
            raw = f.read()
        text = _decode_bytes(raw)
        rows = list(csv.reader(io.StringIO(text)))

        header_idx = self._locate_header(rows)
        if header_idx is None:
            raise ValueError("未找到支付宝账单表头行")

        header = [c.strip() for c in rows[header_idx]]
        col_index = {}
        for i, name in enumerate(header):
            key = _COL_MAP.get(name)
            if key and key not in col_index:
                col_index[key] = i

        info = self._extract_meta(rows, header_idx)
        transactions: List[Transaction] = []

        for row in rows[header_idx + 1:]:
            if not row or all(c.strip() == "" for c in row):
                continue
            raw_time = self._cell(row, col_index, "time").strip()
            if not raw_time:
                continue
            t = self._parse_time(raw_time)
            amount = self._to_float(self._cell(row, col_index, "amount"))
            direction = self._cell(row, col_index, "direction").strip()
            status = self._cell(row, col_index, "status").strip()
            if direction not in (DIRECTION_INCOME, DIRECTION_EXPENSE, DIRECTION_NEUTRAL):
                direction = DIRECTION_EXPENSE if amount >= 0 else DIRECTION_INCOME
            # 预处理：状态为“交易关闭/撤销/取消/失败”的支出不计入实际支出
            if direction == DIRECTION_EXPENSE and any(k in status for k in ("撤销", "取消", "失败")):
                direction = DIRECTION_NEUTRAL

            txn = Transaction(
                time=t,
                amount=abs(amount),
                direction=direction,
                counterparty=self._cell(row, col_index, "counterparty").strip(),
                goods=self._cell(row, col_index, "goods").strip(),
                txn_type="",
                platform=PLATFORM_ALIPAY,
                original_category=self._cell(row, col_index, "original_category").strip(),
                payment_method=self._cell(row, col_index, "payment_method").strip(),
                status=status,
                txn_id=self._cell(row, col_index, "txn_id").strip().strip("\t"),
                merchant_id=str.strip(self._cell(row, col_index, "merchant_id")),
                original_order_id=str.strip(self._cell(row, col_index, "original_order_id")),
                refund_id=str.strip(self._cell(row, col_index, "refund_id")),
                platform_label="支付宝",
                remark=self._cell(row, col_index, "remark").strip(),
            )
            transactions.append(txn)

        info["记录数"] = len(transactions)
        return ParseResult(transactions, info)

    @staticmethod
    def _locate_header(rows) -> int | None:
        for i, row in enumerate(rows):
            for c in row:
                if c.strip() == _HEADER_MARK:
                    return i
        return None

    @staticmethod
    def _extract_meta(rows, header_idx) -> dict:
        meta = {"平台": "支付宝"}
        for row in rows[:header_idx]:
            text = " ".join(c for c in row if c).strip()
            if not text:
                continue
            for key in ("姓名", "支付宝账户", "起始时间", "终止时间", "导出时间"):
                if key in text:
                    # 形如 “姓名：谌行” / “起始时间：[...]”
                    seg = text.split(key, 1)[-1].lstrip(" ：:[]")
                    seg = seg.split("终止时间")[0].split("     ")[0].strip()
                    meta[key] = seg
            if "共" in text and "笔记录" in text:
                meta["记录摘要"] = text
        return meta

    @staticmethod
    def _cell(row, col_index, key) -> str:
        idx = col_index.get(key)
        if idx is None or idx >= len(row):
            return ""
        return str(row[idx] or "").strip()

    @staticmethod
    def _to_float(v) -> float:
        try:
            return float(str(v).replace(",", "").replace("\t", "").strip())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _parse_time(v) -> datetime | None:
        s = v.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None