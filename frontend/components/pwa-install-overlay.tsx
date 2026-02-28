"use client";

import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useIsMobile } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const standaloneMedia = window.matchMedia("(display-mode: standalone)");
  const iosStandalone = (navigator as Navigator & { standalone?: boolean })
    .standalone;
  return standaloneMedia.matches || iosStandalone === true;
}

function isIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

export function PWAInstallOverlay() {
  const isMobile = useIsMobile();
  const [mounted, setMounted] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [installPromptEvent, setInstallPromptEvent] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const isDevEnvironment =
    process.env.NODE_ENV !== "production" ||
    process.env.NEXT_PUBLIC_ENVIRONMENT === "development";

  const handleInstall = useCallback(async () => {
    if (installPromptEvent) {
      installPromptEvent.prompt();
      const { outcome } = await installPromptEvent.userChoice;
      if (outcome === "accepted") {
        setInstalled(true);
        setShowOverlay(false);
      }
      setInstallPromptEvent(null);
    }
  }, [installPromptEvent]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || typeof window === "undefined") return;
    if (isDevEnvironment) return;

    const check = () => {
      if (!isMobile) return;
      if (isStandalone()) return;
      setShowOverlay(true);
    };

    const handleBeforeInstallPrompt = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      setInstallPromptEvent(e);
    };

    const handleAppInstalled = () => {
      setInstalled(true);
      setShowOverlay(false);
    };

    check();

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, [mounted, isMobile, isDevEnvironment]);

  if (
    !mounted ||
    !showOverlay ||
    isDevEnvironment
  )
    return null;

  const hasInstallPrompt = !!installPromptEvent;
  const ios = isIOS();

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/95 dark:bg-black/95 backdrop-blur-sm p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pwa-install-title"
    >
      <div className="flex max-w-sm flex-col items-center gap-6 text-center">
        <h2
          id="pwa-install-title"
          className="text-xl font-semibold text-foreground"
        >
          Install Klarnow AI
        </h2>
        <p className="text-sm text-muted-foreground">
          {ios
            ? "Add this app to your home screen for quick access and a better experience."
            : "Install the app for quick access and a better experience on your device."}
        </p>

        <div className="flex w-full flex-col gap-3">
          {ios ? (
            <div className="rounded-lg border border-border bg-muted/50 p-4 text-left text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-2">
                To add to home screen:
              </p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Tap the Share button (square with arrow)</li>
                <li>Scroll and tap &quot;Add to Home Screen&quot;</li>
                <li>Tap &quot;Add&quot;</li>
              </ol>
            </div>
          ) : (
            <Button
              onClick={handleInstall}
              disabled={!hasInstallPrompt}
              className={cn(!hasInstallPrompt && "opacity-70")}
            >
              {hasInstallPrompt ? "Install app" : "Install when available"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
