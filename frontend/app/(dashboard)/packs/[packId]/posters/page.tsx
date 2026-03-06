"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { packs as packsApi, creative as creativeApi } from "@/lib/api";
import { brandOs as brandOsApi } from "@/api_requests/brand-os";
import { sprintApi } from "@/api_requests/sprint";
import { generatePosters } from "@/lib/generate-poster";
import {
  extractPosterTemplateIdFromFilename,
  sortPosterFiles,
} from "@/lib/poster-output";
import { CreativeFactoryLayout } from "../_components/creative-factory-layout";
import type { CreativeTemplateCardAsset } from "../_components/creative-template-card";
import type { PromptWithResults } from "../_components/creative-template-grid";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import type { Pack, BrandOS } from "@/types/api-types";
import type { BrandContext } from "@/app/api/generate/route";

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
  chat_messages?: { role: string; content: string }[] | null;
};

function getPromptFromAsset(asset: AssetWithMeta): string {
  const msgs = asset.chat_messages;
  if (!msgs || !Array.isArray(msgs)) return "Your creation";
  const userMsg = msgs.find((m) => m.role === "user");
  return userMsg?.content?.trim() || "Your creation";
}

function groupAssetsByPrompt(assets: AssetWithMeta[]): PromptWithResults[] {
  const sorted = [...assets].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  const groups: PromptWithResults[] = [];
  let current: {
    prompt: string;
    results: CreativeTemplateCardAsset[];
    createdAt: string;
  } | null = null;

  for (const asset of sorted) {
    const prompt = getPromptFromAsset(asset);
    const card: CreativeTemplateCardAsset = {
      id: asset.id,
      name: asset.name,
      code: asset.code,
    };
    if (current && current.prompt === prompt) {
      current.results.push(card);
    } else {
      current = { prompt, results: [card], createdAt: asset.created_at };
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
    chat_messages?: { role: string; content: string }[] | null;
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
  const [generatingPrompt, setGeneratingPrompt] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] =
    useState<CreativeTemplateCardAsset | null>(null);
  const [sprintDay, setSprintDay] = useState<number | null>(null);
  const autoGeneratedRef = useRef(false);

  const promptGroups = groupAssetsByPrompt(assets);

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

  const handleFilesGenerated = useCallback(
    async (
      files: Record<string, string>,
      messages: { role: "user" | "assistant"; content: string }[],
    ) => {
      let newAssets: AssetWithMeta[] = [];
      let saveFailCount = 0;
      let lastSaveErrorMessage: string | undefined;
      const now = new Date().toISOString();

      const orderedFiles = sortPosterFiles(files);
      newAssets = orderedFiles.map(([name, code]) => ({
        name,
        code,
        created_at: now,
        chat_messages: messages,
      }));

      if (packId) {
        await Promise.all(
          newAssets.map(async (asset) => {
            try {
              const created = await creativeApi.createAsset({
                pack_id: packId,
                type: "poster",
                name: asset.name,
                source_code: asset.code,
                template_id: extractPosterTemplateIdFromFilename(asset.name),
                chat_messages: messages.length > 0 ? messages : null,
              });
              asset.id = created.id;
              asset.created_at = created.created_at;
            } catch (e) {
              saveFailCount += 1;
              lastSaveErrorMessage =
                e instanceof Error ? e.message : String(e);
            }
          }),
        );
      }
      if (saveFailCount > 0) {
        const message =
          saveFailCount === 1
            ? "Poster couldn't be saved. Try again."
            : `${saveFailCount} posters couldn't be saved. Try again.`;
        toast.error(message, {
          description: lastSaveErrorMessage,
        });
      }
      setAssets((prev) => [...prev, ...newAssets]);
      setGeneratingPrompt(null);
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
    setGeneratingPrompt(prompt);

    generatePosters("/api/generate-poster", prompt, brandContext)
      .then((files) => {
        if (Object.keys(files).length > 0) {
          const messages = [
            { role: "user" as const, content: prompt },
            {
              role: "assistant" as const,
              content: "Done! Your designs have been generated.",
            },
          ];
          handleFilesGenerated(files, messages);
        }
      })
      .catch((err) => {
        autoGeneratedRef.current = false;
        toast.error("Auto-generation failed", {
          description: err instanceof Error ? err.message : String(err),
        });
      })
      .finally(() => {
        setIsGenerating(false);
        setGeneratingPrompt(null);
      });
  }, [
    packId,
    loading,
    assets.length,
    sprintDay,
    brandContext,
    handleFilesGenerated,
  ]);

  const handleGeneratingChange = useCallback(
    (generating: boolean, prompt?: string | null) => {
      setIsGenerating(generating);
      setGeneratingPrompt(generating && prompt ? prompt : null);
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
          generatingPrompt={generatingPrompt}
          isGenerating={isGenerating}
          selectedAsset={selectedAsset}
          onAssetSelect={setSelectedAsset}
          onFilesGenerated={handleFilesGenerated}
          onGeneratingChange={handleGeneratingChange}
          onDeleteAsset={handleDeleteAsset}
        />
      </div>
    </div>
  );
}
