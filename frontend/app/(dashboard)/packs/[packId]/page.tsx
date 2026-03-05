"use client";

import { useEffect, useState, useCallback } from "react";
import {
  useParams,
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Target,
  Megaphone,
  FileCode,
  Users,
  FileCheck,
  Receipt,
  ChevronRight,
  Film,
  Check,
  Lock,
} from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { NotFoundView } from "@/components/not-found-view";
import { packs as packsApi } from "@/api_requests/packs";
import { me } from "@/api_requests/me";
import { sprintApi } from "@/api_requests/sprint";
import type {
  PackSummaryResponse,
  SprintTodayTasksRead,
} from "@/types/api-types";
import { PackActionsMenu } from "@/components/pack-actions-menu";
import { PackChatPanel } from "./_components/pack-chat-panel";
import { useGet } from "@/hooks/use-get";
import { Day0Modal } from "@/components/day-0-modal";
import { Day1Modal } from "@/components/day-1-modal";
import { Day2Modal } from "@/components/day-2-modal";
import { Day3Modal } from "@/components/day-3-modal";
import { DayDetailModal } from "@/components/day-detail-modal";
import { DAY_TITLES } from "@/lib/sprint-phases";
import { useDelayedNextActionToast } from "@/hooks/use-delayed-next-action-toast";

/** Fixed pack summary cards — no add/remove. */
const PACK_SUMMARY_CARDS: string[] = ["brand_os"];

const PACK_OVERVIEW_MODULES: Record<
  string,
  {
    title: string;
    hrefSuffix: string;
    getHref?: (packId: string) => string;
    icon: React.ComponentType<{ className?: string; size?: number }>;
    emptyMessage: string;
    getContent: (summary: PackSummaryResponse) => React.ReactNode;
  }
> = {
  brand_os: {
    title: "Brand Identity",
    hrefSuffix: "/brand-os",
    icon: Target,
    emptyMessage:
      "No Brand Identity yet. Complete onboarding or open Brand Identity to add logo, fonts, and colours.",
    getContent: (s) =>
      s.brand_os ? (
        <>
          {s.brand_os.mission && (
            <p>
              <span className="font-medium text-muted-foreground">
                Mission:
              </span>{" "}
              {s.brand_os.mission}
            </p>
          )}
          {s.brand_os.vision && (
            <p>
              <span className="font-medium text-muted-foreground">Vision:</span>{" "}
              {s.brand_os.vision}
            </p>
          )}
          {s.brand_os.has_positioning && (
            <p className="text-muted-foreground">Positioning defined.</p>
          )}
        </>
      ) : null,
  },
  campaign: {
    title: "Campaign",
    hrefSuffix: "/campaign",
    icon: Megaphone,
    emptyMessage:
      "Set your primary call-to-action and goal so Klaro can tailor your content and next steps.",
    getContent: (s) =>
      s.campaign ? (
        <>
          {s.campaign.primary_cta && (
            <p>
              <span className="font-medium text-muted-foreground">
                Primary CTA:
              </span>{" "}
              {s.campaign.primary_cta}
            </p>
          )}
          {s.campaign.goal_summary && (
            <p>
              <span className="font-medium text-muted-foreground">Goal:</span>{" "}
              {s.campaign.goal_summary}
            </p>
          )}
        </>
      ) : null,
  },
  website: {
    title: "Website",
    hrefSuffix: "/website",
    icon: FileCode,
    emptyMessage: "No published page. Create and publish in Website.",
    getContent: (s) =>
      s.website ? (
        <>
          {s.website.live_url ? (
            <p>
              <span className="font-medium text-muted-foreground">Live:</span>{" "}
              <a
                href={s.website.live_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline break-all"
              >
                {s.website.live_url}
              </a>
            </p>
          ) : (
            <p className="text-muted-foreground">Draft only — not published.</p>
          )}
          {s.website.published_at && (
            <p className="text-xs text-muted-foreground">
              Published {new Date(s.website.published_at).toLocaleDateString()}
            </p>
          )}
        </>
      ) : null,
  },
  leads: {
    title: "Leads",
    hrefSuffix: "/leads",
    icon: Users,
    emptyMessage: "No leads yet.",
    getContent: (s) =>
      s.leads.total > 0 || s.leads.qualified > 0 ? (
        <p>
          {s.leads.total} lead{s.leads.total !== 1 ? "s" : ""}
          {s.leads.qualified > 0 && <>, {s.leads.qualified} qualified</>}
        </p>
      ) : null,
  },
  proposals: {
    title: "Proposals",
    hrefSuffix: "/proposal",
    getHref: (packId) => `/proposals?pack=${packId}`,
    icon: FileCheck,
    emptyMessage: "No proposals yet.",
    getContent: (s) =>
      s.proposals.total > 0 ? (
        <p>
          {s.proposals.total} total
          {(s.proposals.sent > 0 ||
            s.proposals.accepted > 0 ||
            s.proposals.declined > 0) &&
            ` — ${s.proposals.sent} sent, ${s.proposals.accepted} accepted, ${s.proposals.declined} declined`}
        </p>
      ) : null,
  },
  invoices: {
    title: "Invoices",
    hrefSuffix: "/invoice",
    getHref: (packId) => `/invoices?pack=${packId}`,
    icon: Receipt,
    emptyMessage: "No invoices yet.",
    getContent: (s) =>
      s.invoices.total > 0 ? (
        <p>
          {s.invoices.total} total
          {(s.invoices.sent > 0 ||
            s.invoices.paid > 0 ||
            s.invoices.overdue > 0) &&
            ` — ${s.invoices.sent} sent, ${s.invoices.paid} paid${s.invoices.overdue > 0 ? `, ${s.invoices.overdue} overdue` : ""}`}
        </p>
      ) : null,
  },
  creative: {
    title: "Creative (Ads & Posters)",
    hrefSuffix: "/ad-factory",
    icon: Film,
    emptyMessage: "No creative assets yet.",
    getContent: (s) =>
      s.assets_count > 0 ? (
        <p>
          {s.assets_count} asset{s.assets_count !== 1 ? "s" : ""} (Ad Factory &
          posters).
        </p>
      ) : null,
  },
};

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.03, delayChildren: 0.04 },
  },
};

