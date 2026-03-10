"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { packs as packsApi, creative as creativeApi } from "@/lib/api";
import { brandOs as brandOsApi } from "@/api_requests/brand-os";
import { sprintApi } from "@/api_requests/sprint";
import { streamPosterGeneration } from "@/lib/generate-poster";
import {
  extractPosterTemplateIdFromFilename,
  type PosterConversationMessage,
} from "@/lib/poster-output";
import { usePackRefreshListener } from "@/lib/pack-refresh-events";
import { CreativeFactoryLayout } from "../_components/creative-factory-layout";
import type { CreativeTemplateCardAsset } from "../_components/creative-template-card";
import type {
  CreativeGenerationDisplay,
  PromptWithResults,
} from "../_components/creative-template-grid";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import type { Pack, BrandOS } from "@/types/api-types";
import type { BrandContext } from "@/types/generation";

const AUTO_GENERATION_LABEL = "Starter poster pack";
const GENERATION_FILE_TOTAL = 16;

function buildBrandContext(pack: Pack, brand: BrandOS | null): BrandContext {
  const onboarding = pack.onboarding_answers as
    | Record<string, string>
    | undefined;

  let palette: { primary?: string; secondary?: string; accent?: string } = {};
  if (typeof onboarding?.palette === "string") {
    try {
      palette = JSON.parse(onboarding.palette);
    } catch {}
  }

  let fonts: string[] = [];
  if (typeof onboarding?.fonts === "string") {
    try {
      const parsed = JSON.parse(onboarding.fonts);
      fonts = Array.isArray(parsed) ? parsed : [];
    } catch {}
  }

  let logoUrl: string | undefined;
  const rawLogo =
    onboarding?.wordmark_svg_or_url ?? onboarding?.wordmark_result;
  if (
    rawLogo &&
    typeof rawLogo === "string" &&
    !rawLogo.trimStart().startsWith("<")
  ) {
    logoUrl = rawLogo;
  }

  const bs = brand?.brand_strategy;
  const foundation = brand?.foundation;

  return {
    brandName: pack.brand_name ?? foundation?.brand_name ?? undefined,
    industry: foundation?.brand_industry ?? undefined,
    coreOffer: pack.offer_one_liner ?? foundation?.one_line_offer ?? undefined,
    primaryCta: pack.primary_cta ?? undefined,
    primaryPain: pack.primary_pain ?? undefined,
    primaryOutcome: pack.primary_outcome ?? undefined,
    heroAngle: pack.hero_angle ?? undefined,
    uspStatement: pack.usp_statement ?? undefined,
    uspProof: pack.usp_proof ?? undefined,
    logoUrl,
    colorPalette:
      palette.primary || palette.secondary || palette.accent
        ? palette
        : undefined,
    fonts: fonts.length > 0 ? fonts : undefined,
    mission: bs?.mission_vision?.mission ?? undefined,
    vision: bs?.mission_vision?.vision ?? undefined,
    elevatorPitch: bs?.core_messaging_hierarchy?.elevator_pitch ?? undefined,
    proofPoints: bs?.core_messaging_hierarchy?.proof_points?.length
      ? bs.core_messaging_hierarchy.proof_points
      : undefined,
    audiencePersonas: bs?.audience_personas?.length
      ? bs.audience_personas.map((p) => ({
          persona: p.persona,
          needs: p.needs,
          painPoints: p.pain_points,
        }))
      : undefined,
    voiceArchetype: bs?.voice_personality?.archetype ?? undefined,
    designCues: bs?.style_direction_seeds?.design_cues?.length
      ? bs.style_direction_seeds.design_cues
      : undefined,
  };
}

type AssetWithMeta = CreativeTemplateCardAsset & {
  created_at: string;
  chat_messages?: PosterConversationMessage[] | null;
};

function buildPromptDisplay(prompt: string): CreativeGenerationDisplay {
  return {
    kind: "prompt",
    label: prompt,
    displayKey: `prompt:${prompt}`,
  };
}

function formatModeLabel(mode?: string | null): string | null {
  if (!mode) return null;
  const normalized = mode.trim().toLowerCase();
  if (!normalized) return null;
  return `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)} mode`;
}

function buildBackgroundTaskDisplay(
  label: string,
  mode?: string | null,
  taskLabel = "Background task",
): CreativeGenerationDisplay {
  const modeLabel = formatModeLabel(mode);
  return {
    kind: "background_task",
    label,
    taskLabel,
    modeLabel,
    displayKey: `background:${taskLabel}:${modeLabel ?? ""}:${label}`,
  };
}

function buildAutoGenerationDisplay(mode?: string | null): CreativeGenerationDisplay {
  return buildBackgroundTaskDisplay(AUTO_GENERATION_LABEL, mode);
}

