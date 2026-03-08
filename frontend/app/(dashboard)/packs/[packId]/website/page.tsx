"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import { packs as packsApi } from "@/lib/api";
import { brandOs as brandOsApi } from "@/api_requests/brand-os";
import { builder as builderApi } from "@/api_requests/builder";
import {
  Panel,
  Group,
  Separator,
  useDefaultLayout,
} from "react-resizable-panels";
import { MessageSquare, Monitor, RotateCcw } from "@/components/icons";
import { ChatPanel } from "@/components/builder/ChatPanel";
import { PreviewPanel } from "@/components/builder/PreviewPanel";
import { ExportButton } from "@/components/builder/ExportButton";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { useMediaQuery } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";
import type { Pack, BrandOS } from "@/types/api-types";
import type { BrandContext } from "@/types/generation";

function ResizableLayout({
  brandContext,
  packName,
}: {
  brandContext: BrandContext | null;
  packName: string;
}) {
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: "builder-panel-layout",
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
        <div className="h-full overflow-hidden">
          <ChatPanel brandContext={brandContext} packName={packName} />
        </div>
      </Panel>

      <Separator className="w-1.5 bg-border data-[active]:bg-primary hover:bg-primary transition-colors duration-150 cursor-col-resize flex items-center justify-center group">
        <div className="w-0.5 h-8 bg-muted-foreground/40 group-hover:bg-primary-foreground group-data-[active]:bg-primary-foreground rounded-full transition-colors" />
      </Separator>

      <Panel id="preview" defaultSize="70%" minSize="50%">
        <div className="h-full overflow-hidden">
          <PreviewPanel />
        </div>
      </Panel>
    </Group>
  );
}

function TabbedLayout({
  brandContext,
  packName,
}: {
  brandContext: BrandContext | null;
  packName: string;
}) {
  const [activeTab, setActiveTab] = useState<"chat" | "preview">("chat");
  const [refreshPreview, setRefreshPreview] = useState<(() => void) | null>(
    null,
  );
  const liveUrl = useProjectStore((s) => s.liveUrl);

  const handleRegisterRefresh = (refresh: () => void) => {
    setRefreshPreview(() => refresh);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Content area - flex-1, scrollable */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "chat" && (
          <div className="h-full overflow-hidden">
            <ChatPanel brandContext={brandContext} packName={packName} />
          </div>
        )}
        {activeTab === "preview" && (
          <div className="h-full overflow-hidden">
            <PreviewPanel onRegisterRefresh={handleRegisterRefresh} />
          </div>
        )}
      </div>

      {/* Fixed bottom bar - pill tabs + browser chrome when Preview */}
      <div
        className={cn(
          "shrink-0 border-t border-border bg-card",
          "pb-[env(safe-area-inset-bottom)]",
        )}
      >
        {/* Pill tabs */}
        <div className="flex items-center gap-2 px-4 py-3">
          <div className="flex rounded-full border border-border bg-muted/30 p-0.5">
            <button
              type="button"
              onClick={() => setActiveTab("chat")}
              className={cn(
                "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                activeTab === "chat"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("preview")}
              className={cn(
                "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                activeTab === "preview"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Monitor className="h-4 w-4" />
              Preview
            </button>
          </div>
        </div>

        {/* Browser chrome - only when Preview active */}
        {activeTab === "preview" && (
          <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border/50">
            <span className="text-xs text-muted-foreground truncate min-w-0">
              {liveUrl ? liveUrl.replace(/^https?:\/\//, "") : "preview"}
            </span>
            <button
              type="button"
              onClick={() => refreshPreview?.()}
              aria-label="Refresh preview"
              className="shrink-0 p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

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

export default function WebsiteModule() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const [brandContext, setBrandContext] = useState<BrandContext | null>(null);
  const [packName, setPackName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  useEffect(() => {
    if (!packId) return;
    useProjectStore.getState().setActivePack(packId);

    let cancelled = false;

    async function init() {
      try {
        const [pack, brand] = await Promise.all([
          packsApi.get(packId!),
          brandOsApi.getActive(packId!).catch(() => null),
        ]);

        if (cancelled) return;

        setPackName(pack.name);
        setBrandContext(buildBrandContext(pack, brand ?? null));

        let project = await builderApi.getByPack(packId!).catch(() => null);
        if (!project) {
          project = await builderApi
            .create(packId!, pack.name ?? "Untitled Project")
            .catch(() => null);
        }

        if (!cancelled && project) {
          useProjectStore.getState().hydrate({
            files: project.files ?? {},
            messages: project.messages ?? [],
            projectId: project.id,
            liveUrl: project.live_url ?? null,
            publishedFiles: project.published_files ?? null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load website builder",
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
    <div className="absolute inset-0 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-[600] text-foreground tracking-tight">
            Website Builder
          </h1>
          <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-full bg-accent">
            Beta
          </span>
        </div>
        <ExportButton />
      </div>

      {isDesktop ? (
        <ResizableLayout brandContext={brandContext} packName={packName} />
      ) : (
        <TabbedLayout brandContext={brandContext} packName={packName} />
      )}
    </div>
  );
}
