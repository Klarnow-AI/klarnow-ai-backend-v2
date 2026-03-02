import { API_BASE } from "@/lib/utils";
import { getHeaders, getToken, handleUnauthorized } from "@/lib/http";
import { api } from "@/lib/http";
import type {
  Conversation,
  ConversationListResponse,
  Message,
  MessageListResponse,
} from "@/types/api-types";

const CHAT_PREFIX = "/api/v1/chat";

export const chat = {
  listConversations: (packId?: string) =>
    api<ConversationListResponse>(
      packId
        ? `${CHAT_PREFIX}/conversations?pack_id=${packId}`
        : `${CHAT_PREFIX}/conversations`
    ),
  createConversation: (packId?: string) =>
    api<Conversation>(`${CHAT_PREFIX}/conversations`, {
      method: "POST",
      body: JSON.stringify({
        pack_id: packId ?? null,
        day_context: null,
      }),
    }),
  getConversation: (id: string) =>
    api<Conversation>(`${CHAT_PREFIX}/conversations/${id}`),
  deleteConversation: (id: string) =>
    api<void>(`${CHAT_PREFIX}/conversations/${id}`, { method: "DELETE" }),
  getMessages: (conversationId: string) =>
    api<MessageListResponse>(
      `${CHAT_PREFIX}/conversations/${conversationId}/messages`
    ),
  sendMessage: (
    conversationId: string,
    body: {
      content: string;
      mode?: "use" | "preview" | "apply";
      apply_to_message_id?: string | null;
    },
    stream = false,
    signal?: AbortSignal
  ): Promise<Response> => {
    const url = `${API_BASE}${CHAT_PREFIX}/conversations/${conversationId}/messages${
      stream ? "?stream=true" : ""
    }`;
    return fetch(url, {
      method: "POST",
      headers: getHeaders() as HeadersInit,
      body: JSON.stringify(body),
      signal,
    }).then((res) => {
      if (res.status === 401 && getToken()) handleUnauthorized();
      return res;
    });
  },
};
