"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adFactory } from "@/api_requests/ad-factory";
import { creative } from "@/api_requests/creative";
import type { AdFactoryVariant, GenerateVariantsResponse } from "@/api_requests/ad-factory";
import type { CreativeAsset } from "@/types/api-types";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { AdPreviewPanel } from "./_components/ad-preview-panel";

type Screen = "generate" | "overview" | "script-detail" | "render" | "launch";
type VideoAsset = CreativeAsset & { created_at: string };

function mergeVideos(existing: VideoAsset[], incoming: VideoAsset[]): VideoAsset[] {
  const byId = new Map(existing.map((video) => [video.id, video]));
  for (const video of incoming) {
    byId.set(video.id, video);
  }
  return Array.from(byId.values()).sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)
  );
}

export default function AdFactoryPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [screen, setScreen] = useState<Screen>("generate");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateVariantsResponse | null>(null);
  const [videos, setVideos] = useState<VideoAsset[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<"A" | "B" | "C" | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!packId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adFactory.generateVariants(packId);
      setResult(res);
      if (res.validation_status === "pass") {
        setScreen("overview");
        toast.success("3 variants generated");
      } else {
        const failed = res.validation_checks?.filter((c) => !c.passed);
        const msg = failed?.[0]?.message ?? "Validation failed";
        toast.error(msg);
        setError(msg);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to generate variants";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [packId]);

  const loadVideos = useCallback(async () => {
    if (!packId) return;
    try {
      const res = await creative.listAssets(packId);
      setVideos(
        res.items
          .filter((asset) => asset.type === "video")
          .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load rendered videos";
      toast.error(message);
    }
  }, [packId]);

  useEffect(() => {
    void loadVideos();
  }, [loadVideos]);

  const refreshVideosAfterRender = useCallback(() => {
    const delays = [2500, 8000];
    for (const delay of delays) {
      window.setTimeout(() => {
        void loadVideos();
      }, delay);
    }
  }, [loadVideos]);

  if (!packId) return null;

  return (
    <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden">
      <div className="flex-1 min-h-0 overflow-y-auto">
        {screen === "generate" && (
          <Screen1Generate
            onGenerate={handleGenerate}
            loading={loading}
            error={error}
            videos={videos}
          />
        )}
        {screen === "overview" && result && (
          <Screen2Overview
            variants={result.variants}
            videos={videos}
            onRenderWithKling={() => setScreen("render")}
            onSelectVariant={(v) => {
              setSelectedVariant(v);
              setScreen("script-detail");
            }}
          />
        )}
        {screen === "script-detail" && result && selectedVariant && (
          <Screen3ScriptDetail
            variant={result.variants.find((v) => v.slot === selectedVariant)!}
            onBack={() => setScreen("overview")}
            onRenderThisVariant={() => setScreen("render")}
          />
        )}
        {screen === "render" && result && (
          <Screen4RenderConfirmation
            variants={result.variants}
            loading={loading}
            onBack={() => setScreen("overview")}
            onConfirmAndRender={async () => {
              setLoading(true);
              try {
                const res = await adFactory.render(result.render_id, ["A", "B", "C"]);
                const renderedVideos = res.assets.filter(
                  (asset): asset is VideoAsset => asset.type === "video"
                );
                setVideos((current) => mergeVideos(current, renderedVideos));
                refreshVideosAfterRender();
                toast.success(`Rendered ${res.asset_ids.length} videos.`);
                setScreen("overview");
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "Render failed");
              } finally {
                setLoading(false);
              }
            }}
          />
        )}
      </div>

    </div>
  );
}

function Screen1Generate({
  onGenerate,
  loading,
  error,
  videos,
}: {
  onGenerate: () => void;
  loading: boolean;
  error: string | null;
  videos: VideoAsset[];
}) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <div className="mx-auto flex min-h-[60vh] w-full max-w-md flex-col items-center justify-center text-center">
        <div className="max-w-md space-y-4">
          <h2 className="text-xl font-semibold text-foreground">Generate Variants</h2>
          <p className="text-sm text-muted-foreground">
            Create exactly 3 conversion-ready ad variants from your BrandBrief and pack context.
            Deterministic, no prompts.
          </p>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={onGenerate} disabled={loading} size="lg" className="w-full">
            {loading ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Generating…
              </>
            ) : (
              "Generate Variants"
            )}
          </Button>
        </div>
      </div>
      {videos.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <AdPreviewPanel videos={videos} />
        </div>
      )}
    </div>
  );
}

