"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { PWAInstallOverlay } from "@/components/pwa-install-overlay";

export function PWAProvider({ children }: { children: React.ReactNode }) {
  const updateToastShownRef = useRef(false);
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    const isDevEnvironment =
      process.env.NODE_ENV !== "production" ||
      process.env.NEXT_PUBLIC_ENVIRONMENT === "development";
    if (typeof window === "undefined" || !("serviceWorker" in navigator))
      return;
    if (isDevEnvironment) return;

    const onControllerChange = () => {
      if (updateToastShownRef.current) return;
      updateToastShownRef.current = true;
      toast("New version available", {
        action: {
          label: "Refresh",
          onClick: () => window.location.reload(),
        },
        duration: Infinity,
      });
    };

    const onFocus = () => {
      registrationRef.current?.update();
    };

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
    window.addEventListener("focus", onFocus);

    navigator.serviceWorker.register("/sw.js").then(
      (reg) => {
        registrationRef.current = reg;
      },
      () => {
        // Registration failed - app may still work, install prompt just won't appear
      },
    );

    return () => {
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        onControllerChange,
      );
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  return (
    <>
      {children}
      <PWAInstallOverlay />
    </>
  );
}
