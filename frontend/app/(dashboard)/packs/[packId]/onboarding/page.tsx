"use client";

import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  useOnboardingChat,
  OnboardingSlideView,
} from "@/components/onboarding-chat";
import { CoreConceptLockModal } from "@/components/core-concept-lock-modal";

export default function OnboardingPage() {
  const params = useParams();
  const packId = params.packId as string;
  const router = useRouter();
  const state = useOnboardingChat({
    initialPackId: packId,
    onComplete: (id) => {
      router.push(`/packs/${id}`);
      router.refresh();
    },
  });

  return (
    <div className="p-8 max-w-2xl mx-auto min-h-[80vh] flex flex-col justify-center">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold tracking-tight">Set up your pack</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Answer a few questions so Klaro can set up your Brand Identity and
          pack.
        </p>
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="rounded-2xl border border-border bg-card shadow shadow-black/10 p-7 sm:p-9"
      >
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
          interactiveOnly
        />
      </motion.div>

      <CoreConceptLockModal
        open={state.showCoreConceptModal}
        packId={state.completedPack?.id ?? null}
        initialCoreConcept={state.completedPack?.core_concept ?? null}
        onConfirm={state.handleCoreConceptConfirm}
        loading={state.loading}
      />
    </div>
  );
}
