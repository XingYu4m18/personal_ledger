"""账单导入和日期查询，供桌面界面和其他调用方共用。"""
from collections import Counter
from pathlib import Path

from .models import unique_key
from .parser import parse_file
from .storage import merge_transactions


def import_bills(existing, paths, *, batch_keys=None):
    seen = {unique_key(t): t for t in existing}
    messages = []
    parsed = False
    for path in paths:
        name = Path(path).name
        try:
            rows = parse_file(path).transactions
        except Exception as error:
            messages.append(f"{name}：读取失败（{error}）")
            continue
        if not rows:
            messages.append(f"{name}：未读到交易")
            continue
        parsed = True
        count = 0
        for row in rows:
            key = unique_key(row)
            if batch_keys is not None:
                batch_keys.add(key)
            if key not in seen:
                seen[key] = row
                count += 1
            else:
                old = seen[key]
                row.manual_category = old.manual_category
                row.manual_payment_key = old.manual_payment_key
                row.category = old.category
                row.merchant_id = row.merchant_id or old.merchant_id
                row.original_order_id = row.original_order_id or old.original_order_id
                seen[key] = row
        messages.append(f"{name}：新增 {count} 笔，重复 {len(rows) - count} 笔")
    if not parsed:
        raise ValueError("\n".join(messages) or "请选择账单文件")
    rows = merge_transactions(list(seen.values()))
    from .refunds import reconcile
    reconcile(rows)
    return rows, messages


def in_period(rows, period):
    if period is None:
        return rows
    start, end = period
    return [row for row in rows if row.time and start <= row.time.date() <= end]


def expense_totals(rows, key):
    totals = Counter()
    for row in rows:
        if row.is_expense:
            totals[key(row)] += row.net_amount
    return totals
