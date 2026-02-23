"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function PackInvoiceRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const packId = params.packId as string;

  useEffect(() => {
    if (packId) {
      router.replace(`/invoices?pack=${packId}`);
    }
  }, [packId, router]);

  return null;
}
