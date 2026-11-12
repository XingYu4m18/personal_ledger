"""统一交易数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# 收支方向
DIRECTION_EXPENSE = "支出"
DIRECTION_INCOME = "收入"
DIRECTION_NEUTRAL = "不计收支"

# 平台标识
PLATFORM_WECHAT = "wechat"
PLATFORM_ALIPAY = "alipay"

# 默认消费分类
DEFAULT_CATEGORIES = [
    "吃喝",
    "购物",
    "娱乐",
    "交通",
    "医疗健康",
    "教育培训",
    "人际往来",
    "生活服务",
    "数码电器",
    "家居家装",
    "其他",
]

UNCATEGORIZED = "未分类"


@dataclass
class Transaction:
    """一条统一后的账单记录。"""

    time: datetime = None
    amount: float = 0.0
    direction: str = DIRECTION_EXPENSE
    counterparty: str = ""          # 交易对方 / 商家
    goods: str = ""                 # 商品说明 / 商品
    txn_type: str = ""              # 交易类型（微信）或空
    platform: str = ""              # wechat / alipay
    original_category: str = ""     # 支付宝自带「交易分类」
    payment_method: str = ""
    status: str = ""
    txn_id: str = ""                # 交易单号
    category: str = ""              # 归类结果（空 = 未分类）

    # 展示用
    platform_label: str = ""
    remark: str = ""

    manual_category: str | None = None

    merchant_id: str = ""
    original_order_id: str = ""
    refund_id: str = ""
    manual_payment_key: str = ""
    own_card: str = field(default="", init=False)
    refunded_cents: int = field(default=0, init=False)
    refund_note: str = field(default="", init=False)

    @property
    def is_refund_record(self):
        if self.direction == DIRECTION_EXPENSE:
            return False
        return bool(self.refund_id or self.original_order_id or "退款" in self.txn_type
                    or self.original_category == "退款" or self.goods.startswith("退款")
                    or (self.direction != DIRECTION_EXPENSE and "退款" in self.status))

    @property
    def accounting_direction(self):
        if self.own_card or self.is_refund_record or (self.direction == DIRECTION_EXPENSE and
                                     (self.refund_note.startswith("已关联退款") or "全额退款" in self.status) and not self.net_amount):
            return DIRECTION_NEUTRAL
        return self.direction

    @property
    def net_amount(self):
        if self.own_card or self.is_refund_record or self.direction == DIRECTION_NEUTRAL or self.status in ("全额退款", "已全额退款", "全额退款成功"):
            return 0.
        return (round(self.amount * 100) - self.refunded_cents) / 100

    def __post_init__(self) -> None:
        if not self.platform_label and self.platform:
            self.platform_label = {
                PLATFORM_WECHAT: "微信",
                PLATFORM_ALIPAY: "支付宝",
            }.get(self.platform, self.platform)

    @property
    def is_expense(self) -> bool:
        return self.accounting_direction == DIRECTION_EXPENSE

    @property
    def is_income(self) -> bool:
        return self.accounting_direction == DIRECTION_INCOME

    @property
    def is_neutral(self) -> bool:
        return self.direction == DIRECTION_NEUTRAL

    @property
    def category_display(self) -> str:
        if self.own_card:
            return "本人账户划转"
        if self.direction == DIRECTION_INCOME:
            return "收入"
        if self.direction == DIRECTION_NEUTRAL:
            return "不计收支"
        return self.category or UNCATEGORIZED

    @property
    def platform_type(self):
        return self.original_category if self.platform == PLATFORM_ALIPAY else self.txn_type

    @property
    def month(self) -> str:
        """yyyy-MM 形式，用于按月汇总。"""
        if self.time is None:
            return "未知"
        return self.time.strftime("%Y-%m")

    def to_row(self) -> dict:
        """转成表格展示/导出用的一行。"""
        return {
            "时间": self.time.strftime("%Y-%m-%d %H:%M:%S") if self.time else "",
            "平台": self.platform_label,
            "方向": self.direction,
            "金额": self.amount,
            "分类": self.category_display,
            "交易对方": self.counterparty,
            "商品说明": self.goods,
            "交易类型": self.txn_type,
            "原始分类": self.original_category,
            "支付方式": self.payment_method,
            "状态": self.status,
            "交易单号": self.txn_id,
        }


def unique_key(txn: Transaction) -> str:
    """合并去重用主键。"""
    number = (txn.refund_id or txn.txn_id) if txn.is_refund_record else txn.txn_id
    kind = "退款" if txn.is_refund_record else "交易"
    if number.strip() not in ("", "/", "-"):
        return f"{txn.platform}|{kind}|{number.strip()}"
    return f"{txn.platform}|{kind}|{txn.time}|{txn.amount}|{txn.counterparty}|{txn.goods}|{txn.direction}"