"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Check, FileText, X, Lock } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { sprintApi } from "@/api_requests/sprint";
import type { SprintDayDetail } from "@/types/api-types";
import { DayGuideModal } from "@/app/(dashboard)/packs/[packId]/plan-tracker/day/[dayNumber]/_components/DayGuideModal";
import { OutreachLogger } from "@/components/outreach-logger";
import { OutputShippedLogger } from "@/components/output-shipped-logger";
import { ProofLogger } from "@/components/proof-logger";
import { ResponseRulesEditor } from "@/components/response-rules-editor";

const DAY_LABELS: Record<number, string> = {
  0: "Day 0: Foundation",
  1: "Day 1: Offer",
  2: "Day 2: USP + Audience",
  3: "Day 3: Confidence script",
  4: "Day 4: Ad Factory",
  5: "Day 5: Posters",
  6: "Day 6: Conversion destination",
  7: "Day 7: Publish / Confirm",
  8: "Day 8: Response rules",
  9: "Day 9: Follow-up",
  10: "Day 10: Fix the leak",
  11: "Day 11: Close path",
  12: "Day 12: Close conversations",
  13: "Day 13: Invoice / Payment",
  14: "Day 14: Check-in",
};

const DEFAULT_DEFINITION_OF_DONE: Record<number, string> = {
  0: "USP locked and CTA confirmed.",
  1: "Offer updated or locked (build: create offer + price range; improve: audit + tighten).",
  2: "USP visible in messaging (build: create USP + audience; improve: extract from reviews/site).",
  3: "Pitch script created and objections handled.",
  4: "Scripts and shot list generated; content shipped; outreach logged.",
  5: "Poster variants generated and posted; broadcast sent.",
  6: "Conversion destination ready (build: page draft; improve: optimised).",
  7: "Link shared with 10 people; destination confirmed and proof added.",
  8: "Response rules locked and outreach habit started.",
  9: "Follow-up queue cleared.",
  10: "One improvement applied live.",
  11: "Proposal (service/coach) or bundle offer (product) ready.",
  12: "Conversations closed with next step.",
  13: "Invoice or payment request sent.",
  14: "Check-in complete and Sprint 2 created.",
};

