"""在完整流水中关联成功退款，保留付款和退款各自的原始记录。"""
import re
from datetime import datetime
from .models import DIRECTION_EXPENSE, PLATFORM_ALIPAY, PLATFORM_WECHAT, unique_key


def _text(value):
    return re.sub(r"\s+", "", value).casefold().strip("/- ")


def _merchant(value):
    return _text(value).removesuffix("-退款").removesuffix("平台商户")


def _words_match(payment, refund):
    pay_name = _merchant(payment.counterparty)
    names = {_merchant(refund.counterparty), _merchant(refund.txn_type), _merchant(refund.goods)}
    merchant = bool(pay_name and pay_name in names)
    # 通用的“转账”“退款”不能单独作为关联证据。
    generic = {"转账", "退款", "商户消费", "余额", "无", "无备注"}
    descriptions = {_text(payment.goods), _text(payment.remark)} - generic - {"", pay_name}
    details = bool(descriptions & {_text(refund.goods), _text(refund.remark)})
    return merchant, details


def _has_reference(payment, refund):
    if refund.platform == PLATFORM_ALIPAY:
        prefix = re.split(r"[_*]", refund.txn_id, maxsplit=1)[0]
        return bool(payment.txn_id and payment.txn_id in (refund.original_order_id, refund.txn_id, prefix))
    tokens = set(re.findall(r"[A-Za-z0-9_-]+", refund.goods + " " + refund.remark))
    return bool((payment.txn_id and payment.txn_id in (refund.original_order_id, refund.txn_id))
                or (payment.merchant_id and payment.merchant_id == refund.merchant_id)
                or (payment.txn_id and payment.txn_id in tokens)
                or (payment.merchant_id and payment.merchant_id in tokens))


def _payments(rows, refund):
    return [p for p in rows if p.platform == refund.platform and p.direction == DIRECTION_EXPENSE
            and not p.is_refund_record and p.time and refund.time and p.time <= refund.time]


def _rank(payment, refund):
    merchant, details = _words_match(payment, refund)
    if not (merchant or details):
        return (0, 0)
    return (int(details) + int(merchant), int(payment.status in ("全额退款", "已全额退款", "全额退款成功")))


def manual_candidates(rows, refund):
    result = []
    for p in _payments(rows, refund):
        remaining = round(p.amount * 100) - p.refunded_cents
        cents = round(refund.amount * 100)
        if 0 < cents <= remaining and (round(p.amount * 100) == cents or any(_words_match(p, refund)) or _has_reference(p, refund)):
            result.append(p)
    return sorted(result, key=lambda p: p.time, reverse=True)


def reconcile(rows):
    for row in rows:
        row.refunded_cents = 0
        row.refund_note = ""
    refunds = sorted((r for r in rows if r.is_refund_record),
                     key=lambda r: (not bool(r.manual_payment_key), r.time or datetime.min, r.txn_id))
    for refund in refunds:
        if any(word in refund.status for word in ("失败", "处理中", "申请中", "退款中", "关闭", "取消", "拒绝")):
            refund.refund_note = "退款未完成"
            continue
        payments = _payments(rows, refund)
        candidates = [p for p in payments if _has_reference(p, refund)]
        if refund.manual_payment_key:
            candidates = [p for p in payments if unique_key(p) == refund.manual_payment_key]
        elif not candidates and refund.platform == PLATFORM_WECHAT and "部分" not in refund.status:
            # 模糊匹配只接受等额、有文字佐证且最可信候选唯一的支付。
            ranked = [(p, _rank(p, refund)) for p in payments if round(p.amount * 100) == round(refund.amount * 100)]
            best = max((score for _, score in ranked), default=(0, 0))
            candidates = [p for p, score in ranked if score == best and score[0]]
        if len(candidates) != 1:
            refund.refund_note = "退款待匹配"
            continue
        original = candidates[0]
        cents = round(refund.amount * 100)
        zero_order = refund.platform == PLATFORM_ALIPAY and cents == 0 and original.amount == 0
        if not zero_order and not 0 < cents <= round(original.amount * 100) - original.refunded_cents:
            refund.refund_note = "退款金额待核对"
            continue
        original.refunded_cents += cents
        refund.refund_note = "关联原支付：" + (original.txn_id or original.merchant_id or str(original.time))
        original.refund_note = f"已关联退款 {original.refunded_cents / 100:.2f} 元"
