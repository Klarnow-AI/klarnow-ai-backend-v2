"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  FormEvent,
  KeyboardEvent,
} from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import {
  ChevronLeft,
  ChevronRight,
  Send,
  Stop,
  RotateCcw,
  Sparkles,
  Globe,
  Loader2,
} from "@/components/icons";
import { builder } from "@/api_requests/builder";
import { StylePicker } from "@/components/builder/StylePicker";
import {
  QuestionForm,
  type ParsedQuestion,
} from "@/components/builder/QuestionForm";
import { cn } from "@/lib/utils";
import type { BrandContext } from "@/app/api/generate/route";

// ─── Types ────────────────────────────────────────────────────────────────────

type Message = {
  role: "user" | "assistant";
  content: string;
};

type GenStage = "idle" | "thinking" | "planning" | "coding";

// ─── Constants ────────────────────────────────────────────────────────────────

const STAGE_CONFIG: Record<GenStage, { label: string; emoji: string }> = {
  idle: { label: "", emoji: "" },
  thinking: { label: "Reasoning…", emoji: "🧠" },
  planning: { label: "Planning layout…", emoji: "📐" },
  coding: { label: "Writing code…", emoji: "⌨️" },
};

const QUICK_ACTIONS = [
  {
    emoji: "🏷️",
    label: "Pricing",
    prompt:
      "Add a pricing section with 3 tiers — Starter, Pro (highlighted as most popular), and Enterprise. Include a feature list for each tier.",
  },
  {
    emoji: "💬",
    label: "Testimonials",
    prompt:
      "Add a testimonials section with 3 specific, credible customer quotes. Include each person's name, role, and a measurable result.",
  },
  {
    emoji: "❓",
    label: "FAQ",
    prompt:
      "Add an FAQ section with 6 common questions and clear, detailed answers that address buyer objections.",
  },
  {
    emoji: "📞",
    label: "Contact",
    prompt:
      "Add a contact/inquiry section with a lead capture form that collects name, email, phone, and a short message.",
  },
  {
    emoji: "⚡",
    label: "Features",
    prompt:
      "Add a features section — a 3-column grid of 6 benefit-focused items with emoji icons. Focus on outcomes, not mechanics.",
  },
  {
    emoji: "🔢",
    label: "Stats",
    prompt:
      "Add a stats bar with 4 credibility-building numbers (e.g. clients served, satisfaction rate, results delivered, years in business).",
  },
  {
    emoji: "🙋",
    label: "About",
    prompt:
      "Add an About section with a brand/founder story and 3–4 trust signals (credentials, press, certifications).",
  },
  {
    emoji: "📋",
    label: "How it works",
    prompt:
      "Add a 'How it works' section with 3–4 numbered steps explaining the process from start to result.",
  },
  {
    emoji: "✨",
    label: "More minimal",
    prompt:
      "Simplify the design — increase whitespace, tighten the type scale, and remove any visual noise or decorative excess.",
  },
  {
    emoji: "🔥",
    label: "Make bolder",
    prompt:
      "Make the design bolder — stronger type hierarchy, higher contrast, more visual energy. Don't hold back.",
  },
  {
    emoji: "📱",
    label: "Fix mobile",
    prompt:
      "Audit and fix the mobile responsive layout so every section looks great on small screens.",
  },
  {
    emoji: "✍️",
    label: "Improve copy",
    prompt:
      "Rewrite all copy to be more specific, conversion-focused, and compelling. Use concrete numbers. Cut all vague adjectives.",
  },
];

const ACTIONS_COLLAPSED_COUNT = 8;

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

function getStageFromStream(text: string): GenStage {
  const hasThinkingOpen = text.includes("<thinking>");
  const hasThinkingClose = text.includes("</thinking>");
  const hasFile = text.includes("<file");
  if (hasThinkingOpen && !hasThinkingClose) return "thinking";
  if (hasThinkingClose && !hasFile) return "planning";
  if (hasFile) return "coding";
  return "idle";
}

