"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function PlanTrackerDayRedirect() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;
  const dayNumber = params.dayNumber as string;

  useEffect(() => {
    const n = parseInt(dayNumber, 10);
    if (Number.isInteger(n) && n >= 0 && n <= 14) {
      router.replace(`/packs/${packId}/plan-tracker?day=${n}`);
    } else {
      router.replace(`/packs/${packId}/plan-tracker`);
    }
  }, [packId, dayNumber, router]);

  return (
    <div className="p-8 flex items-center justify-center">
      <p className="text-sm text-muted-foreground">Opening day…</p>
    </div>
  );
}
