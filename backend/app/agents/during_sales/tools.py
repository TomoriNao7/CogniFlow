"""During-sales agent tools: 查未支付订单、查询支付状态、修改地址、申请发票"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from app.tools.base import ToolDefinition, ToolParameterDef, ToolResult
from app.tools.registry import tool_registry

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_ORDERS: list[dict] = [
    {
        "order_id": "ORD20260608001",
        "status": "unpaid",
        "amount": 8999.00,
        "items": [{"name": "iPhone 15 Pro 256GB", "qty": 1, "price": 8999.00}],
        "created_at": "2026-06-08 14:30:00",
        "expires_at": "2026-06-08 20:30:00",
        "payment_method": "支付宝",
    },
    {
        "order_id": "ORD20260607002",
        "status": "paid",
        "amount": 1899.00,
        "items": [{"name": "AirPods Pro 2", "qty": 1, "price": 1899.00}],
        "created_at": "2026-06-07 09:15:00",
        "shipping_address": "北京市朝阳区 XXX 路 100 号",
        "payment_method": "微信支付",
    },
    {
        "order_id": "ORD20260609003",
        "status": "payment_failed",
        "amount": 589.00,
        "items": [{"name": "机械键盘 K8 Pro", "qty": 1, "price": 589.00}],
        "created_at": "2026-06-09 10:00:00",
        "fail_reason": "银行卡余额不足",
        "payment_method": "银行卡",
    },
]

_MOCK_PAYMENT_METHODS = [
    {"method": "支付宝", "supported": True, "limit_single": 50000},
    {"method": "微信支付", "supported": True, "limit_single": 20000},
    {"method": "银行卡", "supported": True, "limit_single": 100000},
    {"method": "花呗分期", "supported": True, "limit_single": 30000, "installments": [3, 6, 12]},
]


def _generate_order_id() -> str:
    return f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"


# ── Tool handlers ─────────────────────────────────────────────────────────────

def _query_unpaid_order(user_id: str = "") -> ToolResult:
    """Query unpaid or in-process orders for a user."""
    t0 = time.monotonic()
    unpaid = [o for o in _MOCK_ORDERS if o["status"] in ("unpaid", "payment_failed")]
    result = {
        "orders": unpaid,
        "count": len(unpaid),
        "tip": "请在订单过期前完成支付" if unpaid else "当前没有待支付订单",
    }
    return ToolResult(
        success=True,
        data=result,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _check_payment_status(order_id: str = "") -> ToolResult:
    """Check payment status for a specific order."""
    t0 = time.monotonic()
    order = next((o for o in _MOCK_ORDERS if o["order_id"] == order_id), None)
    if not order:
        return ToolResult(success=False, error=f"未找到订单 {order_id}", data=None)
    payment_info = {
        "order_id": order["order_id"],
        "status": order["status"],
        "amount": order["amount"],
        "payment_method": order.get("payment_method", "未知"),
        "fail_reason": order.get("fail_reason"),
        "available_methods": _MOCK_PAYMENT_METHODS,
    }
    return ToolResult(
        success=True,
        data=payment_info,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _modify_address(order_id: str = "", new_address: str = "") -> ToolResult:
    """Modify shipping address for an unpaid/shipped order."""
    t0 = time.monotonic()
    order = next((o for o in _MOCK_ORDERS if o["order_id"] == order_id), None)
    if not order:
        return ToolResult(success=False, error=f"未找到订单 {order_id}", data=None)
    if order["status"] != "paid":
        return ToolResult(
            success=False,
            error="仅已支付未发货的订单支持修改地址",
            data={"order_id": order_id, "current_status": order["status"]},
        )
    # Simulate address change
    old_addr = order.get("shipping_address", "")
    order["shipping_address"] = new_address
    return ToolResult(
        success=True,
        data={
            "order_id": order_id,
            "old_address": old_addr,
            "new_address": new_address,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _apply_invoice(order_id: str = "", invoice_type: str = "电子发票", title: str = "个人") -> ToolResult:
    """Apply for an invoice for a paid order."""
    t0 = time.monotonic()
    order = next((o for o in _MOCK_ORDERS if o["order_id"] == order_id), None)
    if not order:
        return ToolResult(success=False, error=f"未找到订单 {order_id}", data=None)
    if order["status"] != "paid":
        return ToolResult(
            success=False,
            error="仅已支付订单可申请发票",
            data={"order_id": order_id, "current_status": order["status"]},
        )
    invoice_id = _generate_order_id()
    return ToolResult(
        success=True,
        data={
            "invoice_id": invoice_id,
            "order_id": order_id,
            "amount": order["amount"],
            "type": invoice_type,
            "title": title,
            "status": "已开具",
            "download_url": f"https://invoice.example.com/{invoice_id}.pdf",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


# ── Register tools ────────────────────────────────────────────────────────────

def register_during_sales_tools(agent_id: int = 2) -> None:
    from app.tools.web_search import register_web_search
    register_web_search(agent_id=None)

    tool_registry.register(
        ToolDefinition(
            name="query_unpaid_order",
            display_name="查询未支付订单",
            description="查询用户当前未支付或支付失败的订单列表",
            parameters=[
                ToolParameterDef("user_id", "string", "用户 ID（可选）"),
            ],
        ),
        _query_unpaid_order,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="check_payment_status",
            display_name="查询支付状态",
            description="查询指定订单的支付状态、失败原因及可用支付方式",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
            ],
        ),
        _check_payment_status,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="modify_address",
            display_name="修改收货地址",
            description="修改未发货订单的收货地址（需二次确认）",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
                ToolParameterDef("new_address", "string", "新收货地址（完整地址）", is_required=True),
            ],
        ),
        _modify_address,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="apply_invoice",
            display_name="申请发票",
            description="为已支付订单申请电子发票或纸质发票",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
                ToolParameterDef("invoice_type", "string", "发票类型：电子发票 / 纸质发票"),
                ToolParameterDef("title", "string", "发票抬头：个人 / 企业名称"),
            ],
        ),
        _apply_invoice,
        agent_id=agent_id,
    )