const item = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0 },
};

const TOTAL_SPRINT_STEPS = 14;

function parseStepNumber(label: string): number | null {
  const match = /^Step\s*(\d+)/i.exec(label.trim());
  if (!match) return null;
  const parsed = Number.parseInt(match[1], 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function stepToPercent(step: number): number {
  const percent = (step / TOTAL_SPRINT_STEPS) * 100;
  return Math.min(100, Math.max(0, percent));
}

function SummarySection({
  title,
  href,
  icon: Icon,
  children,
  emptyMessage,
  cardMenu,
  className,
}: {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  children: React.ReactNode;
  emptyMessage: string;
  cardMenu?: React.ReactNode;
  className?: string;
}) {
  const isEmpty =
    children == null ||
    children === false ||
    (typeof children === "string" && !children.trim());
  return (
    <motion.section
      variants={item}
      className={`rounded-2xl border border-border bg-card overflow-hidden flex flex-col lg:min-h-0 ${className ?? ""}`}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 px-5 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background text-muted-foreground">
            <Icon className="h-4 w-4" size={18} />
          </div>
          <h2 className="text-sm font-semibold text-foreground truncate">
            {title}
          </h2>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {cardMenu}
          <Link
            href={href}
            className="text-xs font-medium text-primary hover:underline flex items-center gap-0.5"
          >
            View
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
      <div className="overflow-visible px-5 py-4 lg:flex-1 lg:min-h-0 lg:overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center text-center py-6 px-2 min-h-[120px]">
            <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
              {emptyMessage}
            </p>
            <Link
              href={href}
              className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Get started
            </Link>
          </div>
        ) : (
          <div className="text-sm text-foreground/90 space-y-2">{children}</div>
        )}
      </div>
    </motion.section>
  );
}

