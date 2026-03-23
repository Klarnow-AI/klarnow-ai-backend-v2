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
} from "@/components/icons";
import { StylePicker } from "@/components/builder/StylePicker";
import {
  QuestionForm,
  type ParsedQuestion,
} from "@/components/builder/QuestionForm";
import { cn } from "@/lib/utils";
import {
  fetchApiResponse,
  getApiErrorFromResponse,
  isRequestCancelled,
} from "@/lib/http";
import type { BrandContext, BuilderAssistantMode } from "@/types/generation";

// ─── Types ────────────────────────────────────────────────────────────────────

type Message = {
  role: "user" | "assistant";
  content: string;
  files_snapshot?: Record<string, string>;
};

type GenStage = "idle" | "planning" | "coding";

// ─── Constants ────────────────────────────────────────────────────────────────

const STAGE_CONFIG: Record<GenStage, { label: string; emoji: string }> = {
  idle: { label: "", emoji: "" },
  planning: { label: "Designing…", emoji: "" },
  coding: { label: "Updating site…", emoji: "" },
};

const ASSISTANT_MODES: Array<{
  id: BuilderAssistantMode;
  label: string;
  description: string;
}> = [
  {
    id: "launch",
    label: "Launch",
    description: "Build a strong first version quickly.",
  },
  {
    id: "convert",
    label: "Convert",
    description: "Sharpen CTA flow and lead capture.",
  },
  {
    id: "polish",
    label: "Polish",
    description: "Refine visuals, spacing, and finish.",
  },
  {
    id: "debug",
    label: "Fix issues",
    description: "Target bugs and broken layout behavior.",
  },
];

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
  const hasFile = text.includes("<file");
  if (hasFile) return "coding";
  if (text.trim()) return "planning";
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
  if (brand.targetAudience)
    lines.push(`Target audience: ${brand.targetAudience}.`);
  if (brand.promise) lines.push(`Brand promise: ${brand.promise}.`);
  if (brand.designCues?.length)
    lines.push(`Design cues: ${brand.designCues.join(", ")}.`);
  if (brand.typographyDirection)
    lines.push(`Typography direction: ${brand.typographyDirection}.`);
  if (brand.stylePalette?.length)
    lines.push(`Palette direction: ${brand.stylePalette.join(", ")}.`);

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
  const selectedAssistantMode = useProjectStore((s) => s.selectedAssistantMode);
  const files = useProjectStore((s) => s.files);
  const canUndo = useProjectStore((s) => s.fileHistory.length > 0);
  const projectId = useProjectStore((s) => s.projectId);
  const publishedFiles = useProjectStore((s) => s.publishedFiles);

  const [messages, setMessagesLocal] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [showStreamingIndicator, setShowStreamingIndicator] = useState(false);
  const [genStage, setGenStage] = useState<GenStage>("idle");
  const [activeQuestions, setActiveQuestions] = useState<ParsedQuestion[]>([]);
  const [actionsExpanded, setActionsExpanded] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

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

  // ── Cmd/Ctrl+Z for undo ────────────────────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: WindowEventMap["keydown"]) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z" && !e.shiftKey) {
        const target = e.target as Node;
        if (textareaRef.current?.contains(target)) return;
        e.preventDefault();
        if (canUndo && !isStreaming) {
          useProjectStore.getState().undoLastChange();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canUndo, isStreaming]);

  // ── Stop streaming ────────────────────────────────────────────────────────

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ── Core send request ─────────────────────────────────────────────────────

  const sendRequest = useCallback(
    async (
      userContent: string,
      currentMessages: Message[],
      options?: {
        visible?: boolean;
        assistantMode?: BuilderAssistantMode;
      },
    ) => {
      const visible = options?.visible ?? true;
      const assistantMode = options?.assistantMode ?? selectedAssistantMode;
      setIsStreaming(true);
      setShowStreamingIndicator(visible);
      setGenStage(visible ? "planning" : "idle");
      if (visible) {
        setActiveQuestions([]);
      } else {
        useProjectStore.getState().setIsGenerating(true);
      }
      const currentFiles = useProjectStore.getState().files;
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        if (!projectId) {
          if (visible) {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: "Builder project is not ready yet.",
              },
            ]);
          }
          return;
        }

        const res = await fetchApiResponse(
          `/api/v1/builder/projects/${encodeURIComponent(projectId)}/generate`,
          {
            method: "POST",
            body: JSON.stringify({
              messages: currentMessages,
              files: currentFiles,
              selectedStyle:
                useProjectStore.getState().selectedStyle ?? undefined,
              assistantMode,
            }),
            signal: controller.signal,
          },
        );

        if (!res.ok) {
          const message = (await getApiErrorFromResponse(
            res,
            "Builder generation failed",
          )).message;
          if (visible) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: message },
            ]);
          }
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

          if (visible) {
            const stage = getStageFromStream(accumulated);
            setGenStage(stage);
          }

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

        if (visible && questions.length > 0) {
          const displayMsg =
            summary || "I have a few questions before I start:";
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: displayMsg },
          ]);
          setActiveQuestions(questions);
        } else if (visible) {
          const displayMsg = summary || "Done! I\u2019ve updated your website.";
          setMessages((prev): Message[] => {
            const assistantMsg: Message = {
              role: "assistant",
              content: displayMsg,
              ...(hasFiles ? { files_snapshot: extractedFiles } : {}),
            };
            const updated: Message[] = [...prev, assistantMsg];
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
        if (visible) {
          if (isRequestCancelled(err)) {
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
                  err instanceof Error
                    ? err.message
                    : "We're having trouble on our side. Please try again in a few moments.",
              },
            ]);
          }
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setShowStreamingIndicator(false);
        setGenStage("idle");
        useProjectStore.getState().setIsGenerating(false);
        if (visible) {
          textareaRef.current?.focus();
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projectId, selectedAssistantMode, setMessages],
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
      const hiddenUserMessage: Message = { role: "user", content: fixMsg };
      sendRequest(fixMsg, [...messages, hiddenUserMessage], {
        visible: false,
        assistantMode: "debug",
      });
    };

    window.addEventListener("message", handlePreviewError);
    return () => window.removeEventListener("message", handlePreviewError);
  }, [isStreaming, messages, sendRequest]);

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

  const handleRevertToPublished = useCallback(() => {
    const files = useProjectStore.getState().publishedFiles;
    if (!files || Object.keys(files).length === 0) return;
    useProjectStore.getState().restoreFiles(files);
  }, []);

  const handleRevertToMessage = useCallback(
    (snapshot: Record<string, string>) => {
      useProjectStore.getState().restoreFiles(snapshot);
    },
    [],
  );

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
                  {msg.files_snapshot && (
                    <>
                      <span className="text-border text-xs">·</span>
                      <button
                        className="text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors hover:bg-accent whitespace-nowrap disabled:opacity-40"
                        onClick={() => {
                          if (msg.files_snapshot)
                            handleRevertToMessage(msg.files_snapshot);
                        }}
                        disabled={isStreaming}
                        title="Restore to this version"
                      >
                        Restore
                      </button>
                    </>
                  )}
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
        {showStreamingIndicator && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-accent/40 text-sm text-foreground">
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="flex gap-1 shrink-0">
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:300ms]" />
                </span>
                <span>{stage.label || "Generating\u2026"}</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom area ── */}
      <div className="shrink-0 px-3 pb-3 pt-2 space-y-2">
        {selectedStyle && (
          <div className="rounded-xl border border-border bg-background px-3 py-2.5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  Assistant Mode
                </p>
                <p className="text-xs text-muted-foreground">
                  Choose how Klaro should prioritize the next pass.
                </p>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {ASSISTANT_MODES.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() =>
                    useProjectStore.getState().setSelectedAssistantMode(mode.id)
                  }
                  title={mode.description}
                  disabled={isStreaming}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                    selectedAssistantMode === mode.id
                      ? "border-foreground bg-foreground text-background"
                      : "border-border bg-accent/40 text-foreground hover:bg-accent",
                    isStreaming && "cursor-not-allowed opacity-50",
                  )}
                >
                  {mode.label}
                </button>
              ))}
            </div>
          </div>
        )}

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

        {/* Version control strip */}
        {isPageReady && (
          <div className="rounded-xl border border-border bg-background px-3 py-2.5 flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleUndo}
              disabled={!canUndo || isStreaming}
              title="Undo last generation"
              className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed px-2 py-1 rounded-lg hover:bg-accent transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Undo
            </button>
            {publishedFiles && Object.keys(publishedFiles).length > 0 && (
              <>
                <span className="text-border text-xs">·</span>
                <button
                  type="button"
                  onClick={handleRevertToPublished}
                  disabled={isStreaming}
                  title="Revert to last published version"
                  className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed px-2 py-1 rounded-lg hover:bg-accent transition-colors"
                >
                  Revert to published
                </button>
              </>
            )}
          </div>
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
                showStreamingIndicator
                  ? "Klaro is working\u2026"
                  : "Message Klaro\u2026"
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
                {showStreamingIndicator ? (
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
                    disabled={!input.trim() || isStreaming}
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
