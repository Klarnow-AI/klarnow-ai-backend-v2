"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function PackInvoiceRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    if (packId) {
      router.replace(`/packs/${packId}/docs?type=invoice`);
    }
  }, [packId, router]);

  return null;
}
