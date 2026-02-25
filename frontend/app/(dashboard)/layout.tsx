"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useHasPacks } from "@/hooks/use-has-packs";
import { Sidebar } from "@/components/layout/sidebar";
import { PageLoader } from "@/components/ui/page-loader";
import { ErrorBoundary } from "@/components/error-boundary";

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (pathname === "/packs/new") {
    return (
      <div className="min-h-screen bg-background">
        <ErrorBoundary fallbackTitle="This page encountered an error">
          {children}
        </ErrorBoundary>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ErrorBoundary fallbackTitle="This page encountered an error">
          {children}
        </ErrorBoundary>
      </main>
    </div>
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
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/");
      return;
    }
    if (!packsLoading && !hasPacks && pathname !== "/packs/new") {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, hasPacks, packsLoading, pathname, router]);

  if (isLoading) {
    return <PageLoader variant="screen" />;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (packsLoading) {
    return <PageLoader variant="screen" />;
  }

  if (!hasPacks && pathname !== "/packs/new") {
    return null;
  }

  return <DashboardContent>{children}</DashboardContent>;
}
