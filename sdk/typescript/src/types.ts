export type Run = {
  id: string;
  status: string;
  agent_id: string;
  input_text?: string | null;
  output_text?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  conversation_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type SseEvent = {
  event: string;
  data: Record<string, unknown>;
};

export type CreateRunOptions = {
  input: string;
  agentId?: string;
  pipeline?: string;
  workspaceId?: string;
  conversationId?: string;
  execute?: boolean;
  providerPolicy?: Record<string, unknown>;
};

export type AiceryClientOptions = {
  baseUrl: string;
  apiKey: string;
};
