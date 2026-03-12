"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { packs as packsApi } from "@/api_requests/packs";

export default function ProposalsRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const pack = searchParams.get("pack");
    if (pack) {
      router.replace(`/packs/${pack}/docs?type=proposal`);
      return;
    }

    packsApi
      .list()
      .then((response) => {
        const firstPack = response.items[0];
        router.replace(firstPack ? `/packs/${firstPack.id}/docs?type=proposal` : "/packs");
      })
      .catch(() => router.replace("/packs"));
  }, [router, searchParams]);

  return null;
}
