"use client";

import { useEffect, useState } from "react";
import { sprintApi } from "@/api_requests/sprint";
import {
  CreativeTemplateCard,
  type CreativeTemplateCardAsset,
} from "./creative-template-card";
import { Image, Lock } from "@/components/icons";

export type PromptWithResults = {
  prompt: string;
  results: CreativeTemplateCardAsset[];
  createdAt: string;
};

type CreativeTemplateGridProps = {
  packId: string;
  promptGroups: PromptWithResults[];
  generatingPrompt: string | null;
  isGenerating?: boolean;
  variant: "posters";
  onAssetClick: (asset: CreativeTemplateCardAsset) => void;
};

export function CreativeTemplateGrid({
  packId,
  promptGroups,
  generatingPrompt,
  isGenerating = false,
  variant,
  onAssetClick,
}: CreativeTemplateGridProps) {
  const [sprint, setSprint] = useState<{
    current_day: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  const hasCompletedDay0To3 = (sprint?.current_day ?? 0) >= 4;
  const hasContent = promptGroups.length > 0 || isGenerating;

  useEffect(() => {
    if (!packId) return;
    sprintApi
      .getSprint(packId)
      .then((s) => setSprint(s ? { current_day: s.current_day } : null))
      .catch(() => setSprint(null))
      .finally(() => setLoading(false));
  }, [packId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
      </div>
    );
  }

  if (!hasCompletedDay0To3) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-4">
          <Lock className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground mb-1">
          Complete Step 0–3 to unlock starter templates
        </p>
        <p className="max-w-sm text-sm text-muted-foreground leading-relaxed">
          Finish your sprint setup (Steps 0–3) to access and create{" "}
          posters and flyers.
        </p>
      </div>
    );
  }

  if (!hasContent) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-4">
          <Image className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground mb-1">
          No posters yet
        </p>
        <p className="max-w-sm text-sm text-muted-foreground leading-relaxed">
          Type a prompt in the bar below to create your first{" "}
          poster or flyer.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 p-4 min-w-0 w-full">
      {promptGroups.map((group) => (
        <div key={group.createdAt + group.prompt} className="space-y-4 min-w-0">
          <div className="flex justify-end">
            <div
              className="inline-flex max-w-[85%] rounded-2xl rounded-tr-md px-4 py-3 bg-primary text-primary-foreground"
              style={{ width: "fit-content" }}
            >
              <p className="text-sm whitespace-pre-wrap">{group.prompt}</p>
            </div>
          </div>
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] gap-4">
            {group.results.map((asset, i) => (
              <div key={asset.id ?? `${asset.name}-${i}`} className="min-w-0">
                <CreativeTemplateCard
                  asset={asset}
                  onClick={() => onAssetClick(asset)}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
      {isGenerating && generatingPrompt && (
        <div className="space-y-4 min-w-0">
          <div className="flex justify-end">
            <div
              className="inline-flex max-w-[85%] rounded-2xl rounded-tr-md px-4 py-3 bg-primary text-primary-foreground"
              style={{ width: "fit-content" }}
            >
              <p className="text-sm whitespace-pre-wrap">{generatingPrompt}</p>
            </div>
          </div>
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] gap-4">
            <div className="min-w-0">
              <div className="flex aspect-[4/5] items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 min-w-0">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
                  <p className="text-xs text-muted-foreground">Generating…</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
