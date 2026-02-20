"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageLoader } from "@/components/ui/page-loader";

/** Onboarding runs in the modal on the landing page. Redirect there. */
export default function OnboardingPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return <PageLoader variant="screen" />;
}
