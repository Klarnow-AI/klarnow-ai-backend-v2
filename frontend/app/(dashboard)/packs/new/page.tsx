"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function NewPackPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/packs?new=1");
  }, [router]);

  return null;
}
