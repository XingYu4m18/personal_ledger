"""微信支付账单（.xlsx）解析器。"""

from __future__ import annotations

from datetime import datetime
from typing import List

import openpyxl

from .base import BaseParser, ParseResult
from ..models import (
    Transaction,
    PLATFORM_WECHAT,
    DIRECTION_EXPENSE,
    DIRECTION_INCOME,
    DIRECTION_NEUTRAL,
)

# 微信表头关键列名
_HEADER_MARK = "交易时间"
_COL_MAP = {
    "交易时间": "time",
    "交易类型": "txn_type",
    "交易对方": "counterparty",
    "商品": "goods",
    "收/支": "direction",
    "金额(元)": "amount",
    "金额": "amount",
    "支付方式": "payment_method",
    "当前状态": "status",
    "交易单号": "txn_id",
    "商户单号": "merchant_id",
    "原交易单号": "original_order_id",
    "原交易订单号": "original_order_id",
    "原支付订单号": "original_order_id",
    "退款单号": "refund_id",
    "退款订单号": "refund_id",
    "备注": "remark",
}


class WechatParser(BaseParser):
    platform = PLATFORM_WECHAT

    def parse(self, path: str) -> ParseResult:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        header_idx = self._locate_header(rows)
        if header_idx is None:
            raise ValueError("未找到微信账单表头行")

        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        col_index = {}
        for i, name in enumerate(header):
            key = _COL_MAP.get(name)
            if key and key not in col_index:
                col_index[key] = i

        info = self._extract_meta(rows, header_idx)
        transactions: List[Transaction] = []

        for row in rows[header_idx + 1:]:
            if row is None or all(c is None or str(c).strip() == "" for c in row):
                continue
            raw_time = self._cell(row, col_index, "time")
            if raw_time is None:
                continue
            t = self._parse_time(raw_time)
            amount = self._to_float(self._cell(row, col_index, "amount"))
            direction = str(self._cell(row, col_index, "direction") or "").strip()
            status = self._clean(self._cell(row, col_index, "status"))
            if direction not in (DIRECTION_INCOME, DIRECTION_EXPENSE):
                if amount < 0:
                    direction = DIRECTION_EXPENSE
                else:
                    direction = DIRECTION_EXPENSE
            # 预处理：已关闭/撤销/取消的交易不计入实际支出
            if direction == DIRECTION_EXPENSE and any(k in status for k in ("关闭", "撤销", "取消", "失败", "已过期")):
                direction = DIRECTION_NEUTRAL

            txn = Transaction(
                time=t,
                amount=abs(amount),
                direction=direction,
                counterparty=str(self._cell(row, col_index, "counterparty") or "").strip(),
                goods=str(self._cell(row, col_index, "goods") or "").strip(),
                txn_type=self._clean(self._cell(row, col_index, "txn_type")),
                platform=PLATFORM_WECHAT,
                original_category="",
                payment_method=self._clean(self._cell(row, col_index, "payment_method")),
                status=status,
                txn_id=self._clean(self._cell(row, col_index, "txn_id")),
                merchant_id=self._clean(self._cell(row, col_index, "merchant_id")),
                original_order_id=self._clean(self._cell(row, col_index, "original_order_id")),
                refund_id=self._clean(self._cell(row, col_index, "refund_id")),
                platform_label="微信",
                remark=self._clean(self._cell(row, col_index, "remark")),
            )
            transactions.append(txn)

        info["记录数"] = len(transactions)
        return ParseResult(transactions, info)

    @staticmethod
    def _locate_header(rows) -> int | None:
        for i, row in enumerate(rows):
            if row is None:
                continue
            for c in row:
                if c is not None and str(c).strip() == _HEADER_MARK:
                    return i
        return None

    @staticmethod
    def _extract_meta(rows, header_idx) -> dict:
        meta = {"平台": "微信"}
        for row in rows[:header_idx]:
            if not row:
                continue
            for c in row:
                if not c:
                    continue
                text = str(c)
                for key in ("微信昵称", "起始时间", "导出类型", "导出时间"):
                    if text.startswith(key):
                        meta[key] = text.replace(key, "", 1).strip(" ：:[]()")
        return meta

    @staticmethod
    def _cell(row, col_index, key):
        idx = col_index.get(key)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    @staticmethod
    def _clean(v) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        return "" if s in ("/", "-") else s

    @staticmethod
    def _to_float(v) -> float:
        try:
            return float(str(v).replace(",", "").strip())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _parse_time(v) -> datetime | None:
        if isinstance(v, datetime):
            return v
        if v is None:
            return None
        s = str(v).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None