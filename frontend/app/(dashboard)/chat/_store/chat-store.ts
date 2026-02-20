"use client";

import { create } from "zustand";
import type { Conversation, Message } from "@/types/api-types";

export type ChatState = {
  conversationId: string | null;
  messages: Message[];
  streamingContent: string;
  previewMessageId: string | null;
  applyTargetId: string | null;
  historyList: Conversation[];
  historyLoading: boolean;
  input: string;
  loading: boolean;
  stopTriggered: boolean;
};

export type ChatActions = {
  setConversationId: (id: string | null) => void;
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
  setStreamingContent: (s: string) => void;
  setPreviewMessageId: (id: string | null) => void;
  setApplyTargetId: (id: string | null) => void;
  setHistoryList: (list: Conversation[] | ((prev: Conversation[]) => Conversation[])) => void;
  setHistoryLoading: (v: boolean) => void;
  setInput: (s: string) => void;
  setLoading: (v: boolean) => void;
  setStopTriggered: (v: boolean) => void;
  resetForNewChat: () => void;
  reset: () => void;
};

const initialState: ChatState = {
  conversationId: null,
  messages: [],
  streamingContent: "",
  previewMessageId: null,
  applyTargetId: null,
  historyList: [],
  historyLoading: false,
  input: "",
  loading: false,
  stopTriggered: false,
};

export const useChatStore = create<ChatState & ChatActions>((set) => ({
  ...initialState,
  setConversationId: (id) => set({ conversationId: id }),
  setMessages: (arg) =>
    set((s) => ({
      messages: typeof arg === "function" ? arg(s.messages) : arg,
    })),
  setStreamingContent: (s) => set({ streamingContent: s }),
  setPreviewMessageId: (id) => set({ previewMessageId: id }),
  setApplyTargetId: (id) => set({ applyTargetId: id }),
  setHistoryList: (arg) =>
    set((s) => ({
      historyList: typeof arg === "function" ? arg(s.historyList) : arg,
    })),
  setHistoryLoading: (v) => set({ historyLoading: v }),
  setInput: (s) => set({ input: s }),
  setLoading: (v) => set({ loading: v }),
  setStopTriggered: (v) => set({ stopTriggered: v }),
  resetForNewChat: () =>
    set({
      conversationId: null,
      messages: [],
      streamingContent: "",
      previewMessageId: null,
      applyTargetId: null,
      loading: false,
      stopTriggered: false,
    }),
  reset: () => set({ ...initialState }),
}));
