"""规则引擎：优先级匹配 + 兜底链。"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from ..models import Transaction, DIRECTION_EXPENSE
from .schema import normalize_rule


class RuleEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.categories: List[str] = list(config.get("categories", []))
        self.rules: List[Dict[str, Any]] = [normalize_rule(r) for r in config.get("rules", [])]
        self.type_mapping: Dict[str, str] = config.get("type_mapping", {})
        self.platform_category_mapping: Dict[str, str] = config.get("platform_category_mapping", {})
        # 预编译正则，并按优先级排序（保留原始下标用于命中回溯）
        self._compiled: List[Dict[str, Any]] = []
        for idx, r in enumerate(self.rules):
            item = dict(r)
            item["_index"] = idx
            item["_regex"] = None
            if r["match_mode"] == "regex" and r["keyword"]:
                try:
                    item["_regex"] = re.compile(r["keyword"])
                except re.error:
                    item["_regex"] = None
            self._compiled.append(item)
        self._compiled.sort(key=lambda r: r["priority"], reverse=True)

    # ---- 分类 ----
    def classify_one(self, txn: Transaction, allow_reclassify: bool = True) -> str:
        """对单条交易分类。只对支出做消费归类。"""
        if txn.direction != DIRECTION_EXPENSE:
            txn.category = ""
            return ""
        if txn.manual_category is not None:
            txn.category = txn.manual_category if txn.manual_category in self.categories else ""
            return txn.category
        if txn.category in self.categories and not allow_reclassify:
            return txn.category

        text_map = {
            "counterparty": txn.counterparty,
            "goods": txn.goods,
            "type": txn.txn_type,
            "any": " ".join([txn.counterparty, txn.goods, txn.txn_type]),
        }

        # 1. 用户规则（优先级从高到低）
        for r in self._compiled:
            if not r["enabled"] or r["category"] not in self.categories:
                continue
            field = r["match_field"]
            text = text_map.get(field, "")
            if not text:
                continue
            if self._match(r, text):
                txn.category = r["category"]
                return r["category"]

        # 2. 交易类型映射（微信）
        if self.type_mapping.get(txn.txn_type) in self.categories:
            txn.category = self.type_mapping[txn.txn_type]
            return txn.category

        # 3. 平台原始分类映射（支付宝）
        if self.platform_category_mapping.get(txn.original_category) in self.categories:
            txn.category = self.platform_category_mapping[txn.original_category]
            return txn.category

        txn.category = ""
        return ""

    def classify_all(self, txns: List[Transaction]) -> None:
        for t in txns:
            self.classify_one(t)

    def applied_rule_index(self, txn: Transaction) -> Optional[int]:
        """返回对某条支出实际生效的规则下标（self.rules 中的位置）。

        即按优先级排序后第一条命中的启用规则；非支出或未命中返回 None。
        """
        if txn.direction != DIRECTION_EXPENSE:
            return None
        if txn.manual_category is not None:
            return None
        text_map = {
            "counterparty": txn.counterparty,
            "goods": txn.goods,
            "type": txn.txn_type,
            "any": " ".join([txn.counterparty, txn.goods, txn.txn_type]),
        }
        for r in self._compiled:
            if not r["enabled"] or r["category"] not in self.categories:
                continue
            text = text_map.get(r["match_field"], "")
            if not text:
                continue
            if self._match(r, text):
                return r["_index"]
        return None

    @staticmethod
    def _match(rule: Dict[str, Any], text: str) -> bool:
        mode = rule["match_mode"]
        keyword = rule["keyword"]
        if mode == "regex":
            rx = rule.get("_regex")
            return bool(rx and rx.search(text))
        if mode == "exact":
            return text == keyword
        # contains
        return keyword in text

    # ---- 规则命中预览（纯函数） ----
    @staticmethod
    def test_rule(rule: Dict[str, Any], text: str) -> bool:
        r = normalize_rule(rule)
        if not r["keyword"]:
            return False
        if r["match_mode"] == "regex":
            try:
                return bool(re.search(r["keyword"], text))
            except re.error:
                return False
        if r["match_mode"] == "exact":
            return text == r["keyword"]
        return r["keyword"] in text

    # ---- 命中原因（用于调试/展示） ----
    def hit_source(self, txn: Transaction) -> str:
        """返回分类来源说明：规则名 / 交易类型映射 / 平台分类映射 / 未分类。"""
        if txn.direction != DIRECTION_EXPENSE:
            return "非支出"
        if txn.manual_category is not None:
            return "手动指定"
        for r in self._compiled:
            if not r["enabled"] or r["category"] != txn.category:
                continue
            text_map = {
                "counterparty": txn.counterparty,
                "goods": txn.goods,
                "type": txn.txn_type,
                "any": " ".join([txn.counterparty, txn.goods, txn.txn_type]),
            }
            if self._match(r, text_map.get(r["match_field"], "")):
                return f"规则：{r['name']}"
        if txn.txn_type in self.type_mapping and txn.category == self.type_mapping[txn.txn_type]:
            return f"交易类型：{txn.txn_type}"
        if txn.original_category in self.platform_category_mapping and \
                txn.category == self.platform_category_mapping[txn.original_category]:
            return f"平台分类：{txn.original_category}"
        return "未分类"

    # ---- 分类相关辅助 ----
    def add_category(self, name: str) -> None:
        if name and name not in self.categories:
            self.categories.append(name)

    def sync_config(self) -> Dict[str, Any]:
        """把当前引擎状态写回配置（供保存到 JSON）。"""
        self.config["categories"] = self.categories
        self.config["rules"] = self.rules
        self.config["type_mapping"] = self.type_mapping
        self.config["platform_category_mapping"] = self.platform_category_mapping
        return self.config