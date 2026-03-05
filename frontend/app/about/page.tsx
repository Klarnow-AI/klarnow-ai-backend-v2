"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthModal } from "@/components/auth-modal";
import { PublicHeader } from "@/components/public-header";
import ExplainerSection from "@/components/about/explainer-section";
import CreateSection from "@/components/about/create-section";
import HowItWorksSection from "@/components/about/how-it-works-section";
import FooterCTA from "@/components/about/footer-cta";
import { useAuth } from "@/contexts/auth-context";

export default function AboutPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);

  function handleGetStarted() {
    if (isAuthenticated) {
      router.push("/packs");
      return;
    }
    setAuthModalOpen(true);
  }

  return (
    <div className="relative min-h-screen flex flex-col text-foreground overflow-hidden bg-background">
      <AuthModal
        open={authModalOpen}
        onOpenChange={setAuthModalOpen}
        onRegisterSuccess={() => {
          setAuthModalOpen(false);
          router.push("/packs");
        }}
      />

      <PublicHeader
        onDashboardClick={() => router.push("/packs")}
        onAuthClick={() => setAuthModalOpen(true)}
        showInstallAbout
      />

      <main className="relative z-10">
        <ExplainerSection onGetStarted={handleGetStarted} />
        <CreateSection />
        <HowItWorksSection />
        <FooterCTA onGetStarted={handleGetStarted} />
      </main>
    </div>
  );
}
