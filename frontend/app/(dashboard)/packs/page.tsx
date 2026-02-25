"use client";

import { useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Plus } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { packs as packsApi } from "@/api_requests/packs";
import { Button } from "@/components/ui/button";
import { useGet } from "@/hooks/use-get";

import { PacksEmptyState, PackCard } from "./_components";

export default function PacksPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      router.replace("/packs/new", { scroll: false });
    }
  }, [searchParams, router]);

  const fetcher = useCallback(() => packsApi.list(false), []);
  const { data, isLoading: loading, error, refetch } = useGet("packs-list", fetcher);
  const packs = data?.items ?? [];

  return (
    <div className="p-8 max-w-8xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaign Packs</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage your campaign packs. Start with onboarding, then
            strategy and creative.
          </p>
        </div>
        <Button
          className="gap-2"
          onClick={() => router.push("/packs/new")}
        >
          <Plus className="h-4 w-4" />
          Start new Campaign Pack
        </Button>
      </motion.div>

      {error && (
        <div className="mb-6 rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive flex items-center justify-between">
          <span>{error.message}</span>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center max-w-8xl mx-auto justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : packs.length === 0 ? (
        <PacksEmptyState onCreate={() => router.push("/packs/new")} />
      ) : (
        <ul className="grid gap-5 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {packs.map((pack, i) => (
            <PackCard 
              key={pack.id} 
              pack={pack} 
              index={i}
              onActionComplete={refetch}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
