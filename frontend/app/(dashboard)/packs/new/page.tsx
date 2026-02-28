"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  useOnboardingChat,
  OnboardingSharedStepLayout,
} from "@/components/onboarding-chat";
import { dispatchPacksUpdated } from "@/contexts/new-pack-modal-context";
import { PublicHeader } from "@/components/public-header";
import { AuthModal } from "@/components/auth-modal";

export default function NewPackPage() {
  const router = useRouter();
  const [authModalOpen, setAuthModalOpen] = useState(false);

  function handleComplete(packId: string) {
    dispatchPacksUpdated();
    router.push(`/chat?pack=${packId}`);
  }

  const state = useOnboardingChat({
    onComplete: handleComplete,
    initialPackId: null,
    mvpOnly: true,
  });

  return (
    <div className="min-h-screen flex flex-col">
      <PublicHeader
        onDashboardClick={() => router.push("/packs")}
        onAuthClick={() => setAuthModalOpen(true)}
      />
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={() => {
          setAuthModalOpen(false);
          router.push("/packs/new");
        }}
      />
      <main className="flex-1 flex flex-col items-center justify-center">
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
          mvpOnly
          onboardingProgress={state.onboardingProgress}
          retryFailedStep={state.retryFailedStep}
        />
      </main>
    </div>
  );
}
