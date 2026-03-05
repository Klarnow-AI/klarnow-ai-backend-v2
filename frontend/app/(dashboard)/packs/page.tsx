"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { packs as packsApi } from "@/api_requests/packs";
import { PageLoader } from "@/components/ui/page-loader";

const STORAGE_KEY_LAST_PACK = "sidebar-last-pack-id";

export default function PacksResolverPage() {
  const router = useRouter();

  return (
    <>
      <PackRedirector router={router} />
      <PageLoader variant="screen" message="Loading pack..." />
    </>
  );
}

function PackRedirector({
  router,
}: {
  router: ReturnType<typeof useRouter>;
}) {
  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const res = await packsApi.list(false);
        if (cancelled) return;

        const items = res.items ?? [];
        if (items.length === 0) {
          router.replace("/packs/new", { scroll: false });
          return;
        }

        const savedPackId =
          typeof window !== "undefined"
            ? localStorage.getItem(STORAGE_KEY_LAST_PACK)
            : null;
        const validSavedPackId =
          savedPackId && items.some((item) => item.id === savedPackId)
            ? savedPackId
            : null;
        const targetPackId = validSavedPackId ?? items[0]?.id ?? null;

        if (!targetPackId) {
          router.replace("/packs/new", { scroll: false });
          return;
        }

        try {
          localStorage.setItem(STORAGE_KEY_LAST_PACK, targetPackId);
        } catch {}

        router.replace(`/packs/${targetPackId}`, { scroll: false });
      } catch {
        if (!cancelled) {
          router.replace("/", { scroll: false });
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return null;
}
