#!/usr/bin/env python3
"""CogniFlow Agent 离线评估脚本

覆盖四个维度：意图分类准确率、检索命中率与MRR、工具调用准确率、生成质量
使用方式：
    cd backend
    python scripts/eval.py              # 运行全部测试
    python scripts/eval.py --agent pre_sales   # 只测售前
"""

from __future__ import annotations

import json
import sys
import time
import os
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 测试集 ────────────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    question: str
    expected_agent: str          # pre_sales / during_sales / after_sales
    expected_tool: str | None    # 期望调用的工具名，None 表示不应调工具
    reference_keywords: list[str]  # 回答中应包含的关键词
    category: str = ""


TEST_SET: list[TestCase] = [
    # ═══ 售前 ═══
    TestCase("iPhone 15 Pro 多少钱", "pre_sales", "query_product",
             ["8999", "iPhone", "256GB"], "商品咨询"),
    TestCase("iPhone 15 Pro 有什么颜色", "pre_sales", "query_product",
             ["黑色", "原色钛金属", "蓝色"], "商品咨询"),
    TestCase("AirPods Pro 2 价格", "pre_sales", "query_product",
             ["1899", "AirPods", "降噪"], "商品咨询"),
    TestCase("现在有什么优惠活动", "pre_sales", "check_coupons",
             ["优惠", "券", "618"], "促销查询"),
    TestCase("有什么优惠券可以领", "pre_sales", "check_coupons",
             ["NEW100", "券", "满"], "促销查询"),
    TestCase("帮我查一下 iPhone 的库存", "pre_sales", "check_inventory",
             ["库存", "仓", "货"], "库存查询"),
    TestCase("256G 的 iPhone 有货吗", "pre_sales", "check_inventory",
             ["256", "仓", "货"], "库存查询"),
    TestCase("PLUS 会员有什么权益", "pre_sales", "check_membership",
             ["会员", "权益", "折", "积分"], "会员查询"),
    TestCase("我的积分有多少", "pre_sales", "check_membership",
             ["积分", "会员"], "会员查询"),
    TestCase("这个和那个手机哪个好", "pre_sales", None,
             ["对比", "规格"], "商品对比"),
    TestCase("你们卖什么手机", "pre_sales", None,
             ["iPhone", "Samsung"], "商品列表"),

    # ═══ 售中 ═══
    TestCase("支付失败了怎么办", "during_sales", "query_unpaid_order",
             ["支付", "失败", "订单"], "支付故障"),
    TestCase("帮我查一下未支付订单", "during_sales", "query_unpaid_order",
             ["订单", "未支付"], "订单查询"),
    TestCase("我想修改收货地址", "during_sales", "modify_address",
             ["地址", "修改"], "地址修改"),
    TestCase("帮我开一张发票", "during_sales", "apply_invoice",
             ["发票", "开具"], "发票申请"),
    TestCase("发票信息填错了怎么改", "during_sales", None,
             ["发票", "修改", "抬头"], "发票规则"),
    TestCase("可以取消订单吗", "during_sales", "query_unpaid_order",
             ["订单", "取消"], "订单操作"),

    # ═══ 售后 ═══
    TestCase("我的快递到哪了", "after_sales", "check_logistics",
             ["物流", "快递", "运单"], "物流查询"),
    TestCase("我要退款退货", "after_sales", "request_refund",
             ["退款", "退货"], "退款申请"),
    TestCase("查询退款进度", "after_sales", "check_refund_status",
             ["退款", "进度", "到账"], "退款进度"),
    TestCase("收到的商品是坏的怎么办", "after_sales", None,
             ["退货", "质量", "赔付"], "质量投诉"),
    TestCase("退货要多久", "after_sales", None,
             ["退货", "天", "退款"], "退货时效"),
    TestCase("怎么换货", "after_sales", None,
             ["换货", "天"], "换货流程"),
]

