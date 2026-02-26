"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/page-loader";

interface CoreConceptLockModalProps {
  open: boolean;
  packId: string | null;
  initialCoreConcept: string | null;
  onConfirm: (coreConcept: string) => Promise<void>;
  loading?: boolean;
}

const PLACEHOLDER = "Summarise your offer in one sentence.";

export function CoreConceptLockModal({
  open,
  packId,
  initialCoreConcept,
  onConfirm,
  loading = false,
}: CoreConceptLockModalProps) {
  const [value, setValue] = useState(initialCoreConcept ?? "");

  useEffect(() => {
    if (open) {
      setValue(initialCoreConcept?.trim() ?? "");
    }
  }, [open, initialCoreConcept]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) {
      onConfirm(trimmed);
    } else {
      onConfirm(PLACEHOLDER);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        key="core-concept-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm"
        aria-hidden
      />

      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 pointer-events-none">
        <motion.div
          key="core-concept-modal"
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="core-concept-title"
          className="pointer-events-auto w-full max-w-lg rounded-2xl bg-background border border-border shadow-2xl"
        >
          <form onSubmit={handleSubmit} className="p-8 space-y-6">
            <h2
              id="core-concept-title"
              className="text-xl font-semibold text-foreground"
            >
              One sentence that everything will follow.
            </h2>
            <p className="text-sm text-muted-foreground">
              Confirm or edit your core concept. This will guide your Brand OS
              and assets.
            </p>
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={PLACEHOLDER}
              rows={3}
              className="w-full px-4 py-3 rounded-xl border border-border bg-background text-foreground placeholder:text-muted-foreground transition-all focus:outline-none focus:scale-[1.02] resize-none"
              disabled={loading}
              aria-label="Core concept"
            />
            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={loading || !value.trim()}
            >
              {loading ? (
                <>
                  <Spinner className="h-4 w-4 mr-2" />
                  Saving…
                </>
              ) : (
                "Confirm and continue"
              )}
            </Button>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
