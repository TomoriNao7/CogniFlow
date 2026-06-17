"""After-sales agent tools: 查物流、查订单、发起退款、查退款进度"""

from __future__ import annotations

import time
from datetime import datetime

from app.tools.base import ToolDefinition, ToolParameterDef, ToolResult
from app.tools.registry import tool_registry

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_LOGISTICS: dict[str, dict] = {
    "ORD20260607002": {
        "order_id": "ORD20260607002",
        "carrier": "顺丰速运",
        "tracking_no": "SF1234567890123",
        "status": "运输中",
        "status_detail": "快件已到达【北京朝阳分拣中心】",
        "estimated_delivery": "2026-06-11",
        "history": [
            {"time": "2026-06-08 10:00", "status": "已揽收", "location": "上海市"},
            {"time": "2026-06-09 08:30", "status": "运输中", "location": "上海 → 北京"},
            {"time": "2026-06-10 14:00", "status": "到达分拣中心", "location": "北京朝阳"},
        ],
    },
    "ORD20260605004": {
        "order_id": "ORD20260605004",
        "carrier": "中通快递",
        "tracking_no": "ZT9876543210987",
        "status": "已签收",
        "status_detail": "快件已由本人签收",
        "estimated_delivery": "2026-06-09",
        "history": [
            {"time": "2026-06-06 16:00", "status": "已揽收", "location": "广州市"},
            {"time": "2026-06-08 10:00", "status": "运输中", "location": "广州 → 北京"},
            {"time": "2026-06-09 15:30", "status": "已签收", "location": "北京"},
        ],
    },
}

_MOCK_REFUNDS: list[dict] = [
    {
        "refund_id": "REF20260610001",
        "order_id": "ORD20260607002",
        "amount": 1899.00,
        "reason": "商品与描述不符",
        "status": "处理中",
        "status_detail": "退款申请已提交，等待商家审核",
        "created_at": "2026-06-10 09:00:00",
        "estimated_refund": "3-5 个工作日",
    },
]

_REFUND_POLICY = {
    "conditions": [
        "商品未使用、包装完好、不影响二次销售",
        "自签收之日起 7 天内可申请无理由退货",
        "质量问题 15 天内可申请退货/换货",
    ],
    "not_applicable": [
        "已拆封的消耗品（如食品、化妆品）",
        "定制商品",
        "已激活的数码产品（如手机、电脑）",
    ],
    "refund_timeline": "审核通过后 3-5 个工作日到账",
    "return_shipping": "质量问题商家承担运费，无理由退货用户承担运费",
}


# ── Tool handlers ─────────────────────────────────────────────────────────────

def _check_logistics(order_id: str = "") -> ToolResult:
    """Check logistics status for an order."""
    t0 = time.monotonic()
    info = _MOCK_LOGISTICS.get(order_id)
    if not info:
        return ToolResult(success=False, error=f"未找到订单 {order_id} 的物流信息，请确认订单号是否正确")
    return ToolResult(
        success=True,
        data=info,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _query_order(order_id: str = "") -> ToolResult:
    """Query order details."""
    t0 = time.monotonic()
    # Share mock orders pool — in production this queries the database
    all_orders = {
        "ORD20260607002": {
            "order_id": "ORD20260607002",
            "status": "paid",
            "amount": 1899.00,
            "items": [{"name": "AirPods Pro 2", "qty": 1, "price": 1899.00}],
            "created_at": "2026-06-07 09:15:00",
            "shipping_address": "北京市朝阳区 XXX 路 100 号",
            "payment_method": "微信支付",
        },
        "ORD20260608001": {
            "order_id": "ORD20260608001",
            "status": "unpaid",
            "amount": 8999.00,
            "items": [{"name": "iPhone 15 Pro 256GB", "qty": 1, "price": 8999.00}],
            "created_at": "2026-06-08 14:30:00",
        },
        "ORD20260605004": {
            "order_id": "ORD20260605004",
            "status": "completed",
            "amount": 299.00,
            "items": [{"name": "手机壳 MagSafe", "qty": 1, "price": 299.00}],
            "created_at": "2026-06-05 11:00:00",
            "shipping_address": "北京市海淀区 YYY 路 200 号",
        },
    }
    order = all_orders.get(order_id)
    if not order:
        return ToolResult(success=False, error=f"未找到订单 {order_id}")
    return ToolResult(
        success=True,
        data=order,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _request_refund(order_id: str = "", reason: str = "") -> ToolResult:
    """Request a refund for a paid order."""
    t0 = time.monotonic()
    if order_id not in ("ORD20260607002", "ORD20260605004"):
        return ToolResult(success=False, error=f"订单 {order_id} 不存在或不属于您")
    if order_id == "ORD20260605004":
        return ToolResult(
            success=False,
            error="该订单已超过 7 天无理由退货期限，请联系人工客服处理",
            data={"order_id": order_id, "policy": _REFUND_POLICY},
        )
    refund_id = f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return ToolResult(
        success=True,
        data={
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": 1899.00,
            "reason": reason or "未填写",
            "status": "已提交",
            "status_detail": "退款申请已提交，等待商家审核",
            "estimated_refund": "审核通过后 3-5 个工作日到账",
            "policy": _REFUND_POLICY,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def _check_refund_status(refund_id: str = "") -> ToolResult:
    """Check refund progress."""
    t0 = time.monotonic()
    refund = next((r for r in _MOCK_REFUNDS if r["refund_id"] == refund_id), None)
    if not refund:
        # Return a generic processing status for any refund_id
        return ToolResult(
            success=True,
            data={
                "refund_id": refund_id,
                "status": "银行处理中",
                "status_detail": "退款已通过审核，等待银行到账（通常 1-3 个工作日）",
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    return ToolResult(
        success=True,
        data=refund,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


# ── Register tools ────────────────────────────────────────────────────────────

def register_after_sales_tools(agent_id: int = 3) -> None:
    from app.tools.web_search import register_web_search
    register_web_search(agent_id=None)

    tool_registry.register(
        ToolDefinition(
            name="check_logistics",
            display_name="查询物流",
            description="查询订单物流状态、快递公司、运单号和配送进度",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
            ],
        ),
        _check_logistics,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="query_order",
            display_name="查询订单",
            description="查询订单详细信息：状态、金额、商品、收货地址",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
            ],
        ),
        _query_order,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="request_refund",
            display_name="发起退款",
            description="为已支付订单发起退款/退货申请，需填写退款原因",
            parameters=[
                ToolParameterDef("order_id", "string", "订单编号", is_required=True),
                ToolParameterDef("reason", "string", "退款原因（如：质量问题、不想要了等）", is_required=True),
            ],
        ),
        _request_refund,
        agent_id=agent_id,
    )

    tool_registry.register(
        ToolDefinition(
            name="check_refund_status",
            display_name="查询退款进度",
            description="查询退款申请的处理进度和预计到账时间",
            parameters=[
                ToolParameterDef("refund_id", "string", "退款单号", is_required=True),
            ],
        ),
        _check_refund_status,
        agent_id=agent_id,
    )
