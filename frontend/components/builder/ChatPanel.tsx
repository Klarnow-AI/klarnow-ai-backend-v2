"use client";

import { useState, useRef, useEffect, useCallback, FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import {
  ChevronDown,
  ChevronLeft,
  Settings,
  Pencil,
  Star,
  HelpCircle,
  Send,
  Stop,
} from "@/components/icons";
import { SearchInput } from "@/components/ui/search-input";
import { IconButton } from "@/components/ui/icon-button";
import { Chip } from "@/components/ui/chip";
import { StylePicker } from "@/components/builder/StylePicker";
import { QuestionForm, type ParsedQuestion } from "@/components/builder/QuestionForm";
import type { BrandContext } from "@/app/api/generate/route";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatPanelProps = {
  brandContext?: BrandContext | null;
  packName?: string;
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

function parseQuestions(text: string): ParsedQuestion[] {
  const match = text.match(/<questions>([\s\S]*?)<\/questions>/);
  if (!match) return [];

  const qTagRegex =
    /<q\s+type="(select|text)"(?:\s+options="([^"]*)")?(?:\s+placeholder="([^"]*)")?>([\s\S]*?)<\/q>/g;
  const questions: ParsedQuestion[] = [];
  let qMatch;

  while ((qMatch = qTagRegex.exec(match[1])) !== null) {
    const type = qMatch[1] as "select" | "text";
    const options = qMatch[2]
      ?.split(",")
      .map((o) => o.trim())
      .filter(Boolean);
    const placeholder = qMatch[3];
    const questionText = qMatch[4].trim();
    questions.push({
      type,
      text: questionText,
      ...(options?.length ? { options } : {}),
      ...(placeholder ? { placeholder } : {}),
    });
  }

  if (questions.length > 0) return questions;

  // Fallback: plain list format
  return match[1]
    .split("\n")
    .map((l) => l.replace(/^[\s-]*/, "").trim())
    .filter(Boolean)
    .map((text) => ({
      type: "text" as const,
      text,
      placeholder: "Type your answer…",
    }));
}

function extractStreamingDisplay(text: string): string {
  // Show reasoning indicator while thinking block is active
  if (text.includes("<thinking>")) {
    // Still in thinking phase (no closing tag yet)
    if (!text.includes("</thinking>")) return "Reasoning…";
    // Thinking done — look for summary
  }

  const summaryMatch = text.match(/<summary>([\s\S]*?)<\/summary>/);
  if (summaryMatch) return summaryMatch[1].trim();

  // Partial summary still streaming
  const partialMatch = text.match(/<summary>([\s\S]*?)$/);
  if (partialMatch && partialMatch[1].trim()) return partialMatch[1].trim();

  // Thinking done but no summary yet — show "Building…"
  if (text.includes("</thinking>")) return "Building your website…";

  return "";
}

function buildAutoKickoff(brand: BrandContext, style: string): string {
  const name = brand.brandName || "my brand";
  const qualifier = [
    brand.industry ? `a ${brand.industry} brand` : null,
    brand.coreOffer ? `offering ${brand.coreOffer}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  const lines = [
    `Build a complete landing page for ${name}${qualifier ? ` — ${qualifier}` : ""}.`,
    `Design system: ${style}.`,
  ];

  const sections = ["Hero", "Features/Benefits"];
  if (brand.proofPoints?.length) sections.push("Social Proof");
  if (brand.audiencePersonas?.length) sections.push("Who It\u2019s For");
  sections.push("Call to Action", "Footer");
  lines.push(`Include sections: ${sections.join(", ")}.`);

  if (brand.heroAngle) lines.push(`Hero angle: \u201c${brand.heroAngle}\u201d`);
  if (brand.primaryCta) lines.push(`Primary CTA: \u201c${brand.primaryCta}\u201d`);

  lines.push(
    "Use all brand context available. Build it now — no questions needed. Make it visually stunning and production-ready.",
  );

  return lines.join("\n");
}

function getSuggestionChips(files: Record<string, string>): string[] {
  const allCode = Object.values(files).join(" ").toLowerCase();
  if (allCode.includes("describe your website to get started")) return [];

  const chips: string[] = [];

  if (!allCode.match(/pricing|price|\bplans?\b|\$\d/)) chips.push("Add pricing section");
  if (!allCode.match(/testimonial|review|what (our )?(clients|customers)/))
    chips.push("Add testimonials");
  if (!allCode.match(/contact.*form|<form|input.*email|email.*input/))
    chips.push("Add contact form");
  if (!allCode.match(/faq|frequently asked/)) chips.push("Add FAQ section");
  if (!allCode.match(/footer/)) chips.push("Add a footer");

  chips.push("Make it more minimal");
  chips.push("Make it bolder");

  return chips.slice(0, 5);
}

export function ChatPanel({ brandContext, packName }: ChatPanelProps) {
  const storeMessages = useProjectStore((s) => s.messages);
  const selectedStyle = useProjectStore((s) => s.selectedStyle);
  const files = useProjectStore((s) => s.files);
  const [messages, setMessagesLocal] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [activeQuestions, setActiveQuestions] = useState<ParsedQuestion[]>([]);
  const [streamingDisplay, setStreamingDisplay] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const hasAutoGenerated = useRef(false);
  const hasHydrated = useRef(false);
  const lastAutoFixedError = useRef<string | null>(null);

  const setMessages = useCallback(
    (updater: Message[] | ((prev: Message[]) => Message[])) => {
      setMessagesLocal(updater);
    },
    [],
  );

  useEffect(() => {
    if (useProjectStore.getState().messages !== messages) {
      useProjectStore.getState().setMessages(messages);
    }
  }, [messages]);

  useEffect(() => {
    if (hasHydrated.current) return;
    if (storeMessages.length > 0) {
      hasHydrated.current = true;
      const typed = storeMessages as Message[];
      setMessagesLocal(typed);
      hasAutoGenerated.current = true;
    }
  }, [storeMessages]);

  const params = useParams();
  const packId = params.packId as string | undefined;
  const projectName = packName || brandContext?.brandName || "My Project";

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setPopoverOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingDisplay, scrollToBottom]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const sendRequest = useCallback(
    async (userContent: string, currentMessages: Message[]) => {
      setIsStreaming(true);
      setIsThinking(false);
      setActiveQuestions([]);
      const currentFiles = useProjectStore.getState().files;
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            files: currentFiles,
            brandContext: brandContext ?? undefined,
            selectedStyle: useProjectStore.getState().selectedStyle ?? undefined,
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

          // Detect thinking phase
          const inThinking =
            accumulated.includes("<thinking>") && !accumulated.includes("</thinking>");
          setIsThinking(inThinking);

          const display = extractStreamingDisplay(accumulated);
          setStreamingDisplay(display);

          if (
            !useProjectStore.getState().isGenerating &&
            accumulated.includes("<file")
          ) {
            useProjectStore.getState().setIsGenerating(true);
          }
        }

        const extractedFiles = parseFileTags(accumulated);
        const hasFiles = Object.keys(extractedFiles).length > 0;
        const questions = parseQuestions(accumulated);
        const summary = parseSummary(accumulated);

        if (hasFiles) {
          useProjectStore.getState().updateFiles(extractedFiles);
          // Reset the auto-fix guard when new code is successfully generated
          lastAutoFixedError.current = null;
        }

        if (questions.length > 0) {
          const displayMessage = summary || "I have a few questions before I start:";
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: displayMessage },
          ]);
          setActiveQuestions(questions);
        } else {
          const displayMessage = summary || "Done! I\u2019ve updated your website.";
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: displayMessage },
          ]);
        }
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
        setIsThinking(false);
        setStreamingDisplay("");
        useProjectStore.getState().setIsGenerating(false);
        inputRef.current?.focus();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [brandContext],
  );

  // Auto-generation on first load with brand context + style
  useEffect(() => {
    if (
      hasAutoGenerated.current ||
      !brandContext ||
      !selectedStyle ||
      messages.length > 0 ||
      isStreaming
    )
      return;

    hasAutoGenerated.current = true;

    const autoMessage = buildAutoKickoff(brandContext, selectedStyle);
    const userMsg: Message = { role: "user", content: autoMessage };
    setMessages([userMsg]);
    sendRequest(autoMessage, [userMsg]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandContext, selectedStyle, messages.length, isStreaming, sendRequest]);

  // Listen for preview errors and auto-fix them
  useEffect(() => {
    const handlePreviewError = (e: MessageEvent) => {
      if (!e.data || e.data.type !== "PREVIEW_ERROR") return;
      const error = e.data.error as string;
      if (!error || !error.trim()) return;

      // Don't fix the same error twice in a row (prevents infinite loops)
      if (error === lastAutoFixedError.current) return;

      // Don't interrupt an ongoing stream
      if (isStreaming) return;

      // Don't auto-fix on default/empty project
      const currentFiles = useProjectStore.getState().files;
      const isDefault = Object.values(currentFiles)
        .join("")
        .includes("Describe your website to get started");
      if (isDefault) return;

      lastAutoFixedError.current = error;

      const fixMsg = `There's a JavaScript error in the preview:\n\n${error}\n\nPlease debug and fix the code. Return the complete corrected /App.tsx.`;
      const userMsg: Message = { role: "user", content: fixMsg };

      setMessages((prev) => {
        const updated = [...prev, userMsg];
        sendRequest(fixMsg, updated);
        return updated;
      });
    };

    window.addEventListener("message", handlePreviewError);
    return () => window.removeEventListener("message", handlePreviewError);
  }, [isStreaming, sendRequest]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMessage: Message = { role: "user", content: trimmed };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setActiveQuestions([]);
    sendRequest(trimmed, updatedMessages);
  };

  const handleChipClick = (chip: string) => {
    setInput(chip);
    inputRef.current?.focus();
  };

  const handleQuestionSubmit = (composedAnswer: string) => {
    const userMessage: Message = { role: "user", content: composedAnswer };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setActiveQuestions([]);
    sendRequest(composedAnswer, updatedMessages);
  };

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-card border-r border-border">
      <div ref={popoverRef} className="relative shrink-0 border-b border-border">
        <button
          onClick={() => setPopoverOpen(!popoverOpen)}
          className="flex items-center gap-2 px-3 py-3 w-full hover:bg-accent/50 transition"
        >
          <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
            {projectName[0]}
          </div>
          <span className="text-sm font-medium text-foreground truncate">
            {projectName}
          </span>
          <ChevronDown className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
        </button>

        {popoverOpen && (
          <div className="absolute top-full left-2 w-56 bg-card border border-border rounded-xl shadow-xl z-50 py-1">
            <Link
              href={packId ? `/packs/${packId}` : "/dashboard"}
              className="flex items-center gap-3 px-4 py-2 text-sm text-card-foreground hover:bg-accent"
              onClick={() => setPopoverOpen(false)}
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Pack Overview
            </Link>

            <div className="border-t border-border my-1" />

            <button className="flex items-center gap-3 px-4 py-2 text-sm text-card-foreground hover:bg-accent w-full text-left">
              <Settings className="w-4 h-4" />
              Settings
            </button>
            <button className="flex items-center gap-3 px-4 py-2 text-sm text-card-foreground hover:bg-accent w-full text-left">
              <Pencil className="w-4 h-4" />
              Rename project
            </button>
            <button className="flex items-center gap-3 px-4 py-2 text-sm text-card-foreground hover:bg-accent w-full text-left">
              <Star className="w-4 h-4" />
              Star project
            </button>

            <div className="border-t border-border my-1" />

            <button className="flex items-center gap-3 px-4 py-2 text-sm text-card-foreground hover:bg-accent w-full text-left">
              <HelpCircle className="w-4 h-4" />
              Help
            </button>
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto px-4 py-6 space-y-6"
      >
        {!selectedStyle && messages.length === 0 && <StylePicker />}

        {selectedStyle && messages.length === 0 && !isStreaming && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2 px-4">
              <p className="text-sm text-muted-foreground">
                {brandContext
                  ? "Getting your brand context ready\u2026"
                  : "Describe the website you want to create and I\u2019ll help you build it."}
              </p>
            </div>
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

        {!isStreaming && activeQuestions.length > 0 && (
          <div className="flex justify-start w-full">
            <div className="w-full max-w-[90%]">
              <QuestionForm
                questions={activeQuestions}
                onSubmit={handleQuestionSubmit}
                disabled={isStreaming}
              />
            </div>
          </div>
        )}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%] text-sm text-foreground">
              {isThinking ? (
                <span className="flex items-center gap-2 text-muted-foreground">
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                  Reasoning&hellip;
                </span>
              ) : (
                <>
                  <span className="whitespace-pre-wrap">
                    {streamingDisplay || "\u00A0"}
                  </span>
                  <span
                    className="inline-block w-0.5 h-4 ml-0.5 align-middle bg-current animate-pulse"
                    aria-hidden
                  />
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="shrink-0 px-4 pb-4 pt-2">
        {!isStreaming &&
          activeQuestions.length === 0 &&
          getSuggestionChips(files).length > 0 && (
            <div className="flex items-center gap-2 mb-3 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
              {getSuggestionChips(files).map((chip) => (
                <Chip
                  key={chip}
                  size="sm"
                  className="shrink-0 whitespace-nowrap"
                  onClick={() => handleChipClick(chip)}
                >
                  {chip}
                </Chip>
              ))}
            </div>
          )}
        <form onSubmit={handleSubmit}>
          <SearchInput
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message Klaro…"
            disabled={isStreaming}
            focusScale={false}
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
  );
}
