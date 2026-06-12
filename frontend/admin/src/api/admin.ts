/** Admin panel API client — dashboard, conversations, feedback, knowledge, agents, tools. */

const BASE = 'http://localhost:8000/api/v1/admin';

export interface DashboardStats {
  total_conversations: number;
  today_conversations: number;
  active_conversations: number;
  total_messages: number;
  handoff_count: number;
  satisfaction: number;
  total_feedback: number;
  agent_distribution: { name: string; count: number }[];
}

export interface ConvRow {
  id: number;
  user_id: number;
  agent_name: string;
  status: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
  created_at: string | null;
}

export interface ConvMessages {
  conversation_id: number;
  messages: { id: number; role: string; content: string; created_at: string | null }[];
}

export interface FbStats {
  total: number;
  helpful: number;
  unhelpful: number;
  satisfaction_rate: number;
  pending_review: number;
}

export interface FbRow {
  id: number;
  message_id: number;
  rating: string;
  reason: string | null;
  review_status: string;
  created_at: string | null;
}

export interface DocRow {
  id: number;
  title: string;
  file_type: string;
  split_method: string;
  chunk_count: number;
  total_retrievals: number;
  status: string;
  version: number;
  created_at: string | null;
}

export interface KnowledgeStats {
  total_documents: number;
  total_chunks: number;
  total_retrievals: number;
}

export interface AgentRow {
  id: number;
  name: string;
  display_name: string;
  model: string;
  system_prompt: string | null;
  status: string;
  retrieval_params: Record<string, string>;
}

export interface ToolRow {
  id: number;
  name: string;
  display_name: string;
  description: string;
  http_method: string;
  endpoint_url: string;
  version: string;
  status: string;
  timeout_ms: number;
  retry_count: number;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Dashboard
export const fetchDashboard = () => fetchJson<DashboardStats>(`${BASE}/dashboard`);

// Conversations
export const fetchConversations = (page = 1, status = '') =>
  fetchJson<{ rows: ConvRow[]; page: number }>(`${BASE}/conversations?page=${page}&page_size=50&status=${status}`);

export const fetchConversationMessages = (convId: number) =>
  fetchJson<ConvMessages>(`${BASE}/conversations/${convId}/messages`);

// Feedback
export const fetchFeedback = (page = 1, rating = '') =>
  fetchJson<{ rows: FbRow[]; page: number }>(`${BASE}/feedback?page=${page}&page_size=50&rating=${rating}`);

export const fetchFeedbackStats = () => fetchJson<FbStats>(`${BASE}/feedback/stats`);

// Knowledge
export const fetchKnowledge = (page = 1) =>
  fetchJson<{ rows: DocRow[]; page: number }>(`${BASE}/knowledge?page=${page}&page_size=50`);

export const fetchKnowledgeStats = () => fetchJson<KnowledgeStats>(`${BASE}/knowledge/stats`);

// Agents
export const fetchAgents = () => fetchJson<{ agents: AgentRow[] }>(`${BASE}/agents`);

export const updateAgent = (id: number, body: Record<string, unknown>) =>
  fetchJson<{ status: string }>(`${BASE}/agents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

// Tools
export const fetchAdminTools = () => fetchJson<{ tools: ToolRow[] }>(`${BASE}/tools`);

// Upload
export interface UploadResult {
  status: string;
  filename: string;
  document_id: number;
  chunks: number;
  split_method: string;
  file_type: string;
  elapsed_ms: number;
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/knowledge/upload`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
