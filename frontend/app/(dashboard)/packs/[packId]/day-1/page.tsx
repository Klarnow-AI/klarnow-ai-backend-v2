"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { buildChatUrlWithDay } from "@/app/(dashboard)/chat/helpers";

export default function Day1Redirect() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    router.replace(buildChatUrlWithDay(packId, 1));
  }, [packId, router]);

  return (
    <div className="p-8 flex items-center justify-center">
      <p className="text-sm text-muted-foreground">Opening Day 1…</p>
    </div>
  );
}
