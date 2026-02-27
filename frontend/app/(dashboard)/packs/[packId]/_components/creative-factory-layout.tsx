"use client";

import { useCallback, useEffect } from "react";
import { CreativeTemplateGrid } from "./creative-template-grid";
import { CreativeInputBar } from "./creative-input-bar";
import { CreativePreviewModal } from "./creative-preview-modal";
import { MobileNavContent } from "@/components/layout/mobile-nav-content";
import { useMobileInputNav } from "@/contexts/mobile-input-nav-context";
import { useMediaQuery } from "@/hooks/use-media-query";
import { LayoutDashboard, X } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import type { CreativeTemplateCardAsset } from "./creative-template-card";
import type { PromptWithResults } from "./creative-template-grid";
import type { BrandContext } from "@/app/api/generate/route";

export type CreativeFactoryLayoutProps = {
  variant: "posters";
  packId: string;
  brandContext?: BrandContext | null;
  promptGroups: PromptWithResults[];
  generatingPrompt: string | null;
  isGenerating: boolean;
  selectedAsset: CreativeTemplateCardAsset | null;
  onAssetSelect: (asset: CreativeTemplateCardAsset | null) => void;
  onFilesGenerated: (
    files: Record<string, string>,
    messages: { role: "user" | "assistant"; content: string }[],
  ) => void;
  onGeneratingChange: (generating: boolean, prompt?: string | null) => void;
  onDeleteAsset?: (assetId: string) => void | Promise<void>;
};

export function CreativeFactoryLayout({
  variant,
  packId,
  brandContext,
  promptGroups,
  generatingPrompt,
  isGenerating,
  selectedAsset,
  onAssetSelect,
  onFilesGenerated,
  onGeneratingChange,
  onDeleteAsset,
}: CreativeFactoryLayoutProps) {
  const bottomPlaceholder = "Type to Generate";
  const isMobile = !useMediaQuery("(min-width: 1024px)");
  const { showNavInsteadOfInput, setShowNavInsteadOfInput } =
    useMobileInputNav();

  const handleGenerate = useCallback(
    (
      files: Record<string, string>,
      _messages: { role: "user" | "assistant"; content: string }[],
    ) => {
      onFilesGenerated(files, _messages);
    },
    [onFilesGenerated],
  );

  return (
    <div className="flex flex-col flex-1 min-h-0 min-w-0">
      {/* Main timeline */}
      <div className="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
        <CreativeTemplateGrid
          packId={packId}
          promptGroups={promptGroups}
          generatingPrompt={generatingPrompt}
          isGenerating={isGenerating}
          variant={variant}
          onAssetClick={(asset) => onAssetSelect(asset)}
        />
      </div>

      {/* Bottom bar */}
      <div className="shrink-0 px-4 py-4 min-w-0">
        <div className="w-full min-w-0 max-w-2xl mx-auto flex items-center gap-2">
          {isMobile ? (
            <>
              {showNavInsteadOfInput ? (
                <div className="flex-1 min-w-0 min-h-[4.5rem] flex items-center">
                  <MobileNavContent inline className="h-[4.5rem]" />
                </div>
              ) : (
                <div className="flex-1 min-w-0 min-h-[4.5rem] flex items-center">
                  <CreativeInputBar
                    apiRoute="/api/generate-poster"
                    brandContext={brandContext}
                    placeholder={bottomPlaceholder}
                    onGenerate={handleGenerate}
                    onGeneratingChange={onGeneratingChange}
                    disabled={isGenerating}
                  />
                </div>
              )}
              <div className="shrink-0">
                {showNavInsteadOfInput ? (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="Back to input"
                    onClick={() => setShowNavInsteadOfInput(false)}
                  >
                    <X className="h-5 w-5" />
                  </IconButton>
                ) : (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="Show navigation"
                    onClick={() => setShowNavInsteadOfInput(true)}
                  >
                    <LayoutDashboard className="h-5 w-5" />
                  </IconButton>
                )}
              </div>
            </>
          ) : (
            <CreativeInputBar
              apiRoute="/api/generate-poster"
              brandContext={brandContext}
              placeholder={bottomPlaceholder}
              onGenerate={handleGenerate}
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
