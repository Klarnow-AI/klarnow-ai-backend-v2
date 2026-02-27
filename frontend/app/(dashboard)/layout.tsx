"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useHasPacks } from "@/hooks/use-has-packs";
import { MobileInputNavProvider } from "@/contexts/mobile-input-nav-context";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileHeaderBar } from "@/components/layout/mobile-header-bar";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { SidebarContent } from "@/components/layout/sidebar-content";
import { PageLoader } from "@/components/ui/page-loader";
import { ErrorBoundary } from "@/components/error-boundary";

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sheetOpen, setSheetOpen] = useState(false);

  if (pathname === "/packs/new") {
    return (
      <div className="min-h-screen bg-background">
        <ErrorBoundary fallbackTitle="This page encountered an error">
          {children}
        </ErrorBoundary>
      </div>
    );
  }

  const hideMobileNav =
    pathname?.endsWith("/posters") || pathname?.endsWith("/ad-factory");

  return (
    <MobileInputNavProvider>
      <div className="flex h-dvh overflow-hidden bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden min-w-0 w-full">
          <div className="lg:hidden">
            <MobileHeaderBar />
          </div>
          <main
            className={cn(
              "flex-1 flex flex-col min-h-0 overflow-hidden p-[16px] lg:p-6",
              !hideMobileNav &&
                "pb-[calc(5.5rem+env(safe-area-inset-bottom,0px))]",
            )}
          >
            <ErrorBoundary fallbackTitle="This page encountered an error">
              {children}
            </ErrorBoundary>
          </main>
          {!hideMobileNav && (
            <div className="lg:hidden">
              <MobileBottomNav />
            </div>
          )}
        </div>
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen} side="left">
          <SheetContent className="bg-card">
            <SidebarContent
              variant="sheet"
              onClose={() => setSheetOpen(false)}
              onNavigate={() => setSheetOpen(false)}
            />
          </SheetContent>
        </Sheet>
      </div>
    </MobileInputNavProvider>
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
