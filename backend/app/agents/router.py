"""Intent classification and routing to domain agents.

Two-tier strategy:
  1. LLM classifier (Qwen 1.5B) — primary, high accuracy
  2. Keyword match — fallback on LLM error or timeout
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from app.config import settings

# ── Intent result ────────────────────────────────────────────────────────────


@dataclass
class IntentResult:
    intent_name: str
    target_agent: str  # "pre_sales" | "during_sales" | "after_sales"
    confidence: float
    classifier: str = "keyword"  # "llm" | "keyword"


# ── LLM classification prompt ────────────────────────────────────────────────

_INTENT_SYSTEM_PROMPT = """你是电商客服意图分类器。根据用户消息，判断应该由哪个 Agent 处理。

Agent 列表及其职责：

1. **pre_sales（售前）**：商品咨询、规格参数、价格查询、库存、促销活动、优惠券、会员权益、积分、商品对比和推荐
2. **during_sales（售中）**：下单问题、支付失败、付款方式、修改订单、取消订单、收货地址修改、发票开具
3. **after_sales（售后）**：物流查询、快递进度、退货申请、退款进度、换货、质量问题投诉、售后维权

输出规则：
- 只返回 JSON，不要解释
- 边界模糊的问题默认归类为 after_sales（售后优先，安全保守）
- 问候语、感谢等非业务消息归类为 pre_sales

输出格式：
{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.95}
"""

_FEW_SHOT_EXAMPLES = [
    # 售前
    ("iPhone 15 Pro 多少钱？", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.98}'),
    ("这个手机和那个手机哪个好？", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.92}'),
    ("有什么优惠活动？", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.95}'),
    ("PLUS 会员有什么权益？", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.97}'),
    ("256G 的有货吗？", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.94}'),
    ("你好", '{"intent_name": "query_product", "target_agent": "pre_sales", "confidence": 0.90}'),
    # 售中
    ("我付了钱但显示没成功", '{"intent_name": "place_order", "target_agent": "during_sales", "confidence": 0.96}'),
    ("帮我改一下收货地址", '{"intent_name": "place_order", "target_agent": "during_sales", "confidence": 0.97}'),
    ("我要开发票", '{"intent_name": "place_order", "target_agent": "during_sales", "confidence": 0.98}'),
    ("支付失败了怎么重试？", '{"intent_name": "place_order", "target_agent": "during_sales", "confidence": 0.95}'),
    ("订单可以取消吗？", '{"intent_name": "place_order", "target_agent": "during_sales", "confidence": 0.93}'),
    # 售后
    ("快递到哪了？", '{"intent_name": "check_logistics", "target_agent": "after_sales", "confidence": 0.99}'),
    ("我要退货退款", '{"intent_name": "check_logistics", "target_agent": "after_sales", "confidence": 0.98}'),
    ("收到的东西是坏的", '{"intent_name": "check_logistics", "target_agent": "after_sales", "confidence": 0.97}'),
    ("退款什么时候到账？", '{"intent_name": "check_logistics", "target_agent": "after_sales", "confidence": 0.96}'),
    ("快递显示签收了但我没收到", '{"intent_name": "check_logistics", "target_agent": "after_sales", "confidence": 0.94}'),
]


def _classify_llm(user_query: str) -> IntentResult | None:
    """Use Qwen 1.5B to classify intent. Returns None on failure (→ fallback to keyword)."""
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            timeout=5.0,  # fast timeout for classification
        )

        messages: list[dict] = [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
        ]
        for user_msg, assistant_msg in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": user_query})

        t0 = time.monotonic()
        resp = client.chat.completions.create(
            model=settings.intent_model,
            messages=messages,
            temperature=0.0,
            max_tokens=128,
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or ""
        data = json.loads(raw)

        target = data.get("target_agent", "pre_sales")
        if target not in ("pre_sales", "during_sales", "after_sales"):
            target = "pre_sales"

        return IntentResult(
            intent_name=data.get("intent_name", "query_product"),
            target_agent=target,
            confidence=float(data.get("confidence", 0.7)),
            classifier="llm",
        )
    except Exception:
        return None


# ── Keyword fallback (kept from original implementation) ──────────────────────

_INTENT_RULES: list[tuple[list[str], str, str]] = [
    (
        ["商品", "有没有", "多少钱", "价格", "规格", "颜色", "内存", "配置",
         "对比", "哪个好", "推荐", "优惠", "优惠券", "促销", "打折", "活动",
         "会员", "积分", "权益", "库存", "有货", "有现货", "什么时候到货"],
        "query_product",
        "pre_sales",
    ),
    (
        ["下单", "支付", "付款", "付了", "没成功", "地址", "改地址",
         "发票", "开票", "未支付", "取消订单", "修改订单"],
        "place_order",
        "during_sales",
    ),
    (
        ["物流", "快递", "发货", "到哪了", "货到哪", "单号", "退货",
         "退款", "换货", "投诉", "质量问题", "坏了", "退钱", "赔付"],
        "check_logistics",
        "after_sales",
    ),
]


def _classify_keyword(user_query: str) -> IntentResult:
    """Simple keyword-based intent classification (fallback)."""
    best_score = 0.0
    best_intent = "query_product"
    best_agent = "pre_sales"

    for keywords, intent_name, agent in _INTENT_RULES:
        score = sum(1 for kw in keywords if kw in user_query) / len(keywords)
        if score > best_score:
            best_score = score
            best_intent = intent_name
            best_agent = agent

    confidence = min(best_score * 3, 0.98) if best_score > 0 else 0.5
    return IntentResult(
        intent_name=best_intent,
        target_agent=best_agent,
        confidence=round(confidence, 2),
        classifier="keyword",
    )


# ── Public API ────────────────────────────────────────────────────────────────


def classify_intent(user_query: str) -> IntentResult:
    """Classify user intent with LLM primary + keyword fallback."""
    result = _classify_llm(user_query)
    if result is not None:
        return result
    return _classify_keyword(user_query)


def route_to_agent(intent: IntentResult):
    """Return the appropriate agent instance based on intent."""
    if intent.target_agent == "during_sales":
        from app.agents.during_sales.agent import during_sales_agent

        return during_sales_agent
    if intent.target_agent == "after_sales":
        from app.agents.after_sales.agent import after_sales_agent

        return after_sales_agent
    # Default: pre_sales
    from app.agents.pre_sales.agent import pre_sales_agent

    return pre_sales_agent
