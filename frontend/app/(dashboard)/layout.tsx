"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useHasPacks } from "@/hooks/use-has-packs";
import { NewPackModalProvider, useNewPackModal, dispatchPacksUpdated } from "@/contexts/new-pack-modal-context";
import { Sidebar } from "@/components/layout/sidebar";
import { OnboardingModal } from "@/components/onboarding-modal";
import { PageLoader } from "@/components/ui/page-loader";
import { ErrorBoundary } from "@/components/error-boundary";

function DashboardContent({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { open, closeNewPackModal } = useNewPackModal();

  function handleNewPackComplete(packId: string) {
    closeNewPackModal();
    dispatchPacksUpdated();
    router.push(`/packs/${packId}`);
  }

  return (
    <>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <ErrorBoundary fallbackTitle="This page encountered an error">
            {children}
          </ErrorBoundary>
        </main>
      </div>
      <OnboardingModal
        open={open}
        onOpenChange={(isOpen) => !isOpen && closeNewPackModal()}
        onComplete={handleNewPackComplete}
      />
    </>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const { hasPacks, isLoading: packsLoading } = useHasPacks();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/");
      return;
    }
    if (!packsLoading && !hasPacks) {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, hasPacks, packsLoading, router]);

  if (isLoading) {
    return <PageLoader variant="screen" />;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (packsLoading) {
    return <PageLoader variant="screen" />;
  }

  if (!hasPacks) {
    return null;
  }

  return (
    <NewPackModalProvider>
      <DashboardContent>{children}</DashboardContent>
    </NewPackModalProvider>
  );
}
