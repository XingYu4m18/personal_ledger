"""识别钱包与本人银行卡之间的划转。保留原流水供核对。"""
import re
import unicodedata

BANK_ALIASES = {"工行": "工商银行", "招行": "招商银行", "建行": "建设银行", "农行": "农业银行", "中行": "中国银行"}
WALLET_ACTIONS = ("零钱提现", "零钱充值", "余额提现", "余额充值", "提现到银行卡", "余额转出到银行卡", "银行卡充值到余额", "提现-实时提现", "提现-快速提现", "余额提现到卡", "充值到余额")


def normalize(text):
    text = unicodedata.normalize("NFKC", text).replace(" ", "")
    for alias, bank in BANK_ALIASES.items():
        text = text.replace(alias, bank)
    return text


def transfer_card(row, cards):
    if row.is_refund_record or any(word in row.status for word in ("失败", "关闭", "撤销", "取消")):
        return ""
    descriptions = [normalize(s) for s in (row.txn_type, row.original_category, row.goods)]
    if any("手续费" in s or "服务费" in s for s in descriptions):
        return ""
    wallet = any(s.startswith(action) for s in descriptions for action in WALLET_ACTIONS)
    wallet = wallet or (row.platform == "alipay" and any(s in ("提现", "账户提现", "充值到支付宝余额") for s in descriptions))
    transfer = any(s in ("转账", "转账到银行卡", "提现", "充值", "转账红包", "转账到卡") for s in descriptions)
    target = normalize(row.counterparty)
    for bank, tail in cards:
        # 钱包充值/提现的卡可出现在支付方式。普通转账仅核对收款方。
        locations = [target]
        if wallet:
            locations += [normalize(row.payment_method), *descriptions]
        elif transfer:
            locations += [s for s in descriptions if s.startswith(("转账到银行卡", "提现到银行卡"))]
        if (wallet or transfer) and any(normalize(bank) in s and re.search(r"(?<!\d)" + re.escape(tail) + r"(?!\d)", s) for s in locations):
            return f"{bank}（{tail}）"
    return ""


def apply_transfers(rows, cards):
    for row in rows:
        row.own_card = transfer_card(row, cards)