export default function PackOverviewPage() {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const packId = params.packId as string;
  const [nextAction, setNextAction] = useState<Awaited<
    ReturnType<typeof me.getNextAction>
  > | null>(null);
  const [dayModalOpen, setDayModalOpen] = useState<number | null>(null);
  const [todayTasks, setTodayTasks] = useState<SprintTodayTasksRead | null>(
    null,
  );
  const [taskUpdateId, setTaskUpdateId] = useState<string | null>(null);
  const [startingSprint, setStartingSprint] = useState(false);

  const summaryFetcher = useCallback(
    () => packsApi.getSummary(packId),
    [packId],
  );
  const {
    data: summary,
    isLoading: loading,
    error,
    refetch: fetchSummary,
  } = useGet(packId ? ["pack-summary", packId] : null, summaryFetcher);
  const todayTasksFetcher = useCallback(
    () => sprintApi.getTodayTasks(packId),
    [packId],
  );
  const {
    data: todayTasksData,
    isLoading: todayTasksLoading,
    error: todayTasksError,
    refetch: fetchTodayTasks,
  } = useGet(packId ? ["pack-today-tasks", packId] : null, todayTasksFetcher);

  const loadNextAction = useCallback(() => {
    if (!packId) return;
    me.getNextAction(packId)
      .then(setNextAction)
      .catch(() => setNextAction(null));
  }, [packId]);

  useEffect(() => {
    loadNextAction();
  }, [loadNextAction]);

  useDelayedNextActionToast({
    nextAction,
    delayMs: 8_000,
    durationMs: 10_000,
  });

  useEffect(() => {
    setTodayTasks(todayTasksData ?? null);
  }, [todayTasksData]);

  const stepFromUrl = searchParams.get("step") ?? searchParams.get("day");
  useEffect(() => {
    if (stepFromUrl == null) return;
    const parsed = Number.parseInt(stepFromUrl, 10);
    if (Number.isInteger(parsed) && parsed >= 0 && parsed <= 14) {
      setDayModalOpen(parsed);
    }
  }, [stepFromUrl]);

  async function handleArchive(id: string) {
    await packsApi.archive(id);
    fetchSummary();
  }

  async function handleRestore(id: string) {
    await packsApi.restore(id);
    fetchSummary();
  }

  async function handleDelete(id: string) {
    await packsApi.delete(id);
    router.push("/packs");
  }

  const openDayModal = useCallback(
    (dayNumber: number) => {
      if (dayNumber < 0 || dayNumber > 14) return;
      setDayModalOpen(dayNumber);
      const params = new URLSearchParams(searchParams.toString());
      params.set("step", String(dayNumber));
      params.delete("day");
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const closeDayModal = useCallback(() => {
    setDayModalOpen(null);
    const params = new URLSearchParams(searchParams.toString());
    params.delete("step");
    params.delete("day");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false,
    });
  }, [pathname, router, searchParams]);

  const refreshOverviewState = useCallback(() => {
    fetchSummary();
    fetchTodayTasks();
    loadNextAction();
  }, [fetchSummary, fetchTodayTasks, loadNextAction]);

  const handleDaySaved = useCallback(() => {
    refreshOverviewState();
    router.refresh();
    window.setTimeout(() => {
      refreshOverviewState();
      router.refresh();
    }, 250);
  }, [refreshOverviewState, router]);

  const handleDayComplete = useCallback(() => {
    closeDayModal();
    handleDaySaved();
  }, [closeDayModal, handleDaySaved]);

  const handleTaskToggle = useCallback(
    async (taskId: string, checked: boolean) => {
      if (!todayTasks || todayTasks.day_number == null) return;
      const dayNumber = todayTasks.day_number;
      setTaskUpdateId(taskId);
      setTodayTasks((prev) =>
        prev
          ? {
              ...prev,
              tasks: prev.tasks.map((task) =>
                task.id === taskId ? { ...task, checked } : task,
              ),
            }
          : prev,
      );
      try {
        const updated = await sprintApi.toggleTodayTask(packId, {
          day_number: dayNumber,
          task_id: taskId,
          checked,
        });
        setTodayTasks(updated);
        refreshOverviewState();
      } catch {
        fetchTodayTasks();
      } finally {
        setTaskUpdateId(null);
      }
    },
    [fetchTodayTasks, packId, refreshOverviewState, todayTasks],
  );

  const handleStartSprint = useCallback(async () => {
    setStartingSprint(true);
    try {
      const sprint = await sprintApi.createSprint(packId);
      refreshOverviewState();
      openDayModal(sprint.current_day);
      router.refresh();
    } catch {
      fetchTodayTasks();
    } finally {
      setStartingSprint(false);
    }
  }, [fetchTodayTasks, openDayModal, packId, refreshOverviewState, router]);

  const handleExecuteToday = useCallback(() => {
    if (todayTasks?.day_number == null) return;
    openDayModal(todayTasks.day_number);
  }, [openDayModal, todayTasks]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error || !summary) {
    const maybeNotFound = /not found|404/i.test(error?.message ?? "");
    if (maybeNotFound) {
      return (
        <NotFoundView
          title="Pack not found"
          description="The campaign pack you requested does not exist or has been removed."
          primaryHref="/packs"
          primaryLabel="Back to packs"
          secondaryHref="/packs/new"
          secondaryLabel="Create new pack"
          className="min-h-[60vh]"
        />
      );
    }

    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-sm text-destructive">
          {error?.message ?? "Something went wrong loading this pack."}
        </p>
        <Button variant="outline" onClick={fetchSummary}>
          Retry
        </Button>
      </div>
    );
  }

  const { pack } = summary;
  const chips = nextAction?.actionChips ?? [];
  const hasNextStep = !!nextAction?.actionText || chips.length > 0;
  const hasSprintToday =
    !!todayTasks?.has_sprint && todayTasks.day_number != null;
  const primaryChipIndex = chips.findIndex((chip) => !!chip.href);
  const primaryChip = primaryChipIndex >= 0 ? chips[primaryChipIndex] : null;
  const hasWhatToDoNext = hasNextStep || hasSprintToday;
  const activeDayNumber = hasSprintToday ? todayTasks.day_number : null;
  const currentDayTaskCount = hasSprintToday ? todayTasks.tasks.length : 0;
  const checkedTaskCount = hasSprintToday
    ? todayTasks.tasks.filter((task) => task.checked).length
    : 0;
  const currentDayCompletionRatio =
    currentDayTaskCount > 0 ? checkedTaskCount / currentDayTaskCount : 0;
  const currentStepProgressPercent =
    activeDayNumber != null
      ? stepToPercent(activeDayNumber + currentDayCompletionRatio)
      : 0;
  const isCurrentDayComplete =
    currentDayTaskCount > 0 && checkedTaskCount === currentDayTaskCount;
  const renderedActionChips = chips.map((chip, i) => {
    if (!chip.href) return null;
    if (nextAction?.canProceed === false && primaryChipIndex === i) return null;

    const stepNumber = parseStepNumber(chip.label);

    if (stepNumber != null) {
      const progressPercent = stepToPercent(stepNumber);
      const roundedProgressPercent = Math.round(progressPercent);
      return (
        <Link
          key={i}
          href={chip.href}
          className="block px-5 py-3 text-sm hover:bg-muted/40 focus-visible:bg-muted/40 transition-colors"
        >
          <div className="space-y-2">
            <span className="block font-medium truncate">{chip.label}</span>
            <Progress
              value={progressPercent}
              className="h-1.5 bg-muted"
              role="progressbar"
              aria-label={`${chip.label} progress ${roundedProgressPercent} percent`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={roundedProgressPercent}
            />
          </div>
        </Link>
      );
    }

    return (
      <Link
        key={i}
        href={chip.href}
        className="flex items-center justify-between gap-3 px-5 py-3 text-sm hover:bg-muted/40 transition-colors"
      >
        <span className="font-medium truncate">{chip.label}</span>
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </Link>
    );
  });

  return (
    <div className="flex flex-col p-8 lg:h-full lg:overflow-hidden">
      <div className="flex flex-col gap-6 lg:flex-1 lg:min-h-0 lg:flex-row lg:overflow-hidden">
        <div className="flex flex-col min-w-0 w-full lg:flex-1 lg:min-h-0 lg:overflow-hidden">
          <div className="flex flex-col space-y-8 lg:flex-1 lg:min-h-0 lg:overflow-y-auto">
            {pack.core_concept && (
              <motion.section
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.02 }}
                className="shrink-0 rounded-2xl border border-border/60 bg-muted/30 px-5 py-4"
              >
                <p className="text-sm text-foreground/90 leading-relaxed">
                  {pack.core_concept}
                </p>
              </motion.section>
            )}

            {hasWhatToDoNext && (
              <motion.section
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.04 }}
                className="shrink-0 space-y-3"
              >
                <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  What to do next
                </h2>
                <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
                  {hasSprintToday ? (
                    <>
                      <div className="px-5 py-4 border-b border-border flex items-start justify-between gap-4">
                        <div className="space-y-2 min-w-0">
                          <p className="text-sm font-semibold text-foreground">
                            Step {todayTasks?.day_number}:{" "}
                            {todayTasks?.day_title ?? "Current step"}
                          </p>
                          {todayTasks?.overview && (
                            <div className="max-w-prose">
                              <p className="text-xs text-muted-foreground line-clamp-2">
                                {todayTasks.overview}
                              </p>
                            </div>
                          )}
                          {(todayTasks?.time_estimate ||
                            nextAction?.progressCounters) && (
                            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                              {todayTasks?.time_estimate && (
                                <span>{todayTasks.time_estimate}</span>
                              )}
                              {nextAction?.progressCounters &&
                                Object.entries(nextAction.progressCounters).map(
                                  ([k, v]) => (
                                    <span key={k}>
                                      {k}: {v}
                                    </span>
                                  ),
                                )}
                            </div>
                          )}
                          {nextAction?.blockerMessage && (
                            <p
                              className="text-xs text-amber-600 dark:text-amber-400"
                              role="alert"
                            >
                              {nextAction.blockerMessage}
                            </p>
                          )}
                        </div>
                        {nextAction?.canProceed === false &&
                        primaryChip?.href ? (
                          <Link href={primaryChip.href} className="shrink-0">
                            <Button size="sm">{primaryChip.label}</Button>
                          </Link>
                        ) : (
                          <div className="execute-now-cta-ring shrink-0">
                            <Button
                              onClick={handleExecuteToday}
                              size="md"
                              className="execute-now-cta hover:scale-100 focus-visible:scale-100 active:scale-100 hover:!text-white"
                            >
                              Execute now
                            </Button>
                          </div>
                        )}
                      </div>
                      {activeDayNumber != null && (
                        <div className="px-5 py-3 border-b border-border space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/80">
                              Sprint progress
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Step {activeDayNumber} of {TOTAL_SPRINT_STEPS}
                            </p>
                          </div>
                          <div className="space-y-2">
                            <div className="relative">
                              <Progress
                                value={currentStepProgressPercent}
                                className="h-2 bg-muted/70"
                                role="progressbar"
                                aria-label={`Sprint progress ${Math.round(currentStepProgressPercent)} percent`}
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-valuenow={Math.round(
                                  currentStepProgressPercent,
                                )}
                              />
                              <div className="pointer-events-none absolute inset-0 flex items-center justify-between px-[1px]">
                                {Array.from(
                                  { length: TOTAL_SPRINT_STEPS + 1 },
                                  (_, stepNumber) => (
                                    <span
                                      key={stepNumber}
                                      className={[
                                        "h-2 w-px rounded-full",
                                        stepNumber <= activeDayNumber
                                          ? "bg-emerald-500/40"
                                          : "bg-border/80",
                                      ].join(" ")}
                                    />
                                  ),
                                )}
                              </div>
                            </div>
                            <div className="flex items-center justify-between gap-2 text-[11px]">
                              <p className="text-muted-foreground">
                                {DAY_TITLES[activeDayNumber]}
                              </p>
                              {currentDayTaskCount > 0 && (
                                <p className="text-muted-foreground">
                                  {checkedTaskCount}/{currentDayTaskCount} tasks
                                </p>
                              )}
                            </div>
                          </div>
                          <p
                            className={[
                              "text-[11px] inline-flex items-center gap-1",
                              isCurrentDayComplete
                                ? "text-emerald-700 dark:text-emerald-300"
                                : "text-muted-foreground",
                            ].join(" ")}
                          >
                            {isCurrentDayComplete ? (
                              <Check className="h-3.5 w-3.5" />
                            ) : (
                              <Lock className="h-3.5 w-3.5" />
                            )}
                            {isCurrentDayComplete
                              ? "Current step complete. Next step unlocked."
                              : "Next step stays locked until this step is complete."}
                          </p>
                        </div>
                      )}
                      {/* <div className="divide-y divide-border">
                        {renderedActionChips}
                      </div> */}
                    </>
                  ) : (
                    <>
                      {nextAction?.actionText && (
                        <div className="px-5 py-4 border-b border-border space-y-2">
                          <p className="text-sm font-medium text-foreground">
                            {nextAction.actionText}
                          </p>
                          {nextAction.whyItMatters && (
                            <p className="text-xs text-muted-foreground">
                              {nextAction.whyItMatters}
                            </p>
                          )}
                          {(nextAction.timeEstimate ||
                            nextAction.progressCounters) && (
                            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                              {nextAction.timeEstimate && (
                                <span>{nextAction.timeEstimate}</span>
                              )}
                              {nextAction.progressCounters &&
                                Object.entries(nextAction.progressCounters).map(
                                  ([k, v]) => (
                                    <span key={k}>
                                      {k}: {v}
                                    </span>
                                  ),
                                )}
                            </div>
                          )}
                          {nextAction.blockerMessage && (
                            <p
                              className="text-xs text-amber-600 dark:text-amber-400"
                              role="alert"
                            >
                              {nextAction.blockerMessage}
                            </p>
                          )}
                        </div>
                      )}
                      <div className="divide-y divide-border">
                        {renderedActionChips}
                      </div>
                    </>
                  )}
                </div>
              </motion.section>
            )}

            <motion.section
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 }}
              className="shrink-0 space-y-3"
            >
              <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Today&apos;s tasks
              </h2>
              <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
                {todayTasksLoading ? (
                  <div className="px-5 py-6">
                    <p className="text-sm text-muted-foreground">
                      Loading today&apos;s tasks...
                    </p>
                  </div>
                ) : todayTasksError ? (
                  <div className="px-5 py-6 space-y-3">
                    <p className="text-sm text-destructive">
                      {todayTasksError.message ||
                        "Could not load today's tasks."}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={fetchTodayTasks}
                    >
                      Retry
                    </Button>
                  </div>
                ) : !todayTasks?.has_sprint ? (
                  <div className="px-5 py-6 space-y-4">
                    <p className="text-sm text-muted-foreground">
                      Start your sprint from What to do next to unlock
                      today&apos;s checklist.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="px-5 py-4 border-b border-border">
                      <p className="text-sm font-semibold text-foreground">
                        Checklist
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Track progress for today&apos;s step tasks.
                      </p>
                    </div>
                    <div className="px-5 py-4 space-y-3">
                      {todayTasks.tasks.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No checklist items generated yet.
                        </p>
                      ) : (
                        todayTasks.tasks.map((task) => {
                          const disabled = taskUpdateId === task.id;
                          return (
                            <label
                              key={task.id}
                              className="flex items-start gap-3 text-sm"
                            >
                              <Checkbox
                                checked={task.checked}
                                disabled={disabled}
                                onCheckedChange={(checked) =>
                                  handleTaskToggle(task.id, checked)
                                }
                                className="mt-0.5"
                              />
                              <span className="leading-relaxed">
                                {task.label}
                              </span>
                            </label>
                          );
                        })
                      )}
                    </div>
                  </>
                )}
              </div>
            </motion.section>

            <motion.section
              variants={container}
              initial="hidden"
              animate="visible"
              className="flex flex-col space-y-3 lg:flex-1 lg:min-h-0"
            >
              <div className="shrink-0 flex items-center justify-between gap-3">
                <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Pack summary
                </h2>
                <PackActionsMenu
                  pack={pack}
                  onArchive={handleArchive}
                  onRestore={handleRestore}
                  onDelete={handleDelete}
                />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:flex-1 lg:min-h-0">
                {PACK_SUMMARY_CARDS.map((moduleKey, index) => {
                  const mod = PACK_OVERVIEW_MODULES[moduleKey];
                  if (!mod) return null;
                  const isThird = index === 2;
                  return (
                    <SummarySection
                      key={moduleKey}
                      title={mod.title}
                      href={
                        mod.getHref
                          ? mod.getHref(packId)
                          : `/packs/${packId}${mod.hrefSuffix}`
                      }
                      icon={mod.icon}
                      emptyMessage={mod.emptyMessage}
                      className={isThird ? "col-span-2" : undefined}
                    >
                      {mod.getContent(summary)}
                    </SummarySection>
                  );
                })}
              </div>
            </motion.section>
          </div>
        </div>

        <div className="w-[380px] shrink-0 min-h-0 flex flex-col hidden lg:flex">
          <PackChatPanel packId={packId} />
        </div>
      </div>

      {dayModalOpen !== null && (
        <>
          {dayModalOpen === 0 && (
            <Day0Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDayComplete}
            />
          )}
          {dayModalOpen === 1 && (
            <Day1Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDaySaved}
              onGoToNextStep={() => openDayModal(2)}
            />
          )}
          {dayModalOpen === 2 && (
            <Day2Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDaySaved}
              onGoToNextStep={() => openDayModal(3)}
            />
          )}
          {dayModalOpen === 3 && (
            <Day3Modal
              open={true}
              onClose={closeDayModal}
              packId={packId}
              onComplete={handleDaySaved}
              onGoToNextStep={() => openDayModal(4)}
            />
          )}
          {dayModalOpen >= 4 && dayModalOpen <= 14 && (
            <DayDetailModal
              packId={packId}
              dayNumber={dayModalOpen}
              open={true}
              onClose={closeDayModal}
              onComplete={handleDayComplete}
            />
          )}
        </>
      )}
    </div>
  );
}
