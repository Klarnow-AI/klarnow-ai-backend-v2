"use client";

import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import { Paperclip, Send, Stop } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { SearchInput } from "@/components/ui/search-input";
import type { BrandContext } from "@/app/api/generate/route";

type Message = {
  role: "user" | "assistant";
  content: string;
};

function parseFileTags(text: string): Record<string, string> {
  const files: Record<string, string> = {};
  const regex = /<file name="([^"]+)">([\s\S]*?)<\/file>/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const name = match[1].startsWith("/") ? match[1] : `/${match[1]}`;
    files[name] = match[2].trim();
  }
  return files;
}

function parseSummary(text: string): string {
  const match = text.match(/<summary>([\s\S]*?)<\/summary>/);
  return match ? match[1].trim() : "";
}

type BuilderChatPanelProps = {
  title: string;
  apiRoute: string;
  brandContext?: BrandContext | null;
  initialMessages?: Message[] | null;
  threadKey?: string | number | null;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  onFilesGenerated?: (
    files: Record<string, string>,
    messages: Message[]
  ) => void;
  onGeneratingChange?: (generating: boolean) => void;
};

export function BuilderChatPanel({
  title,
  apiRoute,
  brandContext,
  initialMessages,
  threadKey,
  emptyStateTitle = "Start a conversation",
  emptyStateDescription = "Describe what you\u2019d like to create and Klaro will generate it for you.",
  onFilesGenerated,
  onGeneratingChange,
}: BuilderChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages ?? []);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onFilesGeneratedRef = useRef(onFilesGenerated);
  const onGeneratingChangeRef = useRef(onGeneratingChange);
  onFilesGeneratedRef.current = onFilesGenerated;
  onGeneratingChangeRef.current = onGeneratingChange;

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    setMessages(initialMessages ?? []);
  }, [threadKey, initialMessages]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const sendRequest = useCallback(
    async (userContent: string, currentMessages: Message[]) => {
      setIsStreaming(true);
      onGeneratingChangeRef.current?.(true);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(apiRoute, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            brandContext: brandContext ?? undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.text();
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `Error: ${err}` },
          ]);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          accumulated += decoder.decode(value, { stream: true });
        }

        const extractedFiles = parseFileTags(accumulated);
        const hasFiles = Object.keys(extractedFiles).length > 0;
        const summary = parseSummary(accumulated);
        const displayMessage =
          summary ||
          (hasFiles ? "Done! Your design has been generated." : accumulated);

        if (hasFiles && onFilesGeneratedRef.current) {
          const messagesWithAssistant = [
            ...currentMessages,
            { role: "assistant" as const, content: displayMessage },
          ];
          onFilesGeneratedRef.current(extractedFiles, messagesWithAssistant);
        }

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: displayMessage },
        ]);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Stopped." },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
            },
          ]);
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        onGeneratingChangeRef.current?.(false);
        inputRef.current?.focus();
      }
    },
    [apiRoute, brandContext]
  );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMessage: Message = { role: "user", content: trimmed };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    sendRequest(trimmed, updatedMessages);
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 rounded-2xl border border-border bg-card overflow-hidden">
      <div className="shrink-0 px-4 py-3 border-b border-border bg-muted/30">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4"
        >
          {messages.length === 0 && !isStreaming && (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-8 min-h-[140px]">
              <p className="text-sm font-medium text-foreground mb-1.5">
                {emptyStateTitle}
              </p>
              <p className="text-sm text-muted-foreground max-w-[280px] leading-relaxed">
                {emptyStateDescription}
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "user" ? (
                <div className="rounded-2xl rounded-tr-md px-4 py-3 max-w-[85%] bg-primary text-primary-foreground">
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              ) : (
                <div className="rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%] text-sm text-foreground">
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                </div>
              )}
            </div>
          ))}

          {isStreaming && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%] text-sm text-foreground">
                <span className="whitespace-pre-wrap">{"\u00A0"}</span>
                <span
                  className="inline-block w-0.5 h-4 ml-0.5 align-middle bg-current animate-pulse"
                  aria-hidden
                />
              </div>
            </div>
          )}
        </div>

        <div className="shrink-0 px-4 py-3 border-t border-border">
          <form onSubmit={handleSubmit}>
            <SearchInput
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Klaro…"
              disabled={isStreaming}
              leftAdornment={
                <IconButton
                  type="button"
                  variant="ghost"
                  size="md"
                  aria-label="Attach file"
                >
                  <Paperclip className="h-4 w-4" />
                </IconButton>
              }
              rightAdornment={
                isStreaming ? (
                  <IconButton
                    type="button"
                    variant="solid"
                    size="md"
                    aria-label="Stop"
                    onClick={handleStop}
                  >
                    <Stop className="h-4 w-4" />
                  </IconButton>
                ) : (
                  <IconButton
                    type="submit"
                    variant="solid"
                    size="md"
                    aria-label="Send"
                    disabled={!input.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </IconButton>
                )
              }
            />
          </form>
        </div>
      </div>
    </div>
  );
}
