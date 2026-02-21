"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Sparkles, X } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { sprintApi } from "@/api_requests/sprint";

export function Day3Modal({
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
  const [sprintId, setSprintId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pitchScript, setPitchScript] = useState("");
  const [voiceNotesSent, setVoiceNotesSent] = useState(false);
  const [refiningPitch, setRefiningPitch] = useState(false);

  useEffect(() => {
    if (!open || !packId) return;
    setError("");
    setLoading(true);
    sprintApi
      .getSprint(packId)
      .then((s) => {
        setSprintId(s?.id ?? null);
        if (s?.id) {
          sprintApi.suggestDayFields(packId, 3).then((res) => {
            if (res.pitch_script) setPitchScript(res.pitch_script);
          }).catch(() => {});
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [open, packId]);

  async function handleRefinePitch() {
    setRefiningPitch(true);
    try {
      const res = await sprintApi.suggestField(packId, {
        day: 3,
        field: "pitch_script",
        current_value: pitchScript || undefined,
      });
      setPitchScript(res.suggestion);
    } catch {
      setError("Could not get suggestion");
    } finally {
      setRefiningPitch(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sprintId) {
      setError("No active sprint. Start a sprint from the plan tracker.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await sprintApi.completeDay(packId, sprintId, 3, {
        ...(pitchScript.trim() && { pitch_script: pitchScript.trim() }),
        voice_notes_sent: String(voiceNotesSent),
      });
      onComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete Day 3");
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
          aria-labelledby="day3-modal-title"
          className="pointer-events-auto w-full max-w-[560px] rounded-2xl border border-border bg-card shadow shadow-black/10 max-h-[90vh] overflow-y-auto"
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
              id="day3-modal-title"
              className="font-heading text-2xl font-bold text-foreground pr-10"
            >
              Day 3: Confidence script
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Build: write your pitch script and send 3 voice notes. Improve: list common objections and craft responses.
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
                    <Label htmlFor="day3-pitch">
                      Pitch script (under 60 seconds)
                    </Label>
                    <button
                      type="button"
                      onClick={handleRefinePitch}
                      disabled={refiningPitch || saving}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {refiningPitch ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      Refine with AI
                    </button>
                  </div>
                  <Textarea
                    id="day3-pitch"
                    value={pitchScript}
                    onChange={(e) => setPitchScript(e.target.value)}
                    placeholder="Hi [Name], I help [who] with [problem]. Most people struggle with [pain], but we [solution]. Interested in [CTA]?"
                    rows={4}
                    disabled={saving}
                    className="resize-none"
                  />
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={voiceNotesSent}
                    onChange={(e) => setVoiceNotesSent(e.target.checked)}
                    disabled={saving}
                    className="h-4 w-4 rounded border-border"
                  />
                  <span className="text-sm">I&apos;ve sent 3 voice notes to potential customers</span>
                </label>
                {error && (
                  <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                    {error}
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={saving}>
                    {saving ? "Saving…" : "Complete Day 3"}
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
