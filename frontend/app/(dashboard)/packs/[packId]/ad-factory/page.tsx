"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adFactory } from "@/api_requests/ad-factory";
import type {
  AdFactoryCompile,
  AdFactoryRenderJob,
  AdFactoryVariant,
  RenderScope,
  VariantSlot,
} from "@/api_requests/ad-factory";
import { creative } from "@/api_requests/creative";
import type { CreativeAsset } from "@/types/api-types";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { AdPreviewPanel } from "./_components/ad-preview-panel";

type Screen =
  | "generate"
  | "overview"
  | "variant-detail"
  | "validation"
  | "render-confirmation"
  | "launch";
type VideoAsset = CreativeAsset & { created_at: string };

const SCOPE_LABELS: Record<RenderScope, string> = {
  single_variant_30: "Single Variant 30s",
  abc_bundle_30: "A/B/C Bundle 30s",
  abc_bundle_30_plus_15: "A/B/C Bundle 30s + 15s",
};

function isVideoAsset(asset: CreativeAsset): asset is VideoAsset {
  return asset.type === "video";
}

function sortVideos(items: VideoAsset[]): VideoAsset[] {
  return [...items].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

function mergeVideos(existing: VideoAsset[], incoming: VideoAsset[]): VideoAsset[] {
  const byId = new Map(existing.map((video) => [video.id, video]));
  for (const video of incoming) {
    byId.set(video.id, video);
  }
  return sortVideos(Array.from(byId.values()));
}

function creditsForScope(scope: RenderScope): number {
  if (scope === "single_variant_30") return 1;
  if (scope === "abc_bundle_30") return 3;
  return 5;
}

function scopeToRequest(scope: RenderScope, selectedVariant: VariantSlot) {
  if (scope === "single_variant_30") {
    return {
      selected_variants: [selectedVariant] as VariantSlot[],
      durations_requested: [30] as Array<15 | 30>,
    };
  }
  if (scope === "abc_bundle_30") {
    return {
      selected_variants: ["A", "B", "C"] as VariantSlot[],
      durations_requested: [30] as Array<15 | 30>,
    };
  }
  return {
    selected_variants: ["A", "B", "C"] as VariantSlot[],
    durations_requested: [15, 30] as Array<15 | 30>,
  };
}

function variantsFromCompile(compile: AdFactoryCompile | null): AdFactoryVariant[] {
  if (!compile) return [];
  const variants = compile.compile_result.variants;
  return [variants.A, variants.B, variants.C];
}

function nextLaunchSlot(compile: AdFactoryCompile | null): VariantSlot | null {
  if (!compile) return null;
  const launched = new Set(compile.launch_state.live_order.map((entry) => entry.slot));
  return compile.launch_recommendation.order.find((slot) => !launched.has(slot)) ?? null;
}

export default function AdFactoryPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [screen, setScreen] = useState<Screen>("generate");
  const [compile, setCompile] = useState<AdFactoryCompile | null>(null);
  const [renderJob, setRenderJob] = useState<AdFactoryRenderJob | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<VariantSlot>("A");
  const [renderScope, setRenderScope] = useState<RenderScope>("abc_bundle_30");
  const [videos, setVideos] = useState<VideoAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!packId) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await creative.listAssets(packId);
        if (cancelled) return;
        setVideos(sortVideos(res.items.filter(isVideoAsset)));
      } catch (err) {
        if (cancelled) return;
        toast.error(err instanceof Error ? err.message : "Failed to load rendered videos");
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [packId]);

  if (!packId) return null;

  const variants = variantsFromCompile(compile);
  const activeVariant = variants.find((variant) => variant.slot === selectedVariant) ?? variants[0] ?? null;
  const renderDisabled = compile?.validator_result.status !== "pass";
  const launchSlot = nextLaunchSlot(compile);
  const renderSelection = scopeToRequest(renderScope, selectedVariant);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const nextCompile = await adFactory.createCompile(packId);
      setCompile(nextCompile);
      setRenderJob(null);
      setSelectedVariant("A");
      setRenderScope("abc_bundle_30");
      setScreen("overview");
      if (nextCompile.validator_result.status === "pass") {
        toast.success("3 variants compiled");
      } else {
        const firstFailure = nextCompile.validator_result.blocking_errors[0];
        toast.error(firstFailure?.message ?? "Validation failed");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to compile Ad Factory variants";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmRender = async () => {
    if (!compile) return;
    setLoading(true);
    try {
      const nextRenderJob = await adFactory.createRenderJob({
        compile_result_id: compile.id,
        selected_variants: renderSelection.selected_variants,
        durations_requested: renderSelection.durations_requested,
        provider_target: "kling",
      });
      setRenderJob(nextRenderJob);
      setVideos((current) => mergeVideos(current, nextRenderJob.render_result.assets.filter(isVideoAsset)));
      setScreen("launch");
      toast.success(`Render created with ${nextRenderJob.render_result.asset_ids.length} video asset(s).`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Render failed");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkVariantLive = async () => {
    if (!compile || !launchSlot) return;
    setLoading(true);
    try {
      const response = await adFactory.markVariantLive(compile.id, launchSlot);
      setCompile((current) =>
        current
          ? {
              ...current,
              launch_state: response.launch_state,
            }
          : current,
      );
      toast.success(`Variant ${launchSlot} marked live`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update launch state");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden">
      <div className="flex-1 min-h-0 overflow-y-auto">
        {screen === "generate" && (
          <ScreenGenerate
            error={error}
            loading={loading}
            onGenerate={handleGenerate}
            videos={videos}
          />
        )}
        {screen === "overview" && compile && (
          <ScreenOverview
            compile={compile}
            selectedVariant={selectedVariant}
            onBack={() => setScreen("generate")}
            onChangeVariant={setSelectedVariant}
            onReviewVariant={() => setScreen("variant-detail")}
            videos={videos}
          />
        )}
        {screen === "variant-detail" && compile && activeVariant && (
          <ScreenVariantDetail
            variant={activeVariant}
            onBack={() => setScreen("overview")}
            onContinue={() => setScreen("validation")}
          />
        )}
        {screen === "validation" && compile && (
          <ScreenValidation
            compile={compile}
            loading={loading}
            renderScope={renderScope}
            selectedVariant={selectedVariant}
            onBack={() => setScreen("variant-detail")}
            onChangeScope={setRenderScope}
            onContinue={() => setScreen("render-confirmation")}
          />
        )}
        {screen === "render-confirmation" && compile && (
          <ScreenRenderConfirmation
            compile={compile}
            renderScope={renderScope}
            selectedVariant={selectedVariant}
            loading={loading}
            onBack={() => setScreen("validation")}
            onConfirm={handleConfirmRender}
          />
        )}
        {screen === "launch" && compile && (
          <ScreenLaunch
            compile={compile}
            loading={loading}
            renderJob={renderJob}
            videos={videos}
            nextSlot={launchSlot}
            onBack={() => setScreen("overview")}
            onMarkLive={handleMarkVariantLive}
          />
        )}
      </div>
      {renderDisabled && screen === "validation" && (
        <div className="border-t border-border bg-card px-4 py-3 text-sm text-destructive">
          Render is disabled until all blocking validation issues pass.
        </div>
      )}
    </div>
  );
}

function ScreenGenerate({
  error,
  loading,
  onGenerate,
  videos,
}: {
  error: string | null;
  loading: boolean;
  onGenerate: () => void;
  videos: VideoAsset[];
}) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <div className="mx-auto flex min-h-[60vh] w-full max-w-md flex-col items-center justify-center text-center">
        <div className="max-w-md space-y-4">
          <h2 className="text-xl font-semibold text-foreground">Generate Variants</h2>
          <p className="text-sm text-muted-foreground">
            Compile exactly three deterministic ad variants from your BrandBrief and sprint context.
          </p>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button onClick={onGenerate} disabled={loading} size="lg" className="w-full">
            {loading ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Compiling…
              </>
            ) : (
              "Generate Variants"
            )}
          </Button>
        </div>
      </div>
      {videos.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <AdPreviewPanel videos={videos} />
        </div>
      ) : null}
    </div>
  );
}

