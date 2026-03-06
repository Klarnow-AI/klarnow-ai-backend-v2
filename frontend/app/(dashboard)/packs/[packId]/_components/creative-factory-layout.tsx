"use client";

import { useCallback } from "react";
import { CreativeTemplateGrid } from "./creative-template-grid";
import { CreativeInputBar } from "./creative-input-bar";
import { CreativePreviewModal } from "./creative-preview-modal";
import { useMediaQuery } from "@/hooks/use-media-query";
import type { CreativeTemplateCardAsset } from "./creative-template-card";
import type {
  CreativeGenerationDisplay,
  PromptWithResults,
} from "./creative-template-grid";
import type { BrandContext } from "@/app/api/generate/route";
import type { PosterConversationMessage } from "@/lib/poster-output";

export type CreativeFactoryLayoutProps = {
  variant: "posters";
  packId: string;
  sprintDay: number | null;
  brandContext?: BrandContext | null;
  promptGroups: PromptWithResults[];
  generationDisplay: CreativeGenerationDisplay | null;
  generationProgress?: {
    completedCount: number;
    totalCount: number;
  } | null;
  isGenerating: boolean;
  selectedAsset: CreativeTemplateCardAsset | null;
  onAssetSelect: (asset: CreativeTemplateCardAsset | null) => void;
  onFileGenerated: (
    name: string,
    code: string,
    messages: PosterConversationMessage[],
  ) => void | Promise<void>;
  onGeneratingChange: (
    generating: boolean,
    display?: CreativeGenerationDisplay | null,
  ) => void;
  onDeleteAsset?: (assetId: string) => void | Promise<void>;
};

export function CreativeFactoryLayout({
  variant,
  packId,
  sprintDay,
  brandContext,
  promptGroups,
  generationDisplay,
  generationProgress = null,
  isGenerating,
  selectedAsset,
  onAssetSelect,
  onFileGenerated,
  onGeneratingChange,
  onDeleteAsset,
}: CreativeFactoryLayoutProps) {
  const bottomPlaceholder = "Type to Generate";
  const isMobile = !useMediaQuery("(min-width: 1024px)");

  const handleGenerate = useCallback(
    (name: string, code: string, messages: PosterConversationMessage[]) => {
      onFileGenerated(name, code, messages);
    },
    [onFileGenerated],
  );

  return (
    <div className="flex flex-col flex-1 min-h-0 min-w-0">
      {/* Main timeline */}
      <div className="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
        <CreativeTemplateGrid
          sprintDay={sprintDay}
          promptGroups={promptGroups}
          generationDisplay={generationDisplay}
          isGenerating={isGenerating}
          generationProgress={generationProgress}
          variant={variant}
          onAssetClick={(asset) => onAssetSelect(asset)}
        />
      </div>

      {/* Bottom bar */}
      <div className="shrink-0 px-4 py-4 min-w-0">
        <div className="w-full min-w-0 max-w-2xl mx-auto flex items-center gap-2">
          {isMobile ? (
            <>
              <div className="flex-1 min-w-0 min-h-[4.5rem] flex items-center">
                <CreativeInputBar
                  apiRoute="/api/generate-poster"
                  packId={packId}
                  brandContext={brandContext}
                  placeholder={bottomPlaceholder}
                  onFileGenerated={handleGenerate}
                  onGeneratingChange={onGeneratingChange}
                  disabled={isGenerating}
                />
              </div>
            </>
          ) : (
            <CreativeInputBar
              apiRoute="/api/generate-poster"
              packId={packId}
              brandContext={brandContext}
              placeholder={bottomPlaceholder}
              onFileGenerated={handleGenerate}
              onGeneratingChange={onGeneratingChange}
              disabled={isGenerating}
            />
          )}
        </div>
      </div>

      {/* Preview modal */}
      <CreativePreviewModal
        open={selectedAsset !== null}
        onOpenChange={(open) => !open && onAssetSelect(null)}
        asset={selectedAsset}
        variant={variant}
        onDelete={onDeleteAsset}
      />
    </div>
  );
}
