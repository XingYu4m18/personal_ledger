"""规则配置的 JSON 结构、默认值、加载/保存。"""

from __future__ import annotations

import copy
import json
import os
from typing import List, Dict, Any

from ..models import DEFAULT_CATEGORIES

# 规则字段定义，供 GUI 编辑使用
MATCH_FIELDS = [
    ("counterparty", "交易对方（商家）"),
    ("goods", "商品说明/商品"),
    ("type", "交易类型"),
    ("any", "任意字段（商家+商品+类型）"),
]

MATCH_MODES = [
    ("contains", "包含关键字"),
    ("exact", "完全等于"),
    ("regex", "正则表达式"),
]

DEFAULT_RULE_EXPORT = [
    "name", "enabled", "priority", "match_field", "match_mode",
    "keyword", "category",
]

def default_config() -> Dict[str, Any]:
    """新账本仅提供分类名称，自动分类由用户设置。"""
    return {"version": 1, "categories": list(DEFAULT_CATEGORIES), "rules": [],
            "type_mapping": {}, "platform_category_mapping": {}}


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    base = default_config()
    for key in ("categories", "type_mapping", "platform_category_mapping"):
        if key in data and isinstance(data[key], (dict, list)):
            base[key] = data[key]
    base["rules"] = data.get("rules", [])
    base["version"] = data.get("version", base["version"])
    return base


def save_config(data: Dict[str, Any], path: str) -> None:
    from PySide6.QtCore import QSaveFile, QIODevice
    output = QSaveFile(path)
    if not output.open(QIODevice.WriteOnly):
        raise OSError(output.errorString())
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    if output.write(payload) != len(payload) or not output.commit():
        raise OSError(output.errorString())


def normalize_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """对一条规则做字段规范化，便于 GUI 使用。"""
    r = {
        "name": str(rule.get("name", "")),
        "enabled": bool(rule.get("enabled", True)),
        "priority": int(rule.get("priority", 100)),
        "match_field": str(rule.get("match_field", "counterparty")),
        "match_mode": str(rule.get("match_mode", "contains")),
        "keyword": str(rule.get("keyword", "")),
        "category": str(rule.get("category", "")),
    }
    return r