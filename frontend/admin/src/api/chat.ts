/** HTTP chat API client for admin panel — connects to CogniFlow backend. */

const BASE_URL = 'http://localhost:8000/api/v1';

export interface ChatResponse {
  conversation_id: number;
  message_id: number | null;
  reply: string;
  intent: string;
  handoff: boolean;
  handoff_reason: string;
  trace: Record<string, unknown> | null;
}

export interface ToolInfo {
  name: string;
  display_name: string;
  description: string;
  version: string;
}

export async function sendMessage(
  conversationId: number,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      user_id: 'admin_test',
      message,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function listTools(): Promise<{ agent: string; tools: ToolInfo[] }> {
  const res = await fetch(`${BASE_URL}/tools`);
  return res.json();
}

export async function healthCheck(): Promise<{ status: string; agent: string }> {
  const res = await fetch('http://localhost:8000/health');
  return res.json();
}
