"use client";

import { useParams, useRouter } from "next/navigation";
import {
  useOnboardingChat,
  OnboardingSharedStepLayout,
} from "@/components/onboarding-chat";

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
    <div className="w-full max-w-2xl mx-auto min-h-[80vh] flex flex-col justify-center px-4">
      <OnboardingSharedStepLayout
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
        onboardingProgress={state.onboardingProgress}
        retryFailedStep={state.retryFailedStep}
      />
    </div>
  );
}
