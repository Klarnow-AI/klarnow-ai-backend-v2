"use client";

import { useEffect } from "react";
import { PWAInstallOverlay } from "@/components/pwa-install-overlay";

export function PWAProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator))
      return;
    navigator.serviceWorker
      .register("/sw.js")
      .catch(() => {
        // Registration failed - app may still work, install prompt just won't appear
      });
  }, []);

  return (
    <>
      {children}
      <PWAInstallOverlay />
    </>
  );
}
