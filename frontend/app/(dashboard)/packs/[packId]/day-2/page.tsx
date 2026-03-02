"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Day2Redirect() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    router.replace(`/packs/${packId}/plan-tracker?day=2`);
  }, [packId, router]);

  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <p className="text-sm text-muted-foreground">Opening Day 2…</p>
    </div>
  );
}