function buildAutoGenerationMessages(
  mode?: string | null,
): PosterConversationMessage[] {
  const display = buildAutoGenerationDisplay(mode);
  return [
    {
      role: "assistant",
      content: "Starter poster pack generated automatically.",
      meta: {
        kind: "background_generation",
        label: display.label,
        taskLabel: display.taskLabel ?? undefined,
        mode: mode ?? undefined,
        modeLabel: display.modeLabel ?? undefined,
      },
    },
  ];
}

function getAssetDisplay(asset: AssetWithMeta): CreativeGenerationDisplay {
  const msgs = asset.chat_messages;
  if (!msgs || !Array.isArray(msgs)) return buildPromptDisplay("Your creation");

  const backgroundMessage = msgs.find(
    (message) => message.meta?.kind === "background_generation",
  );
  if (backgroundMessage) {
    return buildBackgroundTaskDisplay(
      backgroundMessage.meta?.label || backgroundMessage.content || AUTO_GENERATION_LABEL,
      backgroundMessage.meta?.mode,
      backgroundMessage.meta?.taskLabel || "Background task",
    );
  }

  const userMsg = msgs.find(
    (message) => message.role === "user" && message.content.trim().length > 0,
  );
  return buildPromptDisplay(userMsg?.content.trim() || "Your creation");
}

function groupAssetsByPrompt(assets: AssetWithMeta[]): PromptWithResults[] {
  const sorted = [...assets].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  const groups: PromptWithResults[] = [];
  let current: {
    display: CreativeGenerationDisplay;
    results: CreativeTemplateCardAsset[];
    createdAt: string;
  } | null = null;

  for (const asset of sorted) {
    const display = getAssetDisplay(asset);
    const card: CreativeTemplateCardAsset = {
      id: asset.id,
      name: asset.name,
      code: asset.code,
    };
    if (current && current.display.displayKey === display.displayKey) {
      current.results.push(card);
    } else {
      current = { display, results: [card], createdAt: asset.created_at };
      groups.push(current);
    }
  }
  return groups;
}

function toAssetsWithMeta(
  items: {
    id: string;
    type: string;
    name: string | null;
    source_code: string | null;
    created_at: string;
    chat_messages?: PosterConversationMessage[] | null;
  }[],
): AssetWithMeta[] {
  return items
    .filter((a) => (a.type === "poster" || a.type === "flyer") && a.source_code)
    .map((a) => ({
      id: a.id,
      name: a.name ?? `/${a.type}_${a.id}.tsx`,
      code: a.source_code!,
      created_at: a.created_at,
      chat_messages: a.chat_messages ?? null,
    }));
}

