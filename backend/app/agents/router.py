"""Intent classification and routing to domain agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntentResult:
    intent_name: str
    target_agent: str  # "pre_sales" | "during_sales" | "after_sales"
    confidence: float


# Keyword-based fast routing for MVP. In production this uses Qwen 1.5B classifier.
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


def classify_intent(user_query: str) -> IntentResult:
    """Simple keyword-based intent classification.
    Production: replace with Qwen 1.5B model call via OpenAI-compatible API.
    """
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
    return IntentResult(intent_name=best_intent, target_agent=best_agent, confidence=confidence)


def route_to_agent(intent: IntentResult):
    """Return the appropriate agent instance based on intent."""
    if intent.target_agent == "pre_sales":
        from app.agents.pre_sales.agent import pre_sales_agent

        return pre_sales_agent
    # Other agents will be wired in later
    from app.agents.pre_sales.agent import pre_sales_agent

    return pre_sales_agent  # default fallback for MVP
