from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class SafetyAction(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    SILENT_BLOCK = "silent_block"


@dataclass
class SafetyRule:
    rule_type: str  # "regex" | "keyword"
    pattern: str
    severity: Severity
    action: SafetyAction
    description: str = ""


@dataclass
class SafetyResult:
    passed: bool
    severity: Severity = Severity.MILD
    action: SafetyAction = SafetyAction.PASS
    matched_rules: list[str] = field(default_factory=list)
    safe_content: str = ""


# Pre-loaded rules matching schema.sql defaults
DEFAULT_RULES: list[SafetyRule] = [
    SafetyRule("regex", r"\b\d{15,19}\b", Severity.SEVERE, SafetyAction.SILENT_BLOCK, "疑似银行卡号"),
    SafetyRule("regex", r"\b1[3-9]\d{9}\b", Severity.MODERATE, SafetyAction.BLOCK, "手机号"),
    SafetyRule("keyword", "管理员密码", Severity.SEVERE, SafetyAction.SILENT_BLOCK, "越狱探测"),
    SafetyRule("keyword", "忽略之前的指令", Severity.SEVERE, SafetyAction.SILENT_BLOCK, "提示词注入探测"),
    SafetyRule("keyword", "傻逼", Severity.MODERATE, SafetyAction.BLOCK, "侮辱性语言"),
    SafetyRule("keyword", "威胁客服人员", Severity.SEVERE, SafetyAction.SILENT_BLOCK, "人身威胁"),
]


class ContentSafety:
    """Content safety checker — runs before intent classification."""

    def __init__(self, rules: list[SafetyRule] | None = None) -> None:
        self._rules = rules or DEFAULT_RULES

    def check(self, content: str) -> SafetyResult:
        matched: list[str] = []
        worst_severity = Severity.MILD
        worst_action = SafetyAction.PASS

        for rule in self._rules:
            if rule.rule_type == "regex":
                if re.search(rule.pattern, content):
                    matched.append(rule.description)
            elif rule.rule_type == "keyword":
                if rule.pattern in content:
                    matched.append(rule.description)
            else:
                continue

            if matched and rule.description == matched[-1]:
                if self._severity_rank(rule.severity) > self._severity_rank(worst_severity):
                    worst_severity = rule.severity
                    worst_action = rule.action

        return SafetyResult(
            passed=len(matched) == 0,
            severity=worst_severity,
            action=worst_action,
            matched_rules=matched,
            safe_content=content if len(matched) == 0 else "",
        )

    @staticmethod
    def _severity_rank(s: Severity) -> int:
        return {Severity.MILD: 1, Severity.MODERATE: 2, Severity.SEVERE: 3}[s]

    def block_message(self, severity: Severity, action: SafetyAction) -> str:
        """Return a neutral rejection message — never expose detection internals."""
        if action == SafetyAction.SILENT_BLOCK:
            return "抱歉，我无法处理这个请求。"
        if severity == Severity.MODERATE:
            return "请重新描述您的问题。"
        return "抱歉，我无法处理这个请求。"


# ── Sensitive info masking ────────────────────────────────────────────────────

_SENSITIVE_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, replacement_pattern, description)
    (r'\b(\d{6})(\d{8,10})(\d{2}[\dXx])\b',  r'\1******\3',   '身份证号'),
    (r'\b(\d{4})\d{8,12}(\d{4})\b',           r'\1********\2', '银行卡号'),
    (r'\b(1[3-9]\d)\d{4}(\d{4})\b',            r'\1****\2',     '手机号'),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', r'***@***.***', '邮箱'),
]


def mask_sensitive(text: str) -> str:
    """Replace sensitive info patterns with masked versions. Returns cleaned text."""
    for pattern, replacement, _desc in _SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


# Global singleton
content_safety = ContentSafety()
