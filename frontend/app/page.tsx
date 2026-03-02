"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FolderPlus } from "@/components/icons";
import { PageLoader } from "@/components/ui/page-loader";
import { useAuth } from "@/contexts/auth-context";
import { useLandingContext } from "@/hooks/use-landing-context";
import { useNextAction } from "@/hooks/use-next-action";
import { ComposeInput } from "@/components/ui/compose-input";
import { Chip } from "@/components/ui/chip";
import { AuthModal } from "@/components/auth-modal";
import { PublicHeader } from "@/components/public-header";
import { cn } from "@/lib/utils";

function getHeadline(
  stage: string | undefined,
  sprintDay: number | null,
  leadCount: number | null,
): string {
  if (!stage || stage === "no_pack")
    return "Build a business people come back to.";
  if (stage === "brand_os_done") return "Your foundation is ready.";
  if (stage === "page_live") return "Your page is live.";
  if (stage === "sprint" && sprintDay != null)
    return `Day ${sprintDay} of 14 Sprint`;
  if (stage === "leads" && leadCount != null)
    return `${leadCount} lead${leadCount === 1 ? "" : "s"} waiting.`;
  return "Continue your campaign.";
}

function getStageLabel(
  stage: string | undefined,
  sprintDay: number | null,
  leadCount: number | null,
): string {
  if (!stage || stage === "no_pack") return "Setup";
  if (stage === "brand_os_done") return "Foundation";
  if (stage === "page_live") return "Page live";
  if (stage === "sprint" && sprintDay != null) return `Day ${sprintDay} of 14`;
  if (stage === "leads" && leadCount != null) return `${leadCount} leads`;
  return "In progress";
}

function getTodayLabel(): string {
  return new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const { context, isLoading: landingLoading } = useLandingContext();
  const { nextAction } = useNextAction(!!isAuthenticated, context?.pack?.id);
  const hasPacks = context?.pack != null;
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    if (isLoading || landingLoading) return;
    if (isAuthenticated && context) {
      if (context.stage === "no_pack") {
        router.replace("/packs/new");
      } else if (context.pack) {
        router.replace(`/packs/${context.pack.id}`);
      }
    }
  }, [isAuthenticated, isLoading, landingLoading, context, router]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (isAuthenticated) {
      router.push(`/chat?q=${encodeURIComponent(query.trim())}`);
    } else {
      setAuthModalOpen(true);
    }
  };

  function handleDashboardClick(e: React.MouseEvent) {
    e.preventDefault();
    if (context?.pack) {
      router.push(`/packs/${context.pack.id}`);
    } else if (landingLoading) {
      return;
    } else {
      router.push("/packs/new");
    }
  }

  function handleRegisterSuccess() {
    setAuthModalOpen(false);
    router.push("/packs/new");
  }

  const headline = getHeadline(
    context?.stage,
    context?.sprintDay ?? null,
    context?.leadCount ?? null,
  );
  const stageLabel = getStageLabel(
    context?.stage,
    context?.sprintDay ?? null,
    context?.leadCount ?? null,
  );
  const showStrip = context?.pack != null;
  const sprintDay = context?.stage === "sprint" ? (context.sprintDay ?? 0) : 0;
  const show14Dots = context?.pack != null && context?.stage === "sprint";

  return (
    <div className="relative min-h-screen flex flex-col text-foreground overflow-hidden bg-background">
      {landingLoading && isAuthenticated && (
        <PageLoader variant="overlay" message="Loading…" />
      )}
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={handleRegisterSuccess}
      />
      <PublicHeader
        onDashboardClick={handleDashboardClick}
        onAuthClick={() => setAuthModalOpen(true)}
        showInstallAbout={!isAuthenticated}
      />

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-4xl flex flex-col items-center text-center px-4 sm:px-6"
        >
          {/* Top strip: Pack name, Day X of 14, date (Command Centre) */}
          {showStrip && context?.pack && (
            <div className="flex items-center justify-center gap-2 sm:gap-3 mb-4 text-xs text-muted-foreground flex-wrap">
              <span>Pack: {context.pack.name}</span>
              <span aria-hidden className="text-muted-foreground/50">
                ·
              </span>
              <span>Stage: {stageLabel}</span>
              <span aria-hidden className="text-muted-foreground/50">
                ·
              </span>
              <span>{getTodayLabel()}</span>
            </div>
          )}

          {/* Contextual headline - two lines */}
          <h3 className="font-heading font-[500] text-foreground tracking-tight mb-2 line-clamp-2 text-3xl sm:text-4xl md:text-5xl leading-tight">
            {headline}
          </h3>
          <p className="text-muted-foreground text-md">
            {headline === "Build a business people come back to."
              ? "A 14-day sprint that helps you publish, capture leads, and get paid."
              : ""}
          </p>

          {/* Sprint dots: Day 0–14 when in sprint; otherwise none */}
          <div
            className="flex items-center justify-center gap-1.5 mb-10"
            aria-hidden
          >
            {!show14Dots ? (
              <span className="text-sm text-muted-foreground"></span>
            ) : (
              Array.from({ length: 15 }, (_, i) => i).map((day) => (
                <span
                  key={day}
                  className={cn(
                    "rounded-full transition-colors",
                    day === sprintDay
                      ? "w-2 h-2 bg-foreground/80"
                      : "w-2 h-2 bg-foreground/20",
                  )}
                />
              ))
            )}
          </div>

          {/* Main input */}
          <ComposeInput
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            placeholder="Describe the campaign you want to launch…"
            wrapperClassName="mb-2"
          />

          {/* Next Action chips (stateful from API, max 3) */}
          <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
            {!isAuthenticated && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <Chip
                  size="md"
                  icon={<FolderPlus />}
                  onClick={() => setAuthModalOpen(true)}
                >
                  Create Campaign Pack
                </Chip>
              </motion.div>
            )}
            {isAuthenticated &&
              nextAction?.actionChips?.slice(0, 3).map((chip, i) =>
                chip.href ? (
                  <motion.div
                    key={chip.label}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 + i * 0.05 }}
                  >
                    <Chip size="md" href={chip.href}>
                      {chip.label}
                    </Chip>
                  </motion.div>
                ) : (
                  <motion.div
                    key={chip.label}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 + i * 0.05 }}
                  >
                    <Chip
                      size="md"
                      icon={<FolderPlus />}
                      onClick={() => router.push("/packs/new")}
                    >
                      {chip.label}
                    </Chip>
                  </motion.div>
                ),
              )}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
