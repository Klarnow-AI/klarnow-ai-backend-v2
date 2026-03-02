"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FolderKanban } from "@/components/icons";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PackActionsMenu } from "@/components/pack-actions-menu";
import type { Pack } from "@/types/api-types";

export type PackCardProps = {
  pack: Pack;
  index?: number;
  onActionComplete?: () => void;
};

function formatRelativeDate(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "Updated today";
    if (diffDays === 1) return "Updated yesterday";
    if (diffDays < 7) return `Updated ${diffDays} days ago`;
    return d.toLocaleDateString();
  } catch {
    return "";
  }
}

function getStatusChip(pack: Pack): { label: string; className: string } {
  if (pack.status === "archived") {
    return { label: "Archived", className: "bg-muted text-muted-foreground" };
  }
  if (pack.onboarding_completed_at) {
    return { label: "Ready", className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20" };
  }
  return { label: "Onboarding", className: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20" };
}

function getDescription(pack: Pack): string {
  if (pack.status === "archived") {
    return "Archived campaign pack. Restore from pack settings if needed.";
  }
  if (pack.onboarding_completed_at) {
    return "Brand OS and campaign ready. Open to view or edit.";
  }
  return "Complete onboarding to generate your Brand OS.";
}

export function PackCard({ pack, index = 0, onActionComplete }: PackCardProps) {
  const statusChip = getStatusChip(pack);
  const description = getDescription(pack);
  const updated = formatRelativeDate(pack.updated_at);

  return (
    <motion.li
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index }}
      className="group relative"
    >
      <Link href={`/packs/${pack.id}`} className="block h-full">
        <Card className="h-full rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md hover:border-border/80 transition-all duration-200 cursor-pointer overflow-hidden">
          <CardHeader className="p-5 pb-2">
            <div className="flex flex-col gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-border bg-background text-foreground">
                <FolderKanban className="h-5 w-5 text-muted-foreground" />
              </div>
              <CardTitle className="text-base font-semibold leading-tight tracking-tight line-clamp-2">
                {pack.name}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-5 py-0">
            <p className="text-sm text-muted-foreground font-normal leading-snug line-clamp-2">
              {description}
            </p>
            {updated && (
              <p className="text-xs text-muted-foreground/80 mt-1.5">
                {updated}
              </p>
            )}
          </CardContent>
          <CardFooter className="p-5 pt-4 flex flex-wrap gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
                statusChip.className
              )}
            >
              {statusChip.label}
            </span>
            <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-muted text-muted-foreground">
              Campaign
            </span>
          </CardFooter>
        </Card>
      </Link>
      
      {/* Actions menu - always visible on touch, hover-reveal on desktop */}
      <div
        className="absolute top-3 right-3 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity touch-manipulation"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <PackActionsMenu
          pack={pack}
          onArchive={async (id) => {
            const { packs: packsApi } = await import("@/api_requests/packs");
            await packsApi.archive(id);
            onActionComplete?.();
          }}
          onRestore={async (id) => {
            const { packs: packsApi } = await import("@/api_requests/packs");
            await packsApi.restore(id);
            onActionComplete?.();
          }}
          onDelete={async (id) => {
            const { packs: packsApi } = await import("@/api_requests/packs");
            await packsApi.delete(id);
            onActionComplete?.();
          }}
        />
      </div>
    </motion.li>
  );
}