function getContextActions(files: Record<string, string>) {
  const code = Object.values(files).join(" ").toLowerCase();
  if (code.includes("describe your website to get started")) return [];

  const present = new Set<string>();
  if (code.match(/pricing|price|\bplans?\b|\$\d/)) present.add("Pricing");
  if (code.match(/testimonial|review/)) present.add("Testimonials");
  if (code.match(/faq|frequently asked/)) present.add("FAQ");
  if (code.match(/contact.*form|<form|input.*email/)) present.add("Contact");
  if (code.match(/features?|benefits?/)) present.add("Features");
  if (code.match(/stat|\d{3,}[+k]/)) present.add("Stats");
  if (code.match(/about|story|mission|founder/)) present.add("About");
  if (code.match(/how.it.works|steps?|process/)) present.add("How it works");

  const tweakLabels = new Set([
    "More minimal",
    "Make bolder",
    "Fix mobile",
    "Improve copy",
  ]);
  const missing = QUICK_ACTIONS.filter(
    (a) => !tweakLabels.has(a.label) && !present.has(a.label),
  );
  const tweaks = QUICK_ACTIONS.filter((a) => tweakLabels.has(a.label));
  return [...missing, ...tweaks];
}

function isAutoGeneratedMsg(msg: Message, index: number): boolean {
  return (
    index === 0 &&
    msg.role === "user" &&
    msg.content.startsWith("Build a complete landing page for")
  );
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
  if (brand.primaryCta)
    lines.push(`Primary CTA: \u201c${brand.primaryCta}\u201d`);

  lines.push(
    "Use all brand context available. Build it now \u2014 no questions needed. Make it visually stunning and production-ready.",
  );

  return lines.join("\n");
}

// ─── Component ───────────────────────────────────────────────────────────────

type ChatPanelProps = {
  brandContext?: BrandContext | null;
  packName?: string;
};