function ScreenOverview({
  compile,
  selectedVariant,
  onBack,
  onChangeVariant,
  onReviewVariant,
  videos,
}: {
  compile: AdFactoryCompile;
  selectedVariant: VariantSlot;
  onBack: () => void;
  onChangeVariant: (slot: VariantSlot) => void;
  onReviewVariant: () => void;
  videos: VideoAsset[];
}) {
  const variants = variantsFromCompile(compile);
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Variant Overview</h2>
          <p className="text-sm text-muted-foreground">
            Review the three locked slots before moving into validation.
          </p>
        </div>
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {variants.map((variant) => {
          const selected = variant.slot === selectedVariant;
          return (
            <button
              key={variant.slot}
              type="button"
              onClick={() => onChangeVariant(variant.slot)}
              className={`rounded-2xl border p-4 text-left transition-colors ${
                selected ? "border-primary bg-primary/5" : "border-border bg-card hover:border-primary/40"
              }`}
            >
              <div className="text-sm font-medium">
                Variant {variant.slot} · {variant.intent.replace(/_/g, " ")}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {variant.path.replace(/_/g, " ")} · {variant.treatment.replace(/_/g, " ")}
              </div>
              <p className="mt-3 text-sm">{variant.core_concept}</p>
              <p className="mt-2 text-xs text-muted-foreground">{variant.hook_line}</p>
            </button>
          );
        })}
      </div>
      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-sm font-medium">Compile Status</div>
            <div className="text-xs text-muted-foreground">
              {compile.validator_result.status === "pass"
                ? "Validation is ready once you review the chosen variant."
                : "Validation has blocking issues that must be resolved before render."}
            </div>
          </div>
          <Button onClick={onReviewVariant}>Review Variant</Button>
        </div>
      </div>
      {videos.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <AdPreviewPanel videos={videos} />
        </div>
      ) : null}
    </div>
  );
}

