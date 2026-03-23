"use client";

import { useState, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { PageLoader } from "@/components/ui/page-loader";
import { useAuth } from "@/contexts/auth-context";
import { useLandingContext } from "@/hooks/use-landing-context";
import { ComposeInput } from "@/components/ui/compose-input";
import { Chip } from "@/components/ui/chip";
import { PublicHeader } from "@/components/public-header";
import { NotFoundView } from "@/components/not-found-view";
import { MVP_QUESTIONS } from "@/components/onboarding-chat-steps";

const AuthModal = dynamic(
  () => import("@/components/auth-modal").then((mod) => mod.AuthModal),
  { ssr: false },
);

const WHAT_DO_YOU_SELL_OFFERS = [
  "coaching service",
  "consulting offer",
  "digital product",
  "local business",
  "online course",
  "agency service",
] as const;

const WHAT_DO_YOU_SELL_AUDIENCES = [
  "first-time founders",
  "busy professionals",
  "small business owners",
  "freelancers",
  "content creators",
  "local business owners",
] as const;

const WHAT_DO_YOU_SELL_FALLBACKS = [
  "I sell a coaching service for small business owners.",
  "I sell social media management for local businesses.",
  "I sell a digital product for first-time founders.",
  "I help local business owners get more customer enquiries.",
] as const;

type WhatDoYouSellPromptParts = {
  offer: string;
  audience: string;
};

type WhatDoYouSellPromptTemplate = (parts: WhatDoYouSellPromptParts) => string;

const WHAT_DO_YOU_SELL_TEMPLATES: WhatDoYouSellPromptTemplate[] = [
  ({ offer }) => `I sell ${offer}.`,
  ({ offer, audience }) => `I sell ${offer} for ${audience}.`,
  ({ offer, audience }) => `We sell ${offer} to ${audience}.`,
  ({ offer, audience }) => `I help ${audience} with ${offer}.`,
];

function randomFrom<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)];
}

function generateWhatDoYouSellPrompts(count = 4): string[] {
  const prompts = new Set<string>();
  const maxAttempts = count * 12;
  let attempts = 0;
  while (prompts.size < count && attempts < maxAttempts) {
    attempts += 1;
    const template = randomFrom(WHAT_DO_YOU_SELL_TEMPLATES);
    const candidate = template({
      offer: randomFrom(WHAT_DO_YOU_SELL_OFFERS),
      audience: randomFrom(WHAT_DO_YOU_SELL_AUDIENCES),
    });
    if (candidate.trim()) prompts.add(candidate);
  }
  if (prompts.size === 0) return [...WHAT_DO_YOU_SELL_FALLBACKS].slice(0, count);
  return [...prompts].slice(0, count);
}

function useAnimatedPlaceholder(
  phrases: readonly string[],
  enabled = true,
): string {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [characterIndex, setCharacterIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!enabled || phrases.length === 0) return;
    const phrase = phrases[phraseIndex % phrases.length] ?? "";
    const atStart = characterIndex === 0;
    const atEnd = characterIndex === phrase.length;
    const timeoutMs = atEnd ? 1400 : isDeleting ? 32 : 56;
    const timeoutId = window.setTimeout(() => {
      if (!isDeleting && atEnd) {
        setIsDeleting(true);
        return;
      }
      if (isDeleting && atStart) {
        setIsDeleting(false);
        setPhraseIndex((prev) => (prev + 1) % phrases.length);
        return;
      }
      setCharacterIndex((prev) => Math.max(0, prev + (isDeleting ? -1 : 1)));
    }, timeoutMs);
    return () => window.clearTimeout(timeoutId);
  }, [phrases, phraseIndex, characterIndex, isDeleting, enabled]);

  if (!enabled) return phrases[0] ?? "";
  const phrase = phrases[phraseIndex % phrases.length] ?? "";
  return phrase.slice(0, characterIndex);
}

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const {
    context,
    isLoading: landingLoading,
    error: landingError,
  } = useLandingContext();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const suggestionPrompts = useMemo(() => generateWhatDoYouSellPrompts(4), []);
  const packQuestionPlaceholders = useMemo(
    () => MVP_QUESTIONS.map((question) => question.label).filter(Boolean),
    [],
  );
  const animatedPlaceholder = useAnimatedPlaceholder(
    packQuestionPlaceholders,
    !query.trim(),
  );

  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    if (landingLoading) return;
    if (landingError) return;
    if (context?.pack?.id) {
      router.replace(`/packs/${context.pack.id}`);
      return;
    }
    router.replace("/packs/new");
  }, [isAuthenticated, isLoading, landingLoading, landingError, context, router]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setAuthModalOpen(true);
  };

  function handleDashboardClick(e: React.MouseEvent) {
    e.preventDefault();
    setAuthModalOpen(true);
  }

  function handleRegisterSuccess() {
    setAuthModalOpen(false);
    router.push("/packs/new");
  }

  if (isLoading) {
    return <PageLoader variant="screen" message="Loading…" />;
  }

  if (isAuthenticated && landingLoading) {
    return <PageLoader variant="screen" message="Loading…" />;
  }

  if (isAuthenticated && landingError) {
    return (
      <NotFoundView
        title="Workspace not available"
        description={landingError.message}
        primaryHref="/packs"
        primaryLabel="Go to packs"
        secondaryHref="/"
        secondaryLabel="Back home"
      />
    );
  }

  if (isAuthenticated) {
    return <PageLoader variant="screen" message="Loading…" />;
  }

  return (
    <div className="relative min-h-screen flex flex-col text-foreground overflow-hidden bg-background">
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={handleRegisterSuccess}
      />
      <PublicHeader
        onDashboardClick={handleDashboardClick}
        onAuthClick={() => setAuthModalOpen(true)}
        showInstallAbout
      />

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-4xl flex flex-col items-center text-center px-4 sm:px-6"
        >
          <h3 className="font-heading font-[500] text-foreground tracking-tight mb-2 line-clamp-2 text-3xl sm:text-4xl md:text-5xl leading-tight">
            Build a business people come back to.
          </h3>
          <p className="text-muted-foreground text-md">
            A 14-day sprint that helps you publish, capture leads, and get paid.
          </p>
          <div className="mb-10" />

          {/* Main input */}
          <ComposeInput
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            placeholder={animatedPlaceholder || "What do you sell?"}
            wrapperClassName="mb-2"
          />

          <div className="flex w-full flex-wrap items-center justify-center gap-2 sm:gap-3">
            {suggestionPrompts.map((prompt, index) => (
              <motion.div
                key={prompt}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + index * 0.05 }}
                className="shrink-0"
              >
                <Chip
                  size="md"
                  onClick={() => setQuery(prompt)}
                  className="max-w-[22rem] overflow-hidden whitespace-nowrap text-ellipsis text-left"
                >
                  {prompt}
                </Chip>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
