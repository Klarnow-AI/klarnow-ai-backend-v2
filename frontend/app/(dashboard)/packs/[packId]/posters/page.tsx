"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { packs as packsApi, creative as creativeApi } from "@/lib/api";
import { brandOs as brandOsApi } from "@/api_requests/brand-os";
import {
  Panel,
  Group,
  Separator,
  useDefaultLayout,
} from "react-resizable-panels";
import { BuilderChatPanel } from "../_components/builder-chat-panel";
import {
  PosterPreviewPanel,
  type PosterAsset,
} from "./_components/poster-preview-panel";

export type PosterWithMeta = PosterAsset & {
  id?: string;
  chat_messages?: { role: "user" | "assistant"; content: string }[];
};
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

function ResizableLayout({
  brandContext,
  posters,
  isGenerating,
  selectedPosterIndex,
  onSelectPosterIndex,
  onDeletePoster,
  onFilesGenerated,
  onGeneratingChange,
}: {
  brandContext: BrandContext | null;
  posters: PosterWithMeta[];
  isGenerating: boolean;
  selectedPosterIndex: number;
  onSelectPosterIndex: (index: number) => void;
  onDeletePoster: (index: number) => void;
  onFilesGenerated: (
    files: Record<string, string>,
    messages: { role: "user" | "assistant"; content: string }[]
  ) => void;
  onGeneratingChange: (generating: boolean) => void;
}) {
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: "posters-panel-layout",
    storage: typeof window !== "undefined" ? localStorage : undefined,
  });

  return (
    <Group
      orientation="horizontal"
      defaultLayout={defaultLayout}
      onLayoutChanged={onLayoutChanged}
      className="flex-1 min-h-0"
    >
      <Panel id="chat" defaultSize="30%" minSize="20%" maxSize="50%">
        <div className="flex flex-col h-full overflow-hidden">
          <BuilderChatPanel
            title="Posters & Flyers"
            apiRoute="/api/generate-poster"
            brandContext={brandContext}
            emptyStateTitle="Create a poster or flyer"
            emptyStateDescription="Describe the poster or flyer you'd like to create and Klaro will generate it using your brand identity."
            initialMessages={
              posters[selectedPosterIndex]?.chat_messages ?? undefined
            }
            threadKey={selectedPosterIndex}
            onFilesGenerated={onFilesGenerated}
            onGeneratingChange={onGeneratingChange}
          />
        </div>
      </Panel>

      <Separator className="w-1.5 bg-transparent hover:bg-primary/50 transition-colors duration-150 cursor-col-resize" />

      <Panel id="preview" defaultSize="70%" minSize="50%">
        <div className="h-full overflow-hidden">
          <PosterPreviewPanel
            posters={posters}
            isGenerating={isGenerating}
            selectedIndex={selectedPosterIndex}
            onSelectIndex={onSelectPosterIndex}
            onDeletePoster={onDeletePoster}
          />
        </div>
      </Panel>
    </Group>
  );
}

export default function PostersPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [brandContext, setBrandContext] = useState<BrandContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [posters, setPosters] = useState<PosterWithMeta[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedPosterIndex, setSelectedPosterIndex] = useState(0);

  useEffect(() => {
    if (!packId) return;

    let cancelled = false;

    async function init() {
      try {
        const [pack, brand, assetsRes] = await Promise.all([
          packsApi.get(packId!),
          brandOsApi.getActive(packId!).catch(() => null),
          creativeApi.listAssets(packId!),
        ]);

        if (!cancelled) {
          setBrandContext(buildBrandContext(pack, brand ?? null));
          const savedPosters: PosterWithMeta[] = assetsRes.items
            .filter(
              (a) =>
                (a.type === "poster" || a.type === "flyer") && a.source_code
            )
            .map((a) => ({
              name: a.name ?? `/${a.type}_${a.id}.tsx`,
              code: a.source_code!,
              id: a.id,
              chat_messages: a.chat_messages ?? undefined,
            }));
          setPosters(savedPosters);
          if (savedPosters.length > 0)
            setSelectedPosterIndex(savedPosters.length - 1);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load poster builder");
          setBrandContext({});
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [packId]);

  useEffect(() => {
    if (!packId || typeof document === "undefined") return;

    function onVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      creativeApi
        .listAssets(packId!)
        .then((res) => {
          const savedPosters: PosterWithMeta[] = res.items
            .filter(
              (a) =>
                (a.type === "poster" || a.type === "flyer") && a.source_code
            )
            .map((a) => ({
              name: a.name ?? `/${a.type}_${a.id}.tsx`,
              code: a.source_code!,
              id: a.id,
              chat_messages: a.chat_messages ?? undefined,
            }));
          setPosters(savedPosters);
          if (savedPosters.length > 0)
            setSelectedPosterIndex(savedPosters.length - 1);
          setError(null);
        })
        .catch(() => {
          // Keep current state; don't overwrite with empty or show error on refetch
        });
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [packId]);

  const handleFilesGenerated = useCallback(
    async (
      files: Record<string, string>,
      messages: { role: "user" | "assistant"; content: string }[]
    ) => {
      const newPosters: PosterWithMeta[] = [];
      let saveFailCount = 0;
      let lastSaveError: Error | null = null;
      for (const [name, code] of Object.entries(files)) {
        const poster: PosterWithMeta = { name, code };
        newPosters.push(poster);
        if (packId) {
          try {
            const created = await creativeApi.createAsset({
              pack_id: packId,
              type: "poster",
              name,
              source_code: code,
              template_id: null,
              chat_messages: messages.length > 0 ? messages : null,
            });
            poster.id = created.id;
            poster.chat_messages = created.chat_messages ?? undefined;
          } catch (e) {
            saveFailCount += 1;
            lastSaveError = e instanceof Error ? e : new Error(String(e));
          }
        }
      }
      if (saveFailCount > 0) {
        const message =
          saveFailCount === 1
            ? "Poster couldn't be saved. Try again."
            : `${saveFailCount} posters couldn't be saved. Try again.`;
        toast.error(message, {
          description: lastSaveError?.message,
        });
      }
      setPosters((prev) => [...prev, ...newPosters]);
      if (newPosters.length > 0)
        setSelectedPosterIndex(
          posters.length + newPosters.length - 1
        );
    },
    [packId]
  );

  const handleDeletePoster = useCallback(
    async (index: number) => {
      const poster = posters[index];
      if (!poster) return;
      if (poster.id && packId) {
        try {
          await creativeApi.deleteAsset(poster.id);
        } catch {
          // Still remove from UI on API failure so list doesn't get stuck
        }
      }
      setPosters((prev) => prev.filter((_, i) => i !== index));
      setSelectedPosterIndex((prev) => {
        if (prev === index) return Math.max(0, index - 1);
        if (prev > index) return prev - 1;
        return prev;
      });
    },
    [posters, packId]
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
    <div className="flex flex-1 min-h-0 overflow-hidden p-4">
      <ResizableLayout
        brandContext={brandContext}
        posters={posters}
        isGenerating={isGenerating}
        selectedPosterIndex={selectedPosterIndex}
        onSelectPosterIndex={setSelectedPosterIndex}
        onDeletePoster={handleDeletePoster}
        onFilesGenerated={handleFilesGenerated}
        onGeneratingChange={setIsGenerating}
      />
    </div>
  );
}
