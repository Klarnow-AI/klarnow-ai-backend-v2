"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Target,
  Megaphone,
  FileCode,
  Calendar,
  Users,
  FileCheck,
  Receipt,
  ChevronRight,
  Film,
} from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { packs as packsApi, me } from "@/lib/api";
import type { Pack, PackSummaryResponse } from "@/types/api-types";
import { PackActionsMenu } from "@/components/pack-actions-menu";
import { PackChatPanel } from "./_components/pack-chat-panel";
import { useGet } from "@/hooks/use-get";

const PACK_TYPE_LABELS: Record<string, string> = {
  enquiries: "Enquiries",
  quotes: "Quotes",
  sales: "Sales",
};

function getStageLabel(stage: string | undefined): string {
  if (!stage || stage === "no_pack") return "Setup";
  if (stage === "brand_os_done") return "Foundation";
  if (stage === "page_live") return "Page live";
  if (stage === "sprint") return "Sprint";
  if (stage === "leads") return "Leads";
  return "In progress";
}

/** Fixed pack summary cards — no add/remove. */
const PACK_SUMMARY_CARDS: string[] = ["brand_os", "plan_tracker"];

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
  conversion_page: {
    title: "Website",
    hrefSuffix: "/website",
    icon: FileCode,
    emptyMessage: "No published page. Create and publish in Website.",
    getContent: (s) =>
      s.conversion_page ? (
        <>
          {s.conversion_page.live_url ? (
            <p>
              <span className="font-medium text-muted-foreground">Live:</span>{" "}
              <a
                href={s.conversion_page.live_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline break-all"
              >
                {s.conversion_page.live_url}
              </a>
            </p>
          ) : (
            <p className="text-muted-foreground">Draft only — not published.</p>
          )}
          {s.conversion_page.published_at && (
            <p className="text-xs text-muted-foreground">
              Published{" "}
              {new Date(s.conversion_page.published_at).toLocaleDateString()}
            </p>
          )}
        </>
      ) : null,
  },
  plan_tracker: {
    title: "Plan & Tracker",
    hrefSuffix: "/plan-tracker",
    icon: Calendar,
    emptyMessage:
      "Start your 14-day sprint to publish, launch, capture leads, and get paid.",
    getContent: (s) =>
      s.plan_tracker?.has_sprint ? (
        <p>
          <span className="font-medium text-muted-foreground">
            14-day sprint
          </span>
          {s.plan_tracker.sprint_day != null && (
            <> — Day {s.plan_tracker.sprint_day} of 14</>
          )}
        </p>
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
      className={`rounded-2xl border border-border bg-card overflow-hidden min-h-0 flex flex-col ${className ?? ""}`}
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
      <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4">
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
  const router = useRouter();
  const packId = params.packId as string;
  const [nextAction, setNextAction] = useState<Awaited<
    ReturnType<typeof me.getNextAction>
  > | null>(null);

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

  useEffect(() => {
    if (!packId) return;
    me.getNextAction(packId)
      .then(setNextAction)
      .catch(() => setNextAction(null));
  }, [packId]);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error || !summary) {
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
  const stageLabel = nextAction ? getStageLabel(nextAction.stage) : null;
  const chips = nextAction?.actionChips ?? [];
  const hasNextStep = !!nextAction?.actionText || chips.length > 0;

  return (
    <div className="flex flex-col h-full overflow-hidden p-8">
      <motion.header
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur-md -mx-8 px-8 py-4 mb-6"
      >
        <div className="max-w-8xl mx-auto flex flex-wrap items-center justify-between gap-8">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            <h1 className="text-xl font-semibold tracking-tight truncate">
              {pack.name}
            </h1>
            {pack.pack_type && (
              <span
                className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground shrink-0"
                aria-label={`Pack type: ${PACK_TYPE_LABELS[pack.pack_type] ?? pack.pack_type}`}
              >
                {PACK_TYPE_LABELS[pack.pack_type] ?? pack.pack_type}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {stageLabel && (
              <span
                className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                aria-label={`Stage: ${stageLabel}`}
              >
                {stageLabel}
              </span>
            )}
            <PackActionsMenu
              pack={pack}
              onArchive={handleArchive}
              onRestore={handleRestore}
              onDelete={handleDelete}
            />
          </div>
        </div>
      </motion.header>

      <div className="flex flex-1 min-h-0 gap-6 overflow-hidden">
        <div className="flex flex-col flex-1 min-w-0 min-h-0 overflow-hidden max-w-6xl">
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col space-y-8">
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

            {hasNextStep && (
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
                    {chips.map((chip, i) =>
                      chip.href ? (
                        <Link
                          key={i}
                          href={chip.href}
                          className="flex items-center justify-between gap-3 px-5 py-3 text-sm hover:bg-muted/40 transition-colors"
                        >
                          <span className="font-medium truncate">
                            {chip.label}
                          </span>
                          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                        </Link>
                      ) : null,
                    )}
                  </div>
                </div>
              </motion.section>
            )}

            <motion.section
              variants={container}
              initial="hidden"
              animate="visible"
              className="flex flex-1 min-h-0 flex flex-col space-y-3"
            >
              <h2 className="shrink-0 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Pack summary
              </h2>
              <div className="grid flex-1 min-h-0 grid-cols-2 grid-rows-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
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

        <div className="w-[380px] shrink-0 min-h-0 flex flex-col">
          <PackChatPanel packId={packId} />
        </div>
      </div>
    </div>
  );
}
