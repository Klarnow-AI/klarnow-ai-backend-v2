"use client";

import { motion } from "framer-motion";
import { X } from "@/components/icons";
import {
  useOnboardingChat,
  OnboardingSlideView,
} from "@/components/onboarding-chat";

export function OnboardingModal({
  open,
  onOpenChange,
  onComplete,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: (packId: string) => void;
}) {
  const state = useOnboardingChat({
    onComplete,
    initialPackId: null,
    mvpOnly: true,
  });

  if (!open) return null;

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 p-4 pointer-events-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.2 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-modal-title"
          className="pointer-events-auto w-full max-w-[600px] rounded-2xl border border-border bg-card shadow shadow-black/10"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative p-7 sm:p-9">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="absolute right-4 top-4 p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
            <h2
              id="onboarding-modal-title"
              className="font-heading text-2xl font-bold text-foreground pr-10"
            >
              Create your first pack
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Takes about 2 minutes. You can edit later.
            </p>

            <div className="mt-6 min-h-[220px]">
              <OnboardingSlideView
                step={state.step}
                answers={state.answers}
                answerTimes={state.answerTimes}
                loading={state.loading}
                error={state.error}
                selectedPackType={state.selectedPackType}
                botMessageTimesRef={state.botMessageTimesRef}
                onChoice={state.handleChoice}
                onPathAInputType={state.handlePathAInputType}
                onPathBVibeToggle={state.handlePathBVibeToggle}
                onPackTypeChoose={state.handlePackTypeChoice}
                input={state.input}
                setInput={state.setInput}
                onSubmit={state.handleSend}
                mvpOnly={true}
              />
              <div className="mt-6">
                <OnboardingSlideView
                  step={state.step}
                  answers={state.answers}
                  answerTimes={state.answerTimes}
                  loading={state.loading}
                  error={state.error}
                  selectedPackType={state.selectedPackType}
                  botMessageTimesRef={state.botMessageTimesRef}
                  onChoice={state.handleChoice}
                  onPathAInputType={state.handlePathAInputType}
                  onPathBVibeToggle={state.handlePathBVibeToggle}
                  onPackTypeChoose={state.handlePackTypeChoice}
                  input={state.input}
                  setInput={state.setInput}
                  onSubmit={state.handleSend}
                  mvpOnly={true}
                  interactiveOnly={true}
                />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </>
  );
}