function ScreenVariantDetail({
  variant,
  onBack,
  onContinue,
}: {
  variant: AdFactoryVariant;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Variant {variant.slot} Detail</h2>
          <p className="text-sm text-muted-foreground">
            Script beats, anchor shots, and render intent all stay traceable to the registry.
          </p>
        </div>
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
      </div>
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="text-xs font-medium text-muted-foreground">Hook</div>
        <p className="mt-1 text-sm">{variant.hook_line}</p>
        <div className="mt-5 text-xs font-medium text-muted-foreground">30s Script</div>
        <ul className="mt-2 space-y-2 text-sm">
          {variant.script_30s.beats.map((beat) => (
            <li key={`${variant.slot}-${beat.beat_name}`}>
              <span className="font-medium capitalize">{beat.beat_name}</span>{" "}
              <span className="text-muted-foreground">
                ({beat.start_second}s-{beat.end_second}s)
              </span>
              : {beat.text}
            </li>
          ))}
        </ul>
        <div className="mt-5 text-xs font-medium text-muted-foreground">Anchor Shots</div>
        <ul className="mt-2 space-y-2 text-sm">
          {variant.anchor_shot_plan.map((shot) => (
            <li key={`${variant.slot}-${shot.index}`}>
              <span className="font-medium">{shot.shot_type.replace(/_/g, " ")}</span>: {shot.on_screen_text}
            </li>
          ))}
        </ul>
        <div className="mt-5 flex justify-end">
          <Button onClick={onContinue}>Continue to Validation</Button>
        </div>
      </div>
    </div>
  );
}

