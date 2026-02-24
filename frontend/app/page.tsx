"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sun, FolderPlus } from "@/components/icons";
import { PageLoader } from "@/components/ui/page-loader";
import { useAuth } from "@/contexts/auth-context";
import { useLandingContext } from "@/hooks/use-landing-context";
import { useNextAction } from "@/hooks/use-next-action";
import { useTheme } from "@/contexts/theme-context";
import { Button } from "@/components/ui/button";
import { ComposeInput } from "@/components/ui/compose-input";
import { Chip } from "@/components/ui/chip";
import { IconButton } from "@/components/ui/icon-button";
import { ThemeSettingsPopover } from "@/components/theme-settings-popover";
import { ProfileDropdown } from "@/components/profile-dropdown";
import { ProfileAvatar } from "@/components/profile-avatar";
import { AuthModal } from "@/components/auth-modal";
import { OnboardingModal } from "@/components/onboarding-modal";
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
  const { resolved: themeResolved } = useTheme();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [onboardingModalOpen, setOnboardingModalOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    if (isLoading || landingLoading) return;
    if (isAuthenticated && context && context.stage === "no_pack") {
      setOnboardingModalOpen(true);
    }
  }, [isAuthenticated, isLoading, landingLoading, context]);

  const logoSrc =
    themeResolved === "dark"
      ? "/logos/logo_white.svg"
      : "/logos/logo_black.svg";

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
      setOnboardingModalOpen(true);
    }
  }

  function handleOnboardingComplete(id: string) {
    setOnboardingModalOpen(false);
    router.push(`/packs/${id}`);
  }

  function handleRegisterSuccess() {
    setAuthModalOpen(false);
    setOnboardingModalOpen(true);
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
    <div className="relative min-h-screen flex flex-col text-foreground overflow-hidden">
      {/* Glassmorphism background: base gradient + frosted glass overlay */}
      <div
        className="fixed inset-0 -z-10 pointer-events-none bg-gradient-to-br from-background via-background to-muted/30"
        aria-hidden
      />
      <div
        className="fixed inset-0 -z-10 pointer-events-none bg-background/70 backdrop-blur-xl backdrop-saturate-150"
        aria-hidden
      />
      {landingLoading && isAuthenticated && (
        <PageLoader variant="overlay" message="Loading…" />
      )}
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={handleRegisterSuccess}
      />
      <OnboardingModal
        open={onboardingModalOpen}
        onOpenChange={setOnboardingModalOpen}
        onComplete={handleOnboardingComplete}
      />
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative flex items-center justify-between px-6 py-4"
      >
        <Link href="/" className="flex items-center gap-2 flex-shrink-0">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-full overflow-hidden">
            <Image
              src={logoSrc}
              alt="Klarnow AI"
              width={36}
              height={36}
              className="object-contain"
            />
          </div>
        </Link>
        {!isLoading && !isAuthenticated && (
          <nav
            className="absolute left-1/2 -translate-x-1/2 flex items-center gap-6"
            aria-label="Main"
          >
            <Link
              href="/install"
              className="text-sm text-foreground/70 no-underline hover:text-foreground transition-colors"
            >
              Install
            </Link>
            <Link
              href="/about"
              className="text-sm text-foreground/70 no-underline hover:text-foreground transition-colors"
            >
              About
            </Link>
          </nav>
        )}
        <nav className="flex items-center gap-2 flex-shrink-0">
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={handleDashboardClick}
                    className="text-sm text-foreground/50 no-underline hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors rounded-lg px-2 py-1 -mx-2 -my-1"
                  >
                    Dashboard
                  </button>
                  <ProfileDropdown
                    open={profileOpen}
                    onOpenChange={setProfileOpen}
                    className="flex h-11 w-11 items-center justify-center rounded-full border-[0.2px] border-border bg-card overflow-hidden"
                  >
                    <ProfileAvatar className="h-full w-full" />
                  </ProfileDropdown>
                </div>
              ) : (
                <>
                  <ThemeSettingsPopover
                    open={settingsOpen}
                    onOpenChange={setSettingsOpen}
                    trigger={
                      <IconButton
                        variant="ghost"
                        size="md"
                        className="rounded-lg"
                        aria-label="Theme"
                      >
                        <Sun className="h-5 w-5" />
                      </IconButton>
                    }
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-border bg-card"
                    onClick={() => setAuthModalOpen(true)}
                  >
                    Sign in
                  </Button>
                  <Button
                    size="sm"
                    className="bg-foreground text-background hover:bg-foreground/90"
                    onClick={() => setAuthModalOpen(true)}
                  >
                    Sign up
                  </Button>
                </>
              )}
            </>
          )}
        </nav>
      </motion.header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-2xl flex flex-col items-center text-center"
        >
          {/* Top strip: Pack name, Day X of 14, date (Command Centre) */}
          {showStrip && context?.pack && (
            <div className="flex items-center justify-center gap-3 mb-4 text-xs text-muted-foreground flex-wrap">
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
          <h1 className="font-heading font-bold text-foreground tracking-tight mb-2 line-clamp-2 text-4xl sm:text-5xl md:text-6xl">
            {headline}
          </h1>

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
            placeholder="Describe the offer you want to launch…"
            wrapperClassName="mb-2"
          />

          {/* Next Action chips (stateful from API, max 3) */}
          <div className="flex flex-wrap items-center justify-center gap-2">
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
                      onClick={() => setOnboardingModalOpen(true)}
                    >
                      {chip.label}
                    </Chip>
                  </motion.div>
                ),
              )}
          </div>
        </motion.div>
      </main>

      {/* Footer: terms/privacy */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="py-6 px-6 flex flex-col items-end gap-4"
      >
        <p className="w-full text-center text-sm text-muted-foreground">
          By using Klarnow AI, you agree to our{" "}
          <Link
            href="/terms"
            className="font-medium text-foreground underline underline-offset-2 hover:no-underline"
          >
            Terms
          </Link>{" "}
          and{" "}
          <Link
            href="/privacy"
            className="font-medium text-foreground underline underline-offset-2 hover:no-underline"
          >
            Privacy Policy
          </Link>
          .
        </p>
      </motion.footer>
    </div>
  );
}
