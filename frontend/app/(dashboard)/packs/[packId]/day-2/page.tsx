"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { buildChatUrlWithDay } from "@/app/(dashboard)/chat/helpers";

export default function Day2Redirect() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    router.replace(buildChatUrlWithDay(packId, 2));
  }, [packId, router]);

  return (
    <div className="p-8 flex items-center justify-center">
      <p className="text-sm text-muted-foreground">Opening Day 2…</p>
    </div>
  );
}
