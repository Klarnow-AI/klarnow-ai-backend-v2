"use client";

import { useEffect } from "react";
import { useConnectivityStore } from "@/store/useConnectivityStore";
import {
  clearConnectivityIssue,
  reportConnectivityIssue,
} from "@/store/useConnectivityStore";
import { isApiBaseMisconfiguredForBrowser } from "@/lib/utils";

export function ConnectivityBanner() {
  const issue = useConnectivityStore((state) => state.issue);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    if (isApiBaseMisconfiguredForBrowser()) {
      reportConnectivityIssue("config");
    } else if (!window.navigator.onLine) {
      reportConnectivityIssue("offline");
    }

    const handleOnline = () => {
      if (!isApiBaseMisconfiguredForBrowser()) {
        clearConnectivityIssue();
      }
    };

    const handleOffline = () => {
      reportConnectivityIssue("offline");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!issue) return null;

  return (
    <div className="sticky top-0 z-[90] w-full border-b border-amber-300/70 bg-amber-50/95 px-4 py-2 text-center text-sm font-medium text-amber-950 backdrop-blur dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
      {issue.message}
    </div>
  );
}