export function DayDetailModal({
  packId,
  dayNumber,
  open: isOpen,
  onClose,
  onComplete,
}: {
  packId: string;
  dayNumber: number;
  open: boolean;
  onClose: () => void;
  onComplete?: () => void;
}) {
  const [detail, setDetail] = useState<SprintDayDetail | null>(null);
  const [sprint, setSprint] = useState<{
    id: string;
    current_day: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const [error, setError] = useState("");
  const [showGuideModal, setShowGuideModal] = useState(false);

  const isValidDay =
    Number.isInteger(dayNumber) && dayNumber >= 4 && dayNumber <= 14;

  useEffect(() => {
    if (!isOpen || !packId || !isValidDay) return;
    setError("");
    setLoading(true);
    Promise.all([
      sprintApi.getSprint(packId),
      sprintApi.getSprintDay(packId, dayNumber),
    ])
      .then(([s, d]) => {
        setSprint(s ? { id: s.id, current_day: s.current_day } : null);
        setDetail(d ?? null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, [isOpen, packId, dayNumber, isValidDay]);

  const handleComplete = async () => {
    if (!sprint) return;
    setCompleting(true);
    setError("");
    try {
      await sprintApi.completeDay(packId, sprint.id, dayNumber);
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete");
    } finally {
      setCompleting(false);
    }
  };

  const handleCheckIn = async () => {
    if (!sprint || dayNumber !== 14) return;
    setCheckingIn(true);
    setError("");
    try {
      await sprintApi.checkIn(packId, sprint.id);
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check in");
    } finally {
      setCheckingIn(false);
    }
  };

  const refetchDay = () => {
    if (!isValidDay) return;
    sprintApi
      .getSprintDay(packId, dayNumber)
      .then(setDetail)
      .catch(() => {});
  };

  const handleLogOutreach = async (increment = 1) => {
    if (!sprint) return;
    try {
      await sprintApi.logOutreach(sprint.id, dayNumber, increment);
      refetchDay();
    } catch {
      setError("Failed to log outreach");
    }
  };
  const handleLogFollowup = async () => {
    if (!sprint) return;
    try {
      await sprintApi.logFollowup(sprint.id, dayNumber, 1);
      refetchDay();
    } catch {
      setError("Failed to log follow-up");
    }
  };
  const handleLogProof = async () => {
    if (!sprint) return;
    try {
      await sprintApi.logProof(sprint.id, dayNumber);
      refetchDay();
    } catch {
      setError("Failed to log proof");
    }
  };
  const handleMarkOutputShipped = async () => {
    if (!sprint) return;
    try {
      await sprintApi.markOutputShipped(sprint.id, dayNumber);
      refetchDay();
    } catch {
      setError("Failed to mark output shipped");
    }
  };

  const canComplete =
    sprint && !detail?.completed_at && detail?.unlocked !== false;
  const isDay14 = dayNumber === 14;
  const showDailyProgress =
    detail &&
    sprint &&
    dayNumber >= 4 &&
    dayNumber <= 13 &&
    !detail.completed_at &&
    detail.unlocked !== false;

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        key="day-detail-overlay"
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 overflow-y-auto"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.2 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="day-detail-modal-title"
          className="pointer-events-auto w-full max-w-[560px] max-h-[90vh] rounded-2xl border border-border bg-card shadow shadow-black/10 flex flex-col my-8"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative p-6 pb-4 shrink-0 border-b">
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <h2
              id="day-detail-modal-title"
              className="font-heading text-xl font-bold text-foreground pr-10"
            >
              {DAY_LABELS[dayNumber] ?? `Day ${dayNumber}`}
            </h2>
          </div>

          <div className="p-6 overflow-y-auto flex-1 min-h-0">
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : error && !detail && !sprint ? (
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            ) : (
              <>
                {detail && detail.unlocked === false && (
                  <Card className="mb-4 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30">
                    <CardContent className="flex items-start gap-3 py-4">
                      <Lock className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                          Day {dayNumber} is locked
                        </p>
                        <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                          {detail.blocker_message ?? `Complete the previous day to unlock Day ${dayNumber}.`}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}
                {detail && (
                  <Card
                    className="mb-4 cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => setShowGuideModal(true)}
                  >
                    <CardHeader className="py-4">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base">Details</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2 pt-0">
                      <p className="text-sm font-medium text-muted-foreground">
                        Definition of done
                      </p>
                      <p className="text-sm">
                        {detail.definition_of_done ??
                          DEFAULT_DEFINITION_OF_DONE[dayNumber] ??
                          `Complete the tasks for Day ${dayNumber}.`}
                      </p>
                      <p className="text-sm text-primary font-medium">
                        Click to view tasks and guide →
                      </p>
                      {detail.completed_at && (
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
                          <Check className="h-4 w-4" /> Completed
                        </div>
                      )}
                      {error && (
                        <p className="text-sm text-red-600 dark:text-red-400">
                          {error}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}
                {dayNumber === 4 && (
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground mb-2">
                      Generate scripts and shot list:
                    </p>
                    <Link href={`/packs/${packId}/ad-factory`}>
                      <Button variant="outline" size="sm">
                        Open Ad Factory
                      </Button>
                    </Link>
                  </div>
                )}
                {dayNumber === 5 && (
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground mb-2">
                      Generate poster variants:
                    </p>
                    <Link href={`/packs/${packId}/posters`}>
                      <Button variant="outline" size="sm">
                        Open Posters
                      </Button>
                    </Link>
                  </div>
                )}
                {dayNumber === 6 && (
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground mb-2">
                      Create or optimise your website:
                    </p>
                    <Link href={`/packs/${packId}/website`}>
                      <Button variant="outline" size="sm">
                        Open Website
                      </Button>
                    </Link>
                  </div>
                )}
                {dayNumber === 8 && (
                  <div className="mb-4">
                    <ResponseRulesEditor packId={packId} onLock={refetchDay} />
                  </div>
                )}
                {showDailyProgress && detail && sprint && (
                  <Card className="mb-4">
                    <CardHeader className="py-4">
                      <CardTitle className="text-base">
                        Daily progress
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Complete these to enable &quot;Mark complete&quot;.
                      </p>
                    </CardHeader>
                    <CardContent className="pt-0 space-y-0">
                      <div className="flex flex-col divide-y divide-border">
                        <div className="py-3">
                          <OutputShippedLogger
                            shipped={!!detail.output_shipped}
                            onMarkShipped={handleMarkOutputShipped}
                          />
                        </div>
                        <div className="py-3 flex flex-col gap-2">
                          <OutreachLogger
                            count={detail.outreach_count ?? 0}
                            target={detail.outreach_target ?? 10}
                            onLog={handleLogOutreach}
                          />
                          <div
                            className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
                            role="progressbar"
                            aria-valuenow={detail.outreach_count ?? 0}
                            aria-valuemin={0}
                            aria-valuemax={detail.outreach_target ?? 10}
                          >
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{
                                width: `${Math.min(
                                  100,
                                  ((detail.outreach_count ?? 0) /
                                    (detail.outreach_target ?? 10)) *
                                    100
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                        <div className="py-3 flex flex-col gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm text-muted-foreground">
                              Follow-ups:
                            </span>
                            <span className="text-sm font-medium">
                              {detail.followup_count ?? 0} /{" "}
                              {detail.followup_target ?? 5}
                            </span>
                            {(detail.followup_count ?? 0) >=
                            (detail.followup_target ?? 5) ? (
                              <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                                <Check className="h-4 w-4" /> Done
                              </span>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={handleLogFollowup}
                              >
                                +1
                              </Button>
                            )}
                          </div>
                          <div
                            className="h-1.5 w-full rounded-full bg-muted overflow-hidden"
                            role="progressbar"
                            aria-valuenow={detail.followup_count ?? 0}
                            aria-valuemin={0}
                            aria-valuemax={detail.followup_target ?? 5}
                          >
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{
                                width: `${Math.min(
                                  100,
                                  ((detail.followup_count ?? 0) /
                                    (detail.followup_target ?? 5)) *
                                    100
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                        <div className="py-3">
                          <ProofLogger
                            logged={!!detail.proof_logged}
                            onLog={handleLogProof}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
                {canComplete && (
                  <div className="pt-2">
                    {isDay14 ? (
                      <Button
                        onClick={handleCheckIn}
                        disabled={checkingIn}
                        className="w-full"
                      >
                        {checkingIn
                          ? "Checking in…"
                          : "Day 14 check-in & start Sprint 2"}
                      </Button>
                    ) : (
                      <Button
                        onClick={handleComplete}
                        disabled={completing}
                        className="w-full"
                      >
                        {completing ? "Saving…" : "Mark complete"}
                      </Button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </motion.div>
      </div>

      <DayGuideModal
        key="day-guide-modal"
        dayNumber={dayNumber}
        open={showGuideModal}
        onOpenChange={setShowGuideModal}
      />
    </AnimatePresence>
  );
}
