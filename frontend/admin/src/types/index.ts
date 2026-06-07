/* Agent */
export interface Agent {
  id: number;
  name: string;
  displayName: string;
  model: string;
  systemPrompt: string;
  status: 'active' | 'inactive';
  retrievalParams: Record<string, string>;
}

/* Tool */
export interface Tool {
  id: number;
  name: string;
  displayName: string;
  description: string;
  endpointUrl: string;
  httpMethod: string;
  timeoutMs: number;
  retryCount: number;
  version: string;
  status: 'active' | 'inactive';
  parameters: ToolParameter[];
}

export interface ToolParameter {
  paramName: string;
  paramType: string;
  paramDesc: string;
  isRequired: boolean;
  defaultValue: string | null;
}

/* Knowledge Document */
export interface KnowledgeDoc {
  id: number;
  title: string;
  fileType: string;
  splitMethod: string;
  originalFilename: string;
  fileSizeBytes: number;
  version: number;
  status: 'active' | 'archived';
  chunkCount: number;
  totalRetrievals: number;
  uploadedBy: string;
  createdAt: string;
}

/* Conversation */
export interface Conversation {
  id: number;
  userNickname: string;
  agentName: string;
  status: 'active' | 'closed' | 'handoff';
  title: string;
  messageCount: number;
  satisfaction?: 'helpful' | 'unhelpful';
  lastMessageAt: string;
  createdAt: string;
}

export interface Message {
  id: number;
  conversationId: number;
  role: 'user' | 'bot' | 'system';
  content: string;
  traceData: Record<string, unknown> | null;
  createdAt: string;
}

/* Feedback */
export interface FeedbackItem {
  messageId: number;
  conversationId: number;
  rating: 'helpful' | 'unhelpful';
  reason: string | null;
  reviewStatus: 'pending' | 'reviewed' | 'ignored';
  createdAt: string;
}

/* Dashboard Stats */
export interface DashboardStats {
  totalConversations: number;
  activeConversations: number;
  handoffRate: number;
  satisfactionRate: number;
  dailyConversations: Array<{ date: string; count: number }>;
  agentDistribution: Array<{ agent: string; count: number }>;
  topBlindSpots: Array<{ query: string; count: number }>;
}

/* Auth */
export interface AdminUser {
  id: number;
  username: string;
  role: 'admin' | 'operator' | 'viewer';
}