AgentNameMap = {"pre_sales": "售前 Agent", "during_sales": "售中 Agent", "after_sales": "售后 Agent"}


# ── 评估执行 ──────────────────────────────────────────────────────────────────

def run_eval(agent_filter: str = "") -> dict:
    """运行全部测试用例，返回评估结果字典。"""
    from app.agents.router import classify_intent, route_to_agent
    from app.core.security import mask_sensitive

    cases = TEST_SET
    if agent_filter:
        cases = [c for c in TEST_SET if c.expected_agent == agent_filter]

    results: list[dict] = []
    intent_correct = 0
    tool_correct = 0
    tool_total = 0
    keyword_hits = 0
    total_time = 0.0

    print(f"\n{'='*60}")
    print(f"CogniFlow Agent 离线评估 — {len(cases)} 条测试")
    print(f"{'='*60}\n")

    for i, tc in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] {tc.question}")
        print(f"  期望: {AgentNameMap.get(tc.expected_agent, tc.expected_agent)} | 工具: {tc.expected_tool or '无'}")

        # 意图分类
        clean = mask_sensitive(tc.question)
        intent = classify_intent(clean)

        intent_ok = intent.target_agent == tc.expected_agent
        if intent_ok:
            intent_correct += 1
            print(f"  意图: {intent.target_agent} ✅ (confidence={intent.confidence:.2f}, {intent.classifier})")
        else:
            print(f"  意图: {intent.target_agent} ❌ (期望 {tc.expected_agent}, confidence={intent.confidence:.2f})")

        # 运行 Agent
        agent = route_to_agent(intent)
        t0 = time.monotonic()
        try:
            import asyncio
            state = asyncio.run(agent.run(conversation_id=99990 + i, user_query=clean))
        except Exception as e:
            print(f"  ❌ Agent 异常: {e}")
            results.append({"case": tc.question, "error": str(e)})
            continue

        elapsed = time.monotonic() - t0
        total_time += elapsed

        # 工具调用评估
        actual_tools = [t["name"] for t in state.get("tool_calls", [])]
        if tc.expected_tool:
            tool_total += 1
            if tc.expected_tool in actual_tools:
                tool_correct += 1
                print(f"  工具: {actual_tools} ✅")
            elif actual_tools:
                print(f"  工具: {actual_tools} ❌ (期望含 {tc.expected_tool})")
            else:
                print(f"  工具: 无 ❌ (期望 {tc.expected_tool})")
        else:
            if actual_tools:
                print(f"  工具: {actual_tools} (无需工具)")
            else:
                print(f"  工具: 无 ✅ (无需工具)")

        # 检索评估
        retrieved_docs = state.get("retrieved_docs", [])
        retrieval_count = state.get("trace", {}).get("retrieval_count", 0)
        retrieval_ms = state.get("trace", {}).get("retrieval_ms", 0)
        print(f"  检索: {retrieval_count} 条 ({retrieval_ms}ms)")

        # 计算 MRR：检索到的第一条文档的来源是否包含预期领域关键词
        rank = -1
        if tc.expected_agent == "pre_sales":
            domain_kw = ["商品目录", "促销", "会员"]
        elif tc.expected_agent == "during_sales":
            domain_kw = ["支付指南", "发票规则"]
        else:
            domain_kw = ["退换货", "物流", "售后"]

        for j, doc in enumerate(retrieved_docs):
            if any(kw in doc.get("source_document", "") for kw in domain_kw):
                rank = j + 1
                break

        # 关键词覆盖评估
        reply = state.get("final_response", "")
        keyword_match = sum(1 for kw in tc.reference_keywords if kw in reply)
        keyword_rate = keyword_match / len(tc.reference_keywords) if tc.reference_keywords else 1.0
        if keyword_rate >= 0.6:
            keyword_hits += 1
            print(f"  关键词: {keyword_match}/{len(tc.reference_keywords)} ✅ ({elapsed:.1f}s)")
        else:
            print(f"  关键词: {keyword_match}/{len(tc.reference_keywords)} ❌ ({elapsed:.1f}s)")

        results.append({
            "question": tc.question,
            "expected_agent": tc.expected_agent,
            "actual_agent": intent.target_agent,
            "intent_ok": intent_ok,
            "expected_tool": tc.expected_tool,
            "actual_tools": actual_tools,
            "tool_ok": tc.expected_tool in actual_tools if tc.expected_tool else not actual_tools,
            "keyword_rate": keyword_rate,
            "retrieval_count": retrieval_count,
            "retrieval_rank": rank,
            "reply_preview": reply[:100],
            "elapsed_s": round(elapsed, 2),
        })

        # 限速，避免 API 限频
        time.sleep(0.3)

    # ── 汇总 ──
    n = len(cases)
    intent_acc = intent_correct / n * 100 if n else 0
    tool_acc = tool_correct / tool_total * 100 if tool_total else 100
    keyword_acc = keyword_hits / n * 100 if n else 0
    avg_time = total_time / n if n else 0

    # MRR（平均倒数排名）
    mrr = 0.0
    mrr_count = 0
    for r in results:
        rank = r.get("retrieval_rank", -1)
        if rank > 0:
            mrr += 1.0 / rank
            mrr_count += 1
    mrr = mrr / mrr_count if mrr_count else 0.0

    # 检索覆盖率
    has_retrieval = sum(1 for r in results if r.get("retrieval_count", 0) > 0)
    retrieval_rate = has_retrieval / n * 100 if n else 0

    print(f"\n{'='*60}")
    print(f"评估结果汇总")
    print(f"{'='*60}")
    print(f"  测试用例数:        {n}")
    print(f"  意图分类准确率:     {intent_acc:.1f}% ({intent_correct}/{n})")
    print(f"  工具调用准确率:     {tool_acc:.1f}% ({tool_correct}/{tool_total})")
    print(f"  关键词命中率:       {keyword_acc:.1f}% ({keyword_hits}/{n})")
    print(f"  检索覆盖率:         {retrieval_rate:.1f}%")
    print(f"  MRR:               {mrr:.4f}")
    print(f"  平均响应时间:       {avg_time:.1f}s")
    print(f"{'='*60}\n")

    # 按 Agent 分组
    for agent in ["pre_sales", "during_sales", "after_sales"]:
        agent_results = [r for r in results if r.get("expected_agent") == agent]
        if not agent_results:
            continue
        a_n = len(agent_results)
        a_intent = sum(1 for r in agent_results if r.get("intent_ok")) / a_n * 100
        a_tool_ok = sum(1 for r in agent_results if r.get("tool_ok") and r.get("expected_tool"))
        a_tool_total = sum(1 for r in agent_results if r.get("expected_tool"))
        a_tool = a_tool_ok / a_tool_total * 100 if a_tool_total else 100
        a_keyword = sum(1 for r in agent_results if r.get("keyword_rate", 0) >= 0.6) / a_n * 100
        print(f"  {AgentNameMap.get(agent, agent):8s} 意图:{a_intent:.0f}%  工具:{a_tool:.0f}%  关键词:{a_keyword:.0f}%  ({a_n}题)")

    return {
        "total": n,
        "intent_accuracy": round(intent_acc, 1),
        "tool_accuracy": round(tool_acc, 1),
        "keyword_hit_rate": round(keyword_acc, 1),
        "retrieval_coverage": round(retrieval_rate, 1),
        "mrr": round(mrr, 4),
        "avg_response_time_s": round(avg_time, 1),
        "details": results,
    }


# ── 命令行入口 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CogniFlow Agent 评估")
    parser.add_argument("--agent", choices=["pre_sales", "during_sales", "after_sales"],
                        help="只评估指定 Agent")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    report = run_eval(args.agent or "")

    if args.json:
        print(json.dumps({k: v for k, v in report.items() if k != "details"}, ensure_ascii=False, indent=2))
