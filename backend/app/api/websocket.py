"""Widget 长连接 WebSocket 端点，流式输出。"""

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.router import classify_intent, route_to_agent
from app.core.security import content_safety, mask_sensitive

router = APIRouter(tags=["websocket"])


@router.websocket("/chat")
async def websocket_chat(ws: WebSocket) -> None:
    await ws.accept()

    conversation_id = 1  # 生产环境从鉴权/握手拿
    failure_count = 0

    try:
        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
                user_message = data.get("message", "")
                conversation_id = data.get("conversation_id", conversation_id)
            except json.JSONDecodeError:
                user_message = raw

            if not user_message.strip():
                continue

            # 脱敏 + 安全检查
            clean_msg = mask_sensitive(user_message)
            safety = content_safety.check(clean_msg)
            if not safety.passed:
                await ws.send_json({
                    "type": "reply",
                    "content": content_safety.block_message(safety.severity, safety.action),
                    "done": True,
                })
                continue

            # 意图识别
            intent = classify_intent(clean_msg)
            agent = route_to_agent(intent)

            # 流式返回
            t0 = time.monotonic()
            await ws.send_json({
                "type": "intent",
                "intent": intent.intent_name,
                "target_agent": intent.target_agent,
                "confidence": intent.confidence,
                "classifier": intent.classifier,
            })

            try:
                state = await agent.run(
                    conversation_id=conversation_id,
                    user_query=clean_msg,
                )
            except Exception:
                failure_count += 1
                if failure_count >= 3:
                    await ws.send_json({
                        "type": "handoff",
                        "reason": "agent_failure",
                        "message": "抱歉，我暂时无法处理，正在为您转接人工客服...",
                    })
                    await ws.close()
                    return
                await ws.send_json({
                    "type": "reply",
                    "content": "抱歉，出了点问题，请稍后重试。",
                    "done": True,
                })
                continue

            failure_count = 0  # 成功则清零

            # 分块模拟流式
            full_reply = state["final_response"]
            chunk_size = 10
            for i in range(0, len(full_reply), chunk_size):
                chunk = full_reply[i : i + chunk_size]
                await ws.send_json({"type": "chunk", "content": chunk})
                await asyncio.sleep(0.02)  # 模拟流式延迟

            await ws.send_json({
                "type": "reply",
                "content": full_reply,
                "trace": state.get("trace"),
                "done": True,
            })

    except WebSocketDisconnect:
        pass  # 客户端断开
