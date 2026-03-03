"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useHasPacks } from "@/hooks/use-has-packs";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileHeaderBar } from "@/components/layout/mobile-header-bar";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { SidebarContent } from "@/components/layout/sidebar-content";
import { PageLoader } from "@/components/ui/page-loader";
import { ErrorBoundary } from "@/components/error-boundary";
import {
  MobileSidebarProvider,
  useMobileSidebar,
} from "@/contexts/mobile-sidebar-context";

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isOpen, setOpen, close } = useMobileSidebar();

  if (pathname === "/packs/new") {
    return (
      <div className="min-h-screen bg-background">
        <ErrorBoundary fallbackTitle="This page encountered an error">
          {children}
        </ErrorBoundary>
      </div>
    );
  }

  const isWebsiteBuilder = pathname?.endsWith("/website");

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      {!isWebsiteBuilder && <Sidebar />}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden min-w-0 w-full">
        <div className="lg:hidden">
          <MobileHeaderBar />
        </div>
        <main className={cn("flex-1 flex flex-col min-h-0 overflow-y-auto p-[16px] lg:p-6")}>
          <ErrorBoundary fallbackTitle="This page encountered an error">
            {children}
          </ErrorBoundary>
        </main>
      </div>
      <Sheet open={isOpen} onOpenChange={setOpen} side="left">
        <SheetContent className="bg-card">
          <SidebarContent
            variant="sheet"
            onClose={close}
            onNavigate={close}
          />
        </SheetContent>
      </Sheet>
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
      router.replace("/packs/new");
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

  return (
    <MobileSidebarProvider>
      <DashboardContent>{children}</DashboardContent>
    </MobileSidebarProvider>
  );
}
