"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Day3Redirect() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    router.replace(`/packs/${packId}?step=3`);
  }, [packId, router]);

  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <p className="text-sm text-muted-foreground">Opening Step 3…</p>
    </div>
  );
}
