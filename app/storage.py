"""数据合并、去重、导出。"""

from __future__ import annotations

from typing import List

import csv
from collections import defaultdict
from openpyxl import Workbook

from .models import Transaction, unique_key, DIRECTION_EXPENSE, UNCATEGORIZED


def merge_transactions(txns: List[Transaction]) -> List[Transaction]:
    """按主键去重，保留首次出现，并按时间升序排列。"""
    seen = set()
    out: List[Transaction] = []
    for t in txns:
        key = unique_key(t)
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    out.sort(key=lambda x: x.time if x.time else __import__("datetime").datetime.min)
    return out


def detail_rows(txns):
    return [{**t.to_row(), "统计方向": t.accounting_direction, "计入金额": t.net_amount,
             "本人账户划转": t.own_card, "退款关联": t.refund_note} for t in txns]


def summary_stats(txns):
    expenses = [t for t in txns if t.is_expense]
    incomes = [t for t in txns if t.is_income]
    return {"笔数": len(txns), "支出笔数": len(expenses), "收入笔数": len(incomes),
            "支出总额": round(sum(t.net_amount for t in expenses),2),
            "收入总额": round(sum(t.net_amount for t in incomes),2),
            "未分类笔数": sum(t.category_display == UNCATEGORIZED for t in expenses)}


def export_csv(txns, path):
    rows = detail_rows(txns)
    headers = list(rows[0]) if rows else list(Transaction().to_row()) + ["统计方向","计入金额","本人账户划转","退款关联"]
    with open(path,"w",encoding="utf-8-sig",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def export_excel(txns, path):
    book = Workbook()
    detail = book.active
    detail.title = "全部明细"
    rows = detail_rows(txns)
    detail.append(list(rows[0]) if rows else list(Transaction().to_row()) + ["统计方向","计入金额","本人账户划转","退款关联"])
    for row in rows:
        detail.append(list(row.values()))
    for title, key, headers in [
        ("分类汇总",lambda t:t.category_display,["分类","笔数","金额合计","金额占比"]),
        ("商家排行",lambda t:t.counterparty,["商家","笔数","金额合计"])]:
        sheet = book.create_sheet(title)
        sheet.append(headers)
        groups = defaultdict(lambda: [0,0])
        for t in txns:
            if t.is_expense:
                groups[key(t)][0] += 1
                groups[key(t)][1] += round(t.net_amount*100)
        total = sum(v[1] for v in groups.values())
        for name,(count,cents) in sorted(groups.items(),key=lambda item:-item[1][1]):
            values = [name,count,cents/100]
            if title == "分类汇总":
                values.append(round(cents/total*100,2) if total else 0)
            sheet.append(values)
    monthly = book.create_sheet("月度汇总")
    monthly.append(["月份","收入","支出","结余"])
    groups = defaultdict(lambda:[0,0])
    for t in txns:
        if t.time:
            values = groups[t.month]
            if t.is_income:
                values[0] += round(t.net_amount*100)
            if t.is_expense:
                values[1] += round(t.net_amount*100)
    for month,(income,expense) in sorted(groups.items()):
        monthly.append([month,income/100,expense/100,(income-expense)/100])
    book.save(path)
