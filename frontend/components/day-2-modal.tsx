"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Sparkles, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { packs } from "@/api_requests/packs";
import { sprintApi } from "@/api_requests/sprint";
import type { Pack } from "@/types/api-types";

export function Day2Modal({
  open,
  onClose,
  packId,
  onComplete,
  onGoToNextStep,
}: {
  open: boolean;
  onClose: () => void;
  packId: string;
  onComplete?: () => void;
  onGoToNextStep?: () => void;
}) {
  const [pack, setPack] = useState<Pack | null>(null);
  const [sprintId, setSprintId] = useState<string | null>(null);
  const [dayComplete, setDayComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [primaryPain, setPrimaryPain] = useState("");
  const [primaryOutcome, setPrimaryOutcome] = useState("");
  const [refiningPain, setRefiningPain] = useState(false);
  const [refiningOutcome, setRefiningOutcome] = useState(false);
  const [suggestingInitial, setSuggestingInitial] = useState(false);

  useEffect(() => {
    if (!open || !packId) return;
    setError("");
    setLoading(true);
    setSuggestingInitial(false);
    Promise.all([packs.get(packId), sprintApi.getSprint(packId)])
      .then(([p, s]) => {
        setPack(p ?? null);
        setSprintId(s?.id ?? null);
        const completed =
          s?.day_cards?.some((c) => c.day_number === 2 && c.completed_at) ?? false;
        setDayComplete(completed);
        const pain = (p?.primary_pain ?? "").trim();
        const outcome = (p?.primary_outcome ?? "").trim();
        setPrimaryPain(pain);
        setPrimaryOutcome(outcome);
        if ((!pain || !outcome) && s?.id) {
          setSuggestingInitial(true);
          sprintApi
            .suggestDayFields(packId, 2)
            .then((res) => {
              if (res.primary_pain) setPrimaryPain(res.primary_pain);
              if (res.primary_outcome) setPrimaryOutcome(res.primary_outcome);
            })
            .catch(() => {})
            .finally(() => setSuggestingInitial(false));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [open, packId]);

  async function handleRefinePain() {
    setRefiningPain(true);
    setError("");
    try {
      const res = await sprintApi.suggestField(packId, {
        day: 2,
        field: "primary_pain",
        current_value: primaryPain || undefined,
      });
      if (res.source === "fallback") {
        setError(res.reason ?? "AI suggestions are currently unavailable.");
        return;
      }
      setPrimaryPain(res.suggestion);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not get suggestion");
    } finally {
      setRefiningPain(false);
    }
  }

  async function handleRefineOutcome() {
    setRefiningOutcome(true);
    setError("");
    try {
      const res = await sprintApi.suggestField(packId, {
        day: 2,
        field: "primary_outcome",
        current_value: primaryOutcome || undefined,
      });
      if (res.source === "fallback") {
        setError(res.reason ?? "AI suggestions are currently unavailable.");
        return;
      }
      setPrimaryOutcome(res.suggestion);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not get suggestion");
    } finally {
      setRefiningOutcome(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const pain = primaryPain.trim();
    const outcome = primaryOutcome.trim();
    if (!pain || !outcome) return;
    if (!sprintId) {
      setError("No active sprint. Start a sprint from Overview.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await sprintApi.completeDay(packId, sprintId, 2, {
        primary_pain: pain,
        primary_outcome: outcome,
      });
      setDayComplete(true);
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete Step 2");
    } finally {
      setSaving(false);
    }
  };

  const isValid = primaryPain.trim().length > 0 && primaryOutcome.trim().length > 0;

  if (!open) return null;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.2 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="day2-modal-title"
          className="pointer-events-auto w-full max-w-[560px] rounded-2xl border border-border bg-card shadow shadow-black/10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative p-7 sm:p-9">
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <h2
              id="day2-modal-title"
              className="font-heading text-2xl font-bold text-foreground pr-10"
            >
              Step 2: USP + Audience
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Define the primary pain point your audience faces and the outcome they desire.
            </p>

            {loading ? (
              <div className="mt-6 min-h-[120px] flex items-center">
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : !sprintId ? (
              <div className="mt-6 min-h-[120px] flex items-center">
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  No active sprint. Go to Overview and start a sprint first.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="day2-pain">
                      Primary pain point <span className="text-red-500">*</span>
                    </Label>
                    <button
                      type="button"
                      onClick={handleRefinePain}
                      disabled={suggestingInitial || refiningPain || saving}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {refiningPain || suggestingInitial ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      Refine with AI
                    </button>
                  </div>
                  {suggestingInitial || refiningPain ? (
                    <Skeleton className="h-[4.5rem] w-full" />
                  ) : (
                    <Textarea
                      id="day2-pain"
                      value={primaryPain}
                      onChange={(e) => setPrimaryPain(e.target.value)}
                      placeholder="What is the main problem or frustration your target audience experiences?"
                      rows={3}
                      required
                      disabled={saving}
                      className="resize-none"
                    />
                  )}
                  <p className="text-xs text-muted-foreground">
                    Example: &quot;Struggling to generate consistent leads for their business&quot;
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="day2-outcome">
                      Primary outcome <span className="text-red-500">*</span>
                    </Label>
                    <button
                      type="button"
                      onClick={handleRefineOutcome}
                      disabled={suggestingInitial || refiningOutcome || saving}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {refiningOutcome || suggestingInitial ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      Refine with AI
                    </button>
                  </div>
                  {suggestingInitial || refiningOutcome ? (
                    <Skeleton className="h-[4.5rem] w-full" />
                  ) : (
                    <Textarea
                      id="day2-outcome"
                      value={primaryOutcome}
                      onChange={(e) => setPrimaryOutcome(e.target.value)}
                      placeholder="What is the desired result or transformation they want to achieve?"
                      rows={3}
                      required
                      disabled={saving}
                      className="resize-none"
                    />
                  )}
                  <p className="text-xs text-muted-foreground">
                    Example: &quot;A steady stream of qualified leads without paid ads&quot;
                  </p>
                </div>
                {error && (
                  <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                    {error}
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!isValid || saving || dayComplete}>
                    {saving ? "Saving…" : dayComplete ? "Step 2 complete" : "Complete Step 2"}
                  </Button>
                  {dayComplete && (
                    <Button
                      type="button"
                      onClick={onGoToNextStep}
                      disabled={saving || !onGoToNextStep}
                    >
                      Go to next step
                    </Button>
                  )}
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