function Screen2Overview({
  variants,
  videos,
  onRenderWithKling,
  onSelectVariant,
}: {
  variants: AdFactoryVariant[];
  videos: VideoAsset[];
  onRenderWithKling: () => void;
  onSelectVariant: (slot: "A" | "B" | "C") => void;
}) {
  return (
    <div className="p-4 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Variant Overview</h2>
        <Button onClick={onRenderWithKling}>Render with Kling</Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {variants.map((v) => (
          <button
            key={v.slot}
            type="button"
            onClick={() => onSelectVariant(v.slot)}
            className="rounded-xl border border-border bg-card p-4 text-left hover:border-primary/50 transition-colors"
          >
            <div className="text-sm font-medium text-foreground mb-1">
              Variant {v.slot} — {v.intent.replace("_", " ")}
            </div>
            <div className="text-xs text-muted-foreground mb-2">
              {v.treatment.replace(/_/g, " ")} · {v.hook_type.replace(/_/g, " ")}
            </div>
            <p className="text-sm line-clamp-2">{v.core_concept}</p>
          </button>
        ))}
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <AdPreviewPanel videos={videos} />
      </div>
    </div>
  );
}

function Screen3ScriptDetail({
  variant,
  onBack,
  onRenderThisVariant,
}: {
  variant: AdFactoryVariant;
  onBack: () => void;
  onRenderThisVariant: () => void;
}) {
  return (
    <div className="p-4 space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          Back
        </Button>
        <h2 className="text-lg font-semibold">Variant {variant.slot} — Script Detail</h2>
      </div>
      <div className="rounded-xl border border-border bg-card p-4 space-y-4">
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">Hook</div>
          <p className="text-sm">{variant.hook_line}</p>
        </div>
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">30s Script Beats</div>
          <ul className="space-y-1 text-sm">
            {variant.script_30s.beats.map((b, i) => (
              <li key={i}>
                <span className="text-muted-foreground">{b.beat_name}:</span> {b.text}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">Shot List</div>
          <ul className="space-y-1 text-sm">
            {variant.shot_list.map((s, i) => (
              <li key={i}>
                {s.shot_type}: {s.on_screen_text}
              </li>
            ))}
          </ul>
        </div>
        <Button onClick={onRenderThisVariant} className="w-full">
          Render This Variant
        </Button>
      </div>
    </div>
  );
}

function Screen4RenderConfirmation({
  variants,
  loading,
  onBack,
  onConfirmAndRender,
}: {
  variants: AdFactoryVariant[];
  loading: boolean;
  onBack: () => void;
  onConfirmAndRender: () => void | Promise<void>;
}) {
  const variantsCount = variants.length;
  return (
    <div className="p-4 space-y-6 max-w-md mx-auto">
      <Button variant="ghost" size="sm" onClick={onBack} disabled={loading}>
        Back
      </Button>
      <h2 className="text-lg font-semibold">Render Confirmation</h2>
      <p className="text-sm text-muted-foreground">
        This will render {variantsCount} video{variantsCount === 1 ? "" : "s"} with Kling.
      </p>
      <Button onClick={onConfirmAndRender} className="w-full" disabled={loading}>
        {loading ? (
          <>
            <Spinner className="mr-2 h-4 w-4" />
            Rendering…
          </>
        ) : (
          "Confirm & Render"
        )}
      </Button>
    </div>
  );
}