export function ChatPanel({ brandContext, packName }: ChatPanelProps) {
  const storeMessages = useProjectStore((s) => s.messages);
  const selectedStyle = useProjectStore((s) => s.selectedStyle);
  const files = useProjectStore((s) => s.files);
  const canUndo = useProjectStore((s) => s.fileHistory.length > 0);
  const projectId = useProjectStore((s) => s.projectId);
  const liveUrl = useProjectStore((s) => s.liveUrl);

  const [messages, setMessagesLocal] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [genStage, setGenStage] = useState<GenStage>("idle");
  const [activeQuestions, setActiveQuestions] = useState<ParsedQuestion[]>([]);
  const [actionsExpanded, setActionsExpanded] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isUnpublishing, setIsUnpublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  // Tracks which message index → version number (local only, not synced)
  const fileUpdateMap = useRef<Map<number, number>>(new Map());
  const versionCounter = useRef(0);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const hasAutoGenerated = useRef(false);
  const hasHydrated = useRef(false);
  const lastAutoFixedError = useRef<string | null>(null);

  const params = useParams();
  const packId = params.packId as string | undefined;
  const projectName = packName || brandContext?.brandName || "My Project";

  // ── Sync messages to store ────────────────────────────────────────────────

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
      setMessagesLocal(storeMessages as Message[]);
      hasAutoGenerated.current = true;
    }
  }, [storeMessages]);

  // ── Auto scroll ───────────────────────────────────────────────────────────

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, genStage, scrollToBottom]);

  // ── Textarea auto-resize ──────────────────────────────────────────────────

  const adjustTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, []);

  useEffect(() => {
    adjustTextarea();
  }, [input, adjustTextarea]);

  // ── Stop streaming ────────────────────────────────────────────────────────

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ── Core send request ─────────────────────────────────────────────────────

  const sendRequest = useCallback(
    async (userContent: string, currentMessages: Message[]) => {
      setIsStreaming(true);
      setGenStage("idle");
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
            selectedStyle:
              useProjectStore.getState().selectedStyle ?? undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errText = await res.text();
          let message: string;
          try {
            const parsed = JSON.parse(errText) as { error?: string };
            message = parsed.error ?? errText;
          } catch {
            message = errText;
          }
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: message },
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

          const stage = getStageFromStream(accumulated);
          setGenStage(stage);

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
          // Snapshot current files before overwriting (enables undo)
          useProjectStore.getState().pushToHistory();
          useProjectStore.getState().updateFiles(extractedFiles);
          lastAutoFixedError.current = null;
        }

        if (questions.length > 0) {
          const displayMsg =
            summary || "I have a few questions before I start:";
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: displayMsg },
          ]);
          setActiveQuestions(questions);
        } else {
          const displayMsg = summary || "Done! I\u2019ve updated your website.";
          setMessages((prev): Message[] => {
            const updated: Message[] = [
              ...prev,
              { role: "assistant", content: displayMsg },
            ];
            if (hasFiles) {
              versionCounter.current += 1;
              fileUpdateMap.current.set(
                updated.length - 1,
                versionCounter.current,
              );
            }
            return updated;
          });
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
              content:
                err instanceof Error && err.message.includes("pipe")
                  ? "We're having trouble generating right now. Please try again in a few moments."
                  : `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
            },
          ]);
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setGenStage("idle");
        useProjectStore.getState().setIsGenerating(false);
        textareaRef.current?.focus();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [brandContext],
  );

  // ── Auto-generate on first load ───────────────────────────────────────────

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

  // ── Auto-fix preview errors ───────────────────────────────────────────────

  useEffect(() => {
    const handlePreviewError = (e: MessageEvent) => {
      if (!e.data || e.data.type !== "PREVIEW_ERROR") return;
      const error = e.data.error as string;
      if (!error?.trim() || error === lastAutoFixedError.current || isStreaming)
        return;

      const currentFiles = useProjectStore.getState().files;
      if (
        Object.values(currentFiles)
          .join("")
          .includes("Describe your website to get started")
      )
        return;

      lastAutoFixedError.current = error;
      const fixMsg = `There's a JavaScript error in the preview:\n\n${error}\n\nPlease debug and fix the code. Return the complete corrected /App.tsx.`;
      const userMsg: Message = { role: "user", content: fixMsg };

      setMessages((prev): Message[] => {
        const updated: Message[] = [...prev, userMsg];
        sendRequest(fixMsg, updated);
        return updated;
      });
    };

    window.addEventListener("message", handlePreviewError);
    return () => window.removeEventListener("message", handlePreviewError);
  }, [isStreaming, sendRequest]);

  // ── Input handlers ────────────────────────────────────────────────────────

  const submitInput = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;
      const userMessage: Message = { role: "user", content: trimmed };
      const updatedMessages = [...messages, userMessage];
      setMessages(updatedMessages);
      setInput("");
      setActiveQuestions([]);
      sendRequest(trimmed, updatedMessages);
    },
    [isStreaming, messages, setMessages, sendRequest],
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submitInput(input);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submitInput(input);
    }
  };

  const handleActionChip = (prompt: string) => {
    setInput(prompt);
    setActionsExpanded(false);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleQuestionSubmit = (composedAnswer: string) => {
    const userMessage: Message = { role: "user", content: composedAnswer };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setActiveQuestions([]);
    sendRequest(composedAnswer, updatedMessages);
  };

  const handleEditMessage = (content: string) => {
    setInput(content);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleRegenerateFrom = (assistantIndex: number) => {
    for (let i = assistantIndex - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        const sliced = messages.slice(0, i + 1);
        setMessages(sliced);
        setActiveQuestions([]);
        sendRequest(messages[i].content, sliced);
        break;
      }
    }
  };

  const handleCopy = async (content: string, idx: number) => {
    await navigator.clipboard.writeText(content).catch(() => {});
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const handleUndo = () => {
    useProjectStore.getState().undoLastChange();
  };

  const handlePublish = useCallback(async () => {
    if (!projectId) return;
    setIsPublishing(true);
    setPublishError(null);
    try {
      const result = await builder.publish(projectId);
      useProjectStore.getState().setLiveUrl(result.live_url ?? null);
    } catch (err) {
      setPublishError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setIsPublishing(false);
    }
  }, [projectId]);

  const handleUnpublish = useCallback(async () => {
    if (!projectId) return;
    setIsUnpublishing(true);
    setPublishError(null);
    try {
      await builder.unpublish(projectId);
      useProjectStore.getState().setLiveUrl(null);
    } catch (err) {
      setPublishError(err instanceof Error ? err.message : "Unpublish failed");
    } finally {
      setIsUnpublishing(false);
    }
  }, [projectId]);

  // ── Derived values ────────────────────────────────────────────────────────

  const contextActions = getContextActions(files);
  const displayActions = actionsExpanded
    ? contextActions
    : contextActions.slice(0, ACTIONS_COLLAPSED_COUNT);
  const hasMoreActions = contextActions.length > ACTIONS_COLLAPSED_COUNT;
  const stage = STAGE_CONFIG[genStage];
  // Page is ready to publish once it has real content (not the default placeholder)
  const isPageReady =
    projectId !== null &&
    !Object.values(files)
      .join("")
      .includes("Describe your website to get started");

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-card border-r border-border">
      {/* ── Header ── */}
      <div className="flex items-center gap-2 px-3 py-3 shrink-0 border-b border-border">
        <Link
          href={packId ? `/chat?pack=${packId}` : "/chat"}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          aria-label="Back to chat"
        >
          <ChevronLeft className="h-5 w-5" />
        </Link>
        <span className="text-sm font-medium text-foreground truncate">
          {projectName}
        </span>
      </div>

      {/* ── Messages ── */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto px-4 py-6 space-y-4"
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

        {messages.map((msg, i) => {
          // Collapsed auto-generated kickoff message
          if (isAutoGeneratedMsg(msg, i)) {
            return (
              <div
                key={i}
                className="flex items-center gap-1.5 py-0.5 text-xs text-muted-foreground"
              >
                <Sparkles className="w-3.5 h-3.5 text-primary/70 shrink-0" />
                <span>Auto-built from brand context</span>
              </div>
            );
          }

          const version = fileUpdateMap.current.get(i);

          // User message
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end group/msg">
                <div className="relative">
                  {/* Hover actions */}
                  <div className="absolute -top-7 right-0 flex items-center gap-px opacity-0 group-hover/msg:opacity-100 transition-opacity bg-card border border-border rounded-lg shadow-sm px-1 py-0.5 z-10">
                    <button
                      className="text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors hover:bg-accent whitespace-nowrap"
                      onClick={() => handleEditMessage(msg.content)}
                    >
                      Edit
                    </button>
                  </div>
                  <div className="rounded-2xl rounded-tr-md px-4 py-3 max-w-[85%] bg-primary text-primary-foreground">
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              </div>
            );
          }

          // Assistant message
          return (
            <div key={i} className="flex justify-start group/msg">
              <div className="relative max-w-[90%]">
                {/* Hover actions */}
                <div className="absolute -top-7 left-0 flex items-center gap-px opacity-0 group-hover/msg:opacity-100 transition-opacity bg-card border border-border rounded-lg shadow-sm px-1 py-0.5 z-10">
                  <button
                    className="text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors hover:bg-accent whitespace-nowrap"
                    onClick={() => handleCopy(msg.content, i)}
                  >
                    {copiedIdx === i ? "Copied!" : "Copy"}
                  </button>
                  <span className="text-border text-xs">·</span>
                  <button
                    className="text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors hover:bg-accent whitespace-nowrap disabled:opacity-40"
                    onClick={() => handleRegenerateFrom(i)}
                    disabled={isStreaming}
                  >
                    Retry
                  </button>
                </div>

                <div className="rounded-2xl rounded-tl-md px-4 py-3 text-sm text-foreground bg-accent/40">
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                  {version !== undefined && (
                    <span className="ml-2 inline-flex items-center text-[10px] font-semibold text-primary/80 bg-primary/10 rounded-full px-1.5 py-0.5 align-middle">
                      v{version}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Question form */}
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

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-accent/40 text-sm text-foreground">
              <span className="flex items-center gap-2 text-muted-foreground">
                {stage.emoji && (
                  <span className="text-base leading-none select-none">
                    {stage.emoji}
                  </span>
                )}
                <span className="flex gap-1 shrink-0">
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:300ms]" />
                </span>
                <span>{stage.label || "Thinking\u2026"}</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom area ── */}
      <div className="shrink-0 px-3 pb-3 pt-2 space-y-2">
        {/* Quick action chips */}
        {!isStreaming &&
          activeQuestions.length === 0 &&
          contextActions.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {displayActions.map((action) => (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => handleActionChip(action.prompt)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-foreground/75 bg-accent hover:bg-accent/60 border border-border/50 rounded-full px-2.5 py-1 transition-all hover:border-foreground/25 hover:text-foreground active:scale-95"
                >
                  <span className="select-none">{action.emoji}</span>
                  <span>{action.label}</span>
                </button>
              ))}
              {hasMoreActions && (
                <button
                  type="button"
                  onClick={() => setActionsExpanded(!actionsExpanded)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground bg-transparent hover:bg-accent border border-dashed border-border/50 rounded-full px-2.5 py-1 transition-all"
                >
                  {actionsExpanded
                    ? "Less"
                    : `+${contextActions.length - ACTIONS_COLLAPSED_COUNT} more`}
                  <ChevronRight
                    className={cn(
                      "w-3 h-3 transition-transform",
                      actionsExpanded && "rotate-90",
                    )}
                  />
                </button>
              )}
            </div>
          )}

        {/* Publish section */}
        {isPageReady && (
          <div className="rounded-xl border border-border bg-background px-3 py-2.5 flex items-center justify-between gap-3">
            {liveUrl ? (
              <>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="flex-shrink-0 w-2 h-2 rounded-full bg-emerald-500" />
                  <a
                    href={liveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-emerald-600 dark:text-emerald-400 font-medium hover:underline truncate"
                    title={liveUrl}
                  >
                    Live
                  </a>
                  <a
                    href={liveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-muted-foreground hover:text-foreground truncate transition-colors"
                    title={liveUrl}
                  >
                    {liveUrl.replace(/^https?:\/\//, "")}
                  </a>
                </div>
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={isPublishing || isStreaming}
                  className="flex-shrink-0 flex items-center gap-1.5 text-xs font-medium text-foreground bg-accent hover:bg-accent/60 border border-border/50 rounded-lg px-2.5 py-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isPublishing ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Globe className="w-3 h-3" />
                  )}
                  {isPublishing ? "Updating…" : "Republish"}
                </button>
                <button
                  type="button"
                  onClick={handleUnpublish}
                  disabled={isUnpublishing || isStreaming}
                  className="flex-shrink-0 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground bg-transparent hover:bg-accent/50 border border-border/50 rounded-lg px-2.5 py-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isUnpublishing ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : null}
                  {isUnpublishing ? "Unpublishing…" : "Unpublish"}
                </button>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground leading-tight">
                  Ready to go live?
                </p>
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={isPublishing || isStreaming}
                  className="flex-shrink-0 flex items-center gap-1.5 text-xs font-semibold text-primary-foreground bg-primary hover:opacity-90 rounded-lg px-3 py-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isPublishing ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Globe className="w-3 h-3" />
                  )}
                  {isPublishing ? "Publishing…" : "Publish"}
                </button>
              </>
            )}
          </div>
        )}
        {publishError && (
          <p className="text-[11px] text-destructive px-1">{publishError}</p>
        )}

        {/* Compose box */}
        <form onSubmit={handleSubmit}>
          <div
            className={cn(
              "rounded-xl border bg-background transition-all",
              "border-border focus-within:border-foreground/30 focus-within:scale-[1.02]",
            )}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isStreaming ? "Klaro is working\u2026" : "Message Klaro\u2026"
              }
              disabled={isStreaming}
              rows={1}
              className="w-full bg-transparent px-3.5 pt-3 pb-1 resize-none outline-none text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-40 min-h-[44px] max-h-[128px] overflow-y-auto leading-relaxed"
            />
            <div className="flex items-center justify-between px-2.5 pb-2 pt-0.5">
              <span className="text-[10px] text-muted-foreground/40 select-none">
                ⌘↵ to send
              </span>
              <div className="flex items-center gap-1">
                {canUndo && !isStreaming && (
                  <button
                    type="button"
                    onClick={handleUndo}
                    title="Undo last generation"
                    className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-lg hover:bg-accent transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Undo
                  </button>
                )}
                {isStreaming ? (
                  <button
                    type="button"
                    onClick={handleStop}
                    aria-label="Stop generation"
                    className="flex items-center justify-center w-8 h-8 rounded-lg bg-foreground text-background hover:opacity-75 transition-opacity"
                  >
                    <Stop className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    aria-label="Send message"
                    disabled={!input.trim()}
                    className="flex items-center justify-center w-8 h-8 rounded-lg bg-foreground text-background disabled:opacity-25 hover:opacity-80 transition-opacity"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
