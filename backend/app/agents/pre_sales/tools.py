"""Pre-sales agent tools: 查商品、查库存、查优惠券、查会员等级"""

from __future__ import annotations

import time

from app.tools.base import ToolDefinition, ToolParameterDef, ToolResult
from app.tools.registry import tool_registry

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_PRODUCTS: dict[str, dict] = {
    "iphone15": {
        "name": "iPhone 15 Pro",
        "price": 8999,
        "specs": "256GB, 黑色, A17 Pro 芯片, 48MP 三摄",
        "colors": ["黑色", "原色钛金属", "蓝色钛金属", "白色钛金属"],
        "storage": ["128GB", "256GB", "512GB", "1TB"],
    },
    "airpods": {
        "name": "AirPods Pro 2",
        "price": 1899,
        "specs": "主动降噪, USB-C 充电, H2 芯片",
        "colors": ["白色"],
    },
}

_MOCK_INVENTORY: dict[str, list[dict]] = {
    "iphone15-256": [
        {"warehouse": "北京仓", "stock": 156, "eta_days": 1},
        {"warehouse": "上海仓", "stock": 89, "eta_days": 2},
        {"warehouse": "广州仓", "stock": 234, "eta_days": 1},
    ],
    "iphone15-512": [
        {"warehouse": "北京仓", "stock": 0, "eta_days": -1},
        {"warehouse": "上海仓", "stock": 12, "eta_days": 3},
    ],
}

_MOCK_COUPONS: list[dict] = [
    {"code": "NEW100", "type": "新人券", "amount": 100, "min_spend": 500, "valid_until": "2026-06-30"},
    {"code": "618SALE", "type": "大促券", "amount": 50, "min_spend": 300, "valid_until": "2026-06-18"},
    {"code": "PLUS95", "type": "会员券", "amount": 0, "desc": "PLUS 会员 95 折", "valid_until": "长期"},
]

_MOCK_MEMBERSHIPS: dict[str, dict] = {
    "user_001": {"level": "PLUS 会员", "points": 12580, "benefits": ["全场 95 折", "双倍积分", "免运费", "专属客服"]},
    "user_002": {"level": "普通会员", "points": 2100, "benefits": ["积分抵现", "生日月双倍积分"]},
    "user_003": {"level": "黄金会员", "points": 5600, "benefits": ["98 折", "1.5 倍积分", "每月 2 张免运费券"]},
}


# ── Tool handlers ─────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Remove spaces and common separators for fuzzy matching."""
    return text.lower().replace(" ", "").replace("-", "").replace("_", "")


def _query_product(product_name: str = "", specs: str = "") -> ToolResult:
    """Query product information."""
    t0 = time.monotonic()
    q = _normalize(product_name)
    results = []
    for key, info in _MOCK_PRODUCTS.items():
        if not q or q in _normalize(key) or _normalize(info.get("name", "")) in q:
            results.append(info)
    if not results:
        return ToolResult(success=True, data={"products": [], "message": "未找到匹配商品"}, duration_ms=int((time.monotonic() - t0) * 1000))
    return ToolResult(success=True, data={"products": results}, duration_ms=int((time.monotonic() - t0) * 1000))


def _check_inventory(product_name: str = "", sku: str = "") -> ToolResult:
    """Check inventory for a product."""
    t0 = time.monotonic()
    key = f"iphone15-256" if "256" in product_name or "256" in sku else "iphone15-512"
    data = _MOCK_INVENTORY.get(key, [])
    return ToolResult(success=True, data={"product": product_name or sku, "inventory": data}, duration_ms=int((time.monotonic() - t0) * 1000))


def _check_coupons(user_id: str = "") -> ToolResult:
    """Check available coupons."""
    t0 = time.monotonic()
    return ToolResult(success=True, data={"coupons": _MOCK_COUPONS}, duration_ms=int((time.monotonic() - t0) * 1000))


def _check_membership(user_id: str = "") -> ToolResult:
    """Check user membership level and benefits."""
    t0 = time.monotonic()
    info = _MOCK_MEMBERSHIPS.get(user_id, _MOCK_MEMBERSHIPS["user_002"])
    return ToolResult(success=True, data={"membership": info}, duration_ms=int((time.monotonic() - t0) * 1000))


# ── Register tools ────────────────────────────────────────────────────────────

def register_pre_sales_tools(agent_id: int = 1) -> None:
    # Also register shared web_search tool
    from app.tools.web_search import register_web_search
    register_web_search(agent_id=None)

    tool_registry.register(
        ToolDefinition(
            name="query_product",
            display_name="查询商品",
            description="查询商品信息：名称、价格、规格、颜色、存储选项等",
            parameters=[
                ToolParameterDef("product_name", "string", "商品名称关键词", is_required=True),
                ToolParameterDef("specs", "string", "规格筛选（可选）"),
            ],
        ),
        _query_product,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="check_inventory",
            display_name="查询库存",
            description="查询商品在各仓库的库存状态和预计送达时间",
            parameters=[
                ToolParameterDef("product_name", "string", "商品名称", is_required=True),
                ToolParameterDef("sku", "string", "具体 SKU 编号（可选）"),
            ],
        ),
        _check_inventory,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="check_coupons",
            display_name="查询优惠券",
            description="查询当前可用的优惠券、促销活动和适用条件",
            parameters=[
                ToolParameterDef("user_id", "string", "用户 ID（可选，默认查询全平台优惠）"),
            ],
        ),
        _check_coupons,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="check_membership",
            display_name="查询会员等级",
            description="查询用户会员等级、积分余额和专属权益",
            parameters=[
                ToolParameterDef("user_id", "string", "用户 ID", is_required=True),
            ],
        ),
        _check_membership,
        agent_id=agent_id,
    )