export default function PostersPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [brandContext, setBrandContext] = useState<BrandContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assets, setAssets] = useState<AssetWithMeta[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationDisplay, setGenerationDisplay] =
    useState<CreativeGenerationDisplay | null>(null);
  const [generationProgress, setGenerationProgress] = useState<{
    completedCount: number;
    totalCount: number;
  } | null>(null);
  const [selectedAsset, setSelectedAsset] =
    useState<CreativeTemplateCardAsset | null>(null);
  const [sprintDay, setSprintDay] = useState<number | null>(null);
  const [sprintMode, setSprintMode] = useState<string | null>(null);
  const autoGeneratedRef = useRef(false);

  const promptGroups = groupAssetsByPrompt(assets);
  const refreshSprintState = useCallback(async () => {
    if (!packId) return;
    try {
      const sprint = await sprintApi.getSprint(packId);
      setSprintDay(sprint?.current_day ?? null);
      setSprintMode(sprint?.mode ?? null);
    } catch {
      setSprintDay(null);
      setSprintMode(null);
    }
  }, [packId]);

  usePackRefreshListener(packId, ["sprint"], refreshSprintState);

  useEffect(() => {
    if (!packId) return;

    let cancelled = false;

    async function init() {
      try {
        const [pack, brand, assetsRes, sprint] = await Promise.all([
          packsApi.get(packId!),
          brandOsApi.getActive(packId!).catch(() => null),
          creativeApi.listAssets(packId!),
          sprintApi.getSprint(packId!).catch(() => null),
        ]);

        if (!cancelled) {
          setBrandContext(buildBrandContext(pack, brand ?? null));
          setAssets(toAssetsWithMeta(assetsRes.items));
          setSprintDay(sprint?.current_day ?? null);
          setSprintMode(sprint?.mode ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load poster builder",
          );
          setBrandContext({});
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [packId]);

  useEffect(() => {
    if (!packId || typeof document === "undefined") return;

    function onVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      creativeApi
        .listAssets(packId!)
        .then((res) => {
          setAssets(toAssetsWithMeta(res.items));
          setError(null);
        })
        .catch(() => {});
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [packId]);

  const handleFileGenerated = useCallback(
    async (
      name: string,
      code: string,
      messages: PosterConversationMessage[],
    ) => {
      if (!packId) return;
      try {
        const created = await creativeApi.createAsset({
          pack_id: packId,
          type: "poster",
          name,
          source_code: code,
          template_id: extractPosterTemplateIdFromFilename(name),
          chat_messages: messages.length > 0 ? messages : null,
        });

        const nextAsset: AssetWithMeta = {
          id: created.id,
          name: created.name ?? name,
          code: created.source_code ?? code,
          created_at: created.created_at,
          chat_messages: (created.chat_messages as PosterConversationMessage[] | null) ?? messages,
        };

        setAssets((prev) => {
          if (prev.some((asset) => asset.id === nextAsset.id)) {
            return prev;
          }
          return [...prev, nextAsset];
        });
        setGenerationProgress((prev) =>
          prev
            ? {
                ...prev,
                completedCount: Math.min(
                  prev.totalCount,
                  prev.completedCount + 1,
                ),
              }
            : prev,
        );
      } catch (e) {
        toast.error("Poster couldn't be saved. Try again.", {
          description: e instanceof Error ? e.message : String(e),
        });
      }
    },
    [packId],
  );

  useEffect(() => {
    if (
      !packId ||
      loading ||
      assets.length > 0 ||
      sprintDay === null ||
      sprintDay < 4 ||
      !brandContext ||
      autoGeneratedRef.current
    )
      return;

    autoGeneratedRef.current = true;
    const prompt = `Create 4 high-converting poster concepts for my brand.
Hard rules:
- Understood in 3 seconds.
- One clear promise and one CTA.
- Variants: Brutal truth, Clever twist, Proof-led, Editorial premium.
- Output must include 4 sizes for each variant: 4x5, 9x16, 16x9, 1x1.
- Return <summary> plus exactly 16 TSX files named:
poster-v1-4x5.tsx, poster-v1-9x16.tsx, poster-v1-16x9.tsx, poster-v1-1x1.tsx,
poster-v2-4x5.tsx, poster-v2-9x16.tsx, poster-v2-16x9.tsx, poster-v2-1x1.tsx,
poster-v3-4x5.tsx, poster-v3-9x16.tsx, poster-v3-16x9.tsx, poster-v3-1x1.tsx,
poster-v4-4x5.tsx, poster-v4-9x16.tsx, poster-v4-16x9.tsx, poster-v4-1x1.tsx.
- Each file must be self-contained TSX with inline styles only.`;
    setIsGenerating(true);
    setGenerationDisplay(buildAutoGenerationDisplay(sprintMode));
    setGenerationProgress({
      completedCount: 0,
      totalCount: GENERATION_FILE_TOTAL,
    });

    streamPosterGeneration(
      {
        apiRoute: "/api/v1/creative/generate",
        messages: [{ role: "user", content: prompt }],
        brandContext,
        packId,
        generationMode: "auto",
      },
      {
        onFile: async (name, code) => {
          await handleFileGenerated(name, code, buildAutoGenerationMessages(sprintMode));
        },
      },
    )
      .catch((err) => {
        autoGeneratedRef.current = false;
        toast.error("Auto-generation failed", {
          description: err instanceof Error ? err.message : String(err),
        });
      })
      .finally(() => {
        setIsGenerating(false);
        setGenerationDisplay(null);
        setGenerationProgress(null);
      });
  }, [
    packId,
    loading,
    assets.length,
    sprintDay,
    sprintMode,
    brandContext,
    handleFileGenerated,
  ]);

  const handleGeneratingChange = useCallback(
    (generating: boolean, display?: CreativeGenerationDisplay | null) => {
      setIsGenerating(generating);
      setGenerationDisplay(generating ? display ?? null : null);
      setGenerationProgress(null);
    },
    [],
  );

  const handleDeleteAsset = useCallback(
    async (assetId: string) => {
      if (!packId) return;
      try {
        await creativeApi.deleteAsset(assetId);
      } catch {
        // Still remove from UI
      }
      setAssets((prev) => prev.filter((a) => a.id !== assetId));
      setSelectedAsset((prev) => (prev?.id === assetId ? null : prev));
    },
    [packId],
  );

  if (!packId) return null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 min-w-0 overflow-hidden flex-col">
      <div className="flex flex-1 min-h-0 min-w-0 overflow-hidden">
        <CreativeFactoryLayout
          variant="posters"
          packId={packId}
          brandContext={brandContext}
          promptGroups={promptGroups}
          generationDisplay={generationDisplay}
          generationProgress={generationProgress}
          isGenerating={isGenerating}
          sprintDay={sprintDay}
          selectedAsset={selectedAsset}
          onAssetSelect={setSelectedAsset}
          onFileGenerated={handleFileGenerated}
          onGeneratingChange={handleGeneratingChange}
          onDeleteAsset={handleDeleteAsset}
        />
      </div>
    </div>
  );
}