function ScreenValidation({
  compile,
  loading,
  renderScope,
  selectedVariant,
  onBack,
  onChangeScope,
  onContinue,
}: {
  compile: AdFactoryCompile;
  loading: boolean;
  renderScope: RenderScope;
  selectedVariant: VariantSlot;
  onBack: () => void;
  onChangeScope: (scope: RenderScope) => void;
  onContinue: () => void;
}) {
  const renderDisabled = compile.validator_result.status !== "pass";
  const scopes: RenderScope[] = ["single_variant_30", "abc_bundle_30", "abc_bundle_30_plus_15"];
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Validation Review</h2>
          <p className="text-sm text-muted-foreground">
            Hard business rules must pass before the render action unlocks.
          </p>
        </div>
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
      </div>
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="text-sm font-medium">
          Status:{" "}
          <span className={compile.validator_result.status === "pass" ? "text-green-600" : "text-destructive"}>
            {compile.validator_result.status}
          </span>
        </div>
        <ul className="mt-4 space-y-2 text-sm">
          {compile.validator_result.checks.map((check) => (
            <li key={check.check_id} className="flex items-start justify-between gap-4">
              <span>
                {check.check_id}
                {check.slot ? ` · ${check.slot}` : ""}
                {check.message ? ` · ${check.message}` : ""}
              </span>
              <span className={check.passed ? "text-green-600" : "text-destructive"}>
                {check.passed ? "pass" : "fail"}
              </span>
            </li>
          ))}
        </ul>
        {compile.claim_guard_result.blocking_errors.length > 0 ? (
          <div className="mt-5 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
            <div className="text-sm font-medium text-destructive">Claim guard blocked render</div>
            <ul className="mt-2 space-y-1 text-sm">
              {compile.claim_guard_result.blocking_errors.map((check) => (
                <li key={`${check.rule_id}-${check.field_path}`}>
                  {check.rule_id} · {check.field_path}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="text-sm font-medium">Credit Preview</div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {scopes.map((scope) => (
            <button
              key={scope}
              type="button"
              onClick={() => onChangeScope(scope)}
              className={`rounded-xl border p-4 text-left ${
                renderScope === scope ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"
              }`}
            >
              <div className="text-sm font-medium">{SCOPE_LABELS[scope]}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {creditsForScope(scope)} credit{creditsForScope(scope) === 1 ? "" : "s"}
                {scope === "single_variant_30" ? ` · Variant ${selectedVariant}` : ""}
              </div>
            </button>
          ))}
        </div>
        <div className="mt-5 flex justify-end">
          <Button onClick={onContinue} disabled={renderDisabled || loading}>
            Render with Kling
          </Button>
        </div>
      </div>
    </div>
  );
}

function ScreenRenderConfirmation({
  compile,
  renderScope,
  selectedVariant,
  loading,
  onBack,
  onConfirm,
}: {
  compile: AdFactoryCompile;
  renderScope: RenderScope;
  selectedVariant: VariantSlot;
  loading: boolean;
  onBack: () => void;
  onConfirm: () => void;
}) {
  const selection = scopeToRequest(renderScope, selectedVariant);
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-8">
      <Button variant="ghost" onClick={onBack} disabled={loading}>
        Back
      </Button>
      <div className="rounded-2xl border border-border bg-card p-5">
        <h2 className="text-xl font-semibold">Render Confirmation</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Kling remains the active render provider. The compile output stays provider-neutral.
        </p>
        <div className="mt-5 space-y-3 text-sm">
          <div>
            <span className="font-medium">Scope:</span> {SCOPE_LABELS[renderScope]}
          </div>
          <div>
            <span className="font-medium">Variants:</span> {selection.selected_variants.join(", ")}
          </div>
          <div>
            <span className="font-medium">Durations:</span> {selection.durations_requested.join("s, ")}s
          </div>
          <div>
            <span className="font-medium">Credits:</span> {creditsForScope(renderScope)}
          </div>
          <div>
            <span className="font-medium">Validation:</span> {compile.validator_result.status}
          </div>
        </div>
        <Button onClick={onConfirm} className="mt-6 w-full" disabled={loading}>
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
    </div>
  );
}

function ScreenLaunch({
  compile,
  loading,
  renderJob,
  videos,
  nextSlot,
  onBack,
  onMarkLive,
}: {
  compile: AdFactoryCompile;
  loading: boolean;
  renderJob: AdFactoryRenderJob | null;
  videos: VideoAsset[];
  nextSlot: VariantSlot | null;
  onBack: () => void;
  onMarkLive: () => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Launch Order</h2>
          <p className="text-sm text-muted-foreground">
            Use the recommended sequence to test emotion, clarity, then offer pressure.
          </p>
        </div>
        <Button variant="ghost" onClick={onBack}>
          Back
        </Button>
      </div>
      <div className="rounded-2xl border border-border bg-card p-5">
        <ol className="space-y-3">
          {compile.launch_recommendation.order.map((slot, index) => {
            const launched = compile.launch_state.live_order.some((entry) => entry.slot === slot);
            return (
              <li key={slot} className="flex items-start justify-between gap-4 text-sm">
                <div>
                  <div className="font-medium">
                    {index + 1}. Variant {slot}
                  </div>
                  <div className="text-muted-foreground">{compile.launch_recommendation.rationale[index]}</div>
                </div>
                <span className={launched ? "text-green-600" : "text-muted-foreground"}>
                  {launched ? "Live" : "Queued"}
                </span>
              </li>
            );
          })}
        </ol>
        <Button onClick={onMarkLive} disabled={loading || !nextSlot} className="mt-6">
          {nextSlot ? `Mark Variant ${nextSlot} as Live` : "All Variants Marked Live"}
        </Button>
        {renderJob ? (
          <div className="mt-4 text-sm text-muted-foreground">
            Latest render job: {renderJob.status} · {renderJob.render_result.asset_ids.length} assets
          </div>
        ) : null}
      </div>
      {videos.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <AdPreviewPanel videos={videos} />
        </div>
      ) : null}
    </div>
  );
}
