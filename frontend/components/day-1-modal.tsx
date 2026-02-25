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

export function Day1Modal({
  open,
  onClose,
  packId,
  onComplete,
}: {
  open: boolean;
  onClose: () => void;
  packId: string;
  onComplete?: () => void;
}) {
  const [pack, setPack] = useState<Pack | null>(null);
  const [sprintId, setSprintId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [offerOneLiner, setOfferOneLiner] = useState("");
  const [refiningOffer, setRefiningOffer] = useState(false);
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
        const current = (p?.offer_one_liner ?? "").trim();
        setOfferOneLiner(current);
        if (!current && s?.id) {
          setSuggestingInitial(true);
          sprintApi
            .suggestDayFields(packId, 1)
            .then((res) => {
              if (res.offer_one_liner) setOfferOneLiner(res.offer_one_liner);
            })
            .catch(() => {})
            .finally(() => setSuggestingInitial(false));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [open, packId]);

  async function handleRefineOffer() {
    setRefiningOffer(true);
    try {
      const res = await sprintApi.suggestField(packId, {
        day: 1,
        field: "offer_one_liner",
        current_value: offerOneLiner || undefined,
      });
      setOfferOneLiner(res.suggestion);
    } catch {
      setError("Could not get suggestion");
    } finally {
      setRefiningOffer(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = offerOneLiner.trim();
    if (!value) return;
    if (!sprintId) {
      setError("No active sprint. Start a sprint from the plan tracker.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await sprintApi.completeDay(packId, sprintId, 1, {
        offer_one_liner: value,
      });
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete Day 1");
    } finally {
      setSaving(false);
    }
  };

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
          aria-labelledby="day1-modal-title"
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
              id="day1-modal-title"
              className="font-heading text-2xl font-bold text-foreground pr-10"
            >
              Day 1: Offer
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Lock down what you&apos;re selling in one clear sentence. This is the foundation of your marketing.
            </p>

            {loading ? (
              <div className="mt-6 min-h-[120px] flex items-center">
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : !sprintId ? (
              <div className="mt-6 min-h-[120px] flex items-center">
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  No active sprint. Go to Plan tracker and start a sprint first.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label htmlFor="day1-offer">
                      Offer one-liner <span className="text-red-500">*</span>
                    </Label>
                    <button
                      type="button"
                      onClick={handleRefineOffer}
                      disabled={suggestingInitial || refiningOffer || saving}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {refiningOffer || suggestingInitial ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      Refine with AI
                    </button>
                  </div>
                  {suggestingInitial || refiningOffer ? (
                    <Skeleton className="h-[5rem] w-full" />
                  ) : (
                    <Textarea
                      id="day1-offer"
                      value={offerOneLiner}
                      onChange={(e) => setOfferOneLiner(e.target.value)}
                      placeholder="e.g. We help busy founders get a steady stream of qualified leads without paid ads."
                      rows={4}
                      required
                      disabled={saving}
                      className="resize-none"
                    />
                  )}
                  <p className="text-xs text-muted-foreground">
                    What exactly are you selling? One sentence someone can say yes or no to.
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
                  <Button type="submit" disabled={!offerOneLiner.trim() || saving}>
                    {saving ? "Saving…" : "Lock offer & complete Day 1"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
