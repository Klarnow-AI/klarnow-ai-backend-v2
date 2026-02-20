"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { usePackLayoutContext } from "../_context/pack-layout-context";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  Users,
  Target,
  LayoutDashboard,
  Loader2,
  Settings,
  Mic,
  FileText,
  Palette,
  X,
  Sparkles,
  Trash2,
} from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/page-loader";
import { brandOs } from "@/api_requests/brand-os";
import { packs as packsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  BrandOS,
  Pack,
  BrandStrategyProfile,
  MissionVision,
  AudiencePersona,
  PositioningDifferentiation,
  VoicePersonality,
  CoreMessagingHierarchy,
  StyleDirectionSeeds,
} from "@/types/api-types";

const PILLS = [
  { id: "all", label: "All" },
  { id: "mission_vision", label: "Mission & Vision" },
  { id: "audience", label: "Audience" },
  { id: "positioning", label: "Positioning" },
  { id: "voice", label: "Voice & Personality" },
  { id: "messaging", label: "Messaging" },
  { id: "style", label: "Style" },
] as const;

type PillId = (typeof PILLS)[number]["id"];

type EditSectionId =
  | "mission_vision"
  | "audience"
  | "positioning"
  | "voice"
  | "messaging"
  | "style";

const EDIT_SECTION_LABELS: Record<EditSectionId, string> = {
  mission_vision: "Edit Mission & Vision",
  audience: "Edit Audience Personas",
  positioning: "Edit Positioning & Differentiation",
  voice: "Edit Voice & Personality",
  messaging: "Edit Messaging",
  style: "Edit Style",
};

const LOGO_STYLE_CHIPS = [
  "minimal",
  "geometric",
  "playful",
  "professional",
  "modern",
  "classic",
  "bold",
  "abstract",
] as const;

const LOGO_COLOR_CHIPS = [
  "blue and white",
  "black and white",
  "neutral and versatile",
  "warm earth tones",
  "bold primary colors",
  "monochrome",
  "pastel",
  "high contrast",
] as const;

function DrawerFieldLabel({
  label,
  suggestLabel = "Suggest with AI",
  onSuggestClick,
  isSuggesting,
}: {
  label: string;
  suggestLabel?: string;
  onSuggestClick?: () => void | Promise<void>;
  isSuggesting?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const busy = isSuggesting ?? loading;
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      {onSuggestClick ? (
        <button
          type="button"
          onClick={async () => {
            setLoading(true);
            try {
              await onSuggestClick();
            } finally {
              setLoading(false);
            }
          }}
          disabled={busy}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
        >
          {busy ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          {suggestLabel}
        </button>
      ) : null}
    </div>
  );
}

function TextareaWithIcon({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full min-h-[160px] rounded-lg border border-border bg-background px-3 py-2 text-sm resize-none",
        className,
      )}
      {...props}
    />
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
      {children}
    </span>
  );
}

/** Renders a color swatch (actual color only, no text). Value should be hex or valid CSS color. */
function ColorSwatch({ value }: { value: string }) {
  const cssColor = /^#|^rgb|^hsl/.test(value)
    ? value
    : `#${value.replace(/^#/, "")}`;
  return (
    <div
      className="h-8 w-8 rounded-md border border-border shrink-0 shadow-sm"
      style={{ backgroundColor: cssColor }}
      title={value}
    />
  );
}

function SectionCard({
  title,
  icon: Icon,
  iconBg,
  onEdit,
  children,
  emptyMessage,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  iconBg: string;
  onEdit?: () => void;
  children: React.ReactNode;
  emptyMessage: string;
}) {
  const isEmpty =
    children == null ||
    (typeof children === "string" && !children.trim()) ||
    (Array.isArray(children) && children.length === 0);
  return (
    <div className="rounded-2xl border border-border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/30 px-5 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${iconBg} text-white`}
          >
            <Icon className="h-4 w-4" size={18} />
          </div>
          <h2 className="text-sm font-semibold text-foreground truncate">
            {title}
          </h2>
        </div>
        {onEdit && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-muted-foreground hover:text-foreground"
            onClick={onEdit}
          >
            <Settings className="h-3.5 w-3.5" />
            Edit
          </Button>
        )}
      </div>
      <div className="px-5 py-4">
        {isEmpty ? (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

const defaultMissionVision: MissionVision = {
  mission: "",
  vision: "",
  promise: "",
};
const defaultPositioning: PositioningDifferentiation = {
  statement: "",
  unique_advantage: "",
};
const defaultVoice: VoicePersonality = {
  profile: [],
  archetype: "",
  we_are: [],
  we_are_not: [],
};
const defaultMessaging: CoreMessagingHierarchy = {
  elevator_pitch: "",
  proof_points: [],
};
const defaultStyle: StyleDirectionSeeds = {
  typography: "",
  design_cues: [],
  palette: [],
};

export default function BrandOSPage() {
  const params = useParams();
  const packId = params.packId as string;
  const packLayout = usePackLayoutContext();
  const [active, setActive] = useState<BrandOS | null | undefined>(undefined);
  const [pack, setPack] = useState<Pack | null>(null);
  const [pill, setPill] = useState<PillId>("all");
  const [regenerating, setRegenerating] = useState(false);
  const [logoLoadFailed, setLogoLoadFailed] = useState(false);
  const [logoDrawerOpen, setLogoDrawerOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<EditSectionId | null>(
    null,
  );
  const [editDraft, setEditDraft] = useState<Partial<BrandStrategyProfile>>({});
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [suggestingField, setSuggestingField] = useState<string | null>(null);
  const [logoUploading, setLogoUploading] = useState(false);
  const [logoGenerating, setLogoGenerating] = useState(false);
  const [logoRemoving, setLogoRemoving] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  const [logoStyleChips, setLogoStyleChips] = useState<string[]>([]);
  const [logoColorChips, setLogoColorChips] = useState<string[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [suggestTypographyLoading, setSuggestTypographyLoading] = useState(false);
  const [suggestPaletteLoading, setSuggestPaletteLoading] = useState(false);
  const [suggestIdentityError, setSuggestIdentityError] = useState<string | null>(null);
  const hasAutoSuggestedPaletteRef = useRef(false);

  useEffect(() => {
    brandOs
      .getActive(packId)
      .then(setActive)
      .catch(() => setActive(null));
  }, [packId]);

  useEffect(() => {
    packsApi
      .get(packId)
      .then(setPack)
      .catch(() => setPack(null));
  }, [packId]);

  useEffect(() => {
    setLogoLoadFailed(false);
  }, [pack?.onboarding_answers]);

  async function handleRegenerate() {
    if (!active?.id) return;
    setRegenerating(true);
    try {
      const updated = await brandOs.regenerate(packId, active.id);
      setActive(updated ?? null);
    } catch {
      // Error surfaced by API
    } finally {
      setRegenerating(false);
    }
  }

  function openEdit(section: EditSectionId) {
    if (!active?.brand_strategy) return;
    const bs = active.brand_strategy;
    switch (section) {
      case "mission_vision":
        setEditDraft({
          mission_vision: { ...defaultMissionVision, ...bs.mission_vision },
        });
        break;
      case "audience":
        setEditDraft({
          audience_personas:
            (bs.audience_personas ?? []).length > 0
              ? JSON.parse(JSON.stringify(bs.audience_personas))
              : [{ persona: "", needs: [], pain_points: [] }],
        });
        break;
      case "positioning":
        setEditDraft({
          positioning_differentiation: {
            ...defaultPositioning,
            ...bs.positioning_differentiation,
          },
        });
        break;
      case "voice":
        setEditDraft({
          voice_personality: { ...defaultVoice, ...bs.voice_personality },
        });
        break;
      case "messaging":
        setEditDraft({
          core_messaging_hierarchy: {
            ...defaultMessaging,
            ...bs.core_messaging_hierarchy,
          },
        });
        break;
      case "style":
        setEditDraft({
          style_direction_seeds: {
            ...defaultStyle,
            ...bs.style_direction_seeds,
          },
        });
        break;
    }
    setSaveError(null);
    setEditingSection(section);
  }

  function closeEdit() {
    setEditingSection(null);
    setLogoDrawerOpen(false);
    setEditDraft({});
    setSaveError(null);
    setLogoError(null);
    setSuggestIdentityError(null);
  }

  async function handleSaveEdit() {
    if (!active?.brand_strategy || !editingSection) return;
    setSaveLoading(true);
    setSaveError(null);
    try {
      const merged: BrandStrategyProfile = {
        ...active.brand_strategy,
        ...editDraft,
      };
      const updated = await brandOs.updateActive(packId, {
        brand_strategy: merged,
      });
      setActive(updated);
      closeEdit();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleSuggest(
    fieldKey: string,
    currentValue: string,
    applySuggestion: (suggestion: string) => void,
  ) {
    setSuggestingField(fieldKey);
    try {
      const res = await brandOs.suggest(packId, {
        field: fieldKey,
        current_value: currentValue || undefined,
      });
      applySuggestion(res.suggestion);
    } catch {
      setSaveError("Could not get suggestion");
    } finally {
      setSuggestingField(null);
    }
  }

  async function handleSuggestTypography() {
    if (!pack) return;
    setSuggestIdentityError(null);
    setSuggestTypographyLoading(true);
    try {
      const oa = pack.onboarding_answers as Record<string, string> | undefined;
      let fontNames: string[] = [];
      if (typeof oa?.fonts === "string") {
        try {
          const f = JSON.parse(oa.fonts);
          fontNames = Array.isArray(f) ? f : typeof f === "string" ? [f] : [];
        } catch {}
      }
      const currentHeadline = fontNames[0] ?? undefined;
      const currentBody = fontNames[1] ?? fontNames[0] ?? undefined;
      const res = await packsApi.suggestTypography(packId, {
        current_headline: currentHeadline,
        current_body: currentBody,
      });
      await packsApi.patch(packId, {
        onboarding_answers: {
          ...(pack.onboarding_answers as Record<string, string>),
          fonts: JSON.stringify([res.headline_font, res.body_font]),
        },
      });
      const updated = await packsApi.get(packId);
      setPack(updated);
    } catch (e) {
      setSuggestIdentityError(e instanceof Error ? e.message : "Could not suggest typography");
    } finally {
      setSuggestTypographyLoading(false);
    }
  }

  async function handleSuggestPalette() {
    if (!pack) return;
    setSuggestIdentityError(null);
    setSuggestPaletteLoading(true);
    try {
      const currentEntries = [
        ['primary', palette.primary],
        ['secondary', palette.secondary],
        ['accent', palette.accent],
        ['background', palette.background],
        ['surface', palette.surface],
      ].filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1].length > 0);
      const current: Record<string, string> | undefined =
        currentEntries.length > 0 ? Object.fromEntries(currentEntries) : undefined;
      const res = await packsApi.suggestPalette(packId, current ? { current_palette: current } : undefined);
      const nextPalette: Record<string, string> = {
        primary: res.primary,
        secondary: res.secondary,
        accent: res.accent,
      };
      if (res.background) nextPalette.background = res.background;
      if (res.surface) nextPalette.surface = res.surface;
      await packsApi.patch(packId, {
        onboarding_answers: {
          ...(pack.onboarding_answers as Record<string, string>),
          palette: JSON.stringify(nextPalette),
        },
      });
      const updated = await packsApi.get(packId);
      setPack(updated);
    } catch (e) {
      setSuggestIdentityError(e instanceof Error ? e.message : "Could not suggest palette");
    } finally {
      setSuggestPaletteLoading(false);
    }
  }

  // Auto-suggest palette once for new brands (no palette, no extracted colors)
  useEffect(() => {
    if (!pack?.onboarding_answers || hasAutoSuggestedPaletteRef.current) return;
    const oa = pack.onboarding_answers as Record<string, string>;
    let parsedPalette: Record<string, string> = {};
    try {
      if (oa.palette) parsedPalette = JSON.parse(oa.palette);
    } catch {}
    let extracted: { color_candidates?: string[] } | null = null;
    try {
      if (oa.extracted_brand) extracted = JSON.parse(oa.extracted_brand);
    } catch {}
    const hasPalette = !!(
      parsedPalette.primary ||
      parsedPalette.secondary ||
      parsedPalette.accent
    );
    const hasExtracted = !!extracted?.color_candidates?.length;
    if (hasPalette || hasExtracted) return;
    hasAutoSuggestedPaletteRef.current = true;
    handleSuggestPalette();
  }, [pack]);

  if (active === undefined) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[40vh]">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const bs = active?.brand_strategy;
  const mv = bs?.mission_vision;
  const personas = bs?.audience_personas ?? [];
  const positioning = bs?.positioning_differentiation;
  const voice = bs?.voice_personality;
  const messaging = bs?.core_messaging_hierarchy;
  const style = bs?.style_direction_seeds;

  const showMissionVision = pill === "all" || pill === "mission_vision";
  const showAudience = pill === "all" || pill === "audience";
  const showPositioning = pill === "all" || pill === "positioning";
  const showVoice = pill === "all" || pill === "voice";
  const showMessaging = pill === "all" || pill === "messaging";
  const showStyle = pill === "all" || pill === "style";

  // Brand identity from pack onboarding: extract-from-website or generate-starter-brand
  const onboarding = pack?.onboarding_answers as
    | Record<string, string>
    | undefined;
  type ExtractedBrand = {
    brand_name?: string;
    logo_url?: string;
    color_candidates?: string[];
  };
  let extractedBrand: ExtractedBrand | null = null;
  if (typeof onboarding?.extracted_brand === "string") {
    try {
      extractedBrand = JSON.parse(onboarding.extracted_brand) as ExtractedBrand;
    } catch {}
  }
  const paletteRaw = onboarding?.palette;
  let palette: {
    primary?: string;
    secondary?: string;
    accent?: string;
    [k: string]: string | undefined;
  } = {};
  if (typeof paletteRaw === "string") {
    try {
      palette = JSON.parse(paletteRaw) as typeof palette;
    } catch {}
  }
  const fontNames: string[] = onboarding?.fonts
    ? (() => {
        try {
          const f = JSON.parse(onboarding.fonts);
          return Array.isArray(f) ? f : typeof f === "string" ? [f] : [];
        } catch {
          return [];
        }
      })()
    : [];
  const colorCandidates = extractedBrand?.color_candidates ?? [];
  const wordmarkSvgOrUrl =
    onboarding?.wordmark_svg_or_url ??
    onboarding?.wordmark_result ??
    extractedBrand?.logo_url;
  const brandName = extractedBrand?.brand_name ?? onboarding?.brand_name;
  // Display list: palette values first (no role labels in UI), then extracted candidates if any
  const PALETTE_ORDER = ["primary", "secondary", "accent", "background", "surface"] as const;
  const paletteValues = PALETTE_ORDER.map((k) => palette[k]).filter(
    (v): v is string => !!v && typeof v === "string" && v.trim() !== "",
  );
  const normalizedSet = new Set(paletteValues.map((v) => v.trim().toLowerCase()));
  const extraFromExtract =
    colorCandidates.filter(
      (c) => typeof c === "string" && c.trim() && !normalizedSet.has(c.trim().toLowerCase()),
    ).slice(0, 8) ?? [];
  const displayColors =
    paletteValues.length > 0
      ? [...paletteValues, ...extraFromExtract]
      : colorCandidates
          .filter((c): c is string => typeof c === "string" && c.trim() !== "")
          .slice(0, 8);
  const hasPaletteColors = displayColors.length > 0;
  const hasBrandIdentity =
    !!wordmarkSvgOrUrl ||
    fontNames.length > 0 ||
    hasPaletteColors ||
    !!brandName?.trim();

  const brandOsSummary = (() => {
    if (!bs) return "";
    const parts: string[] = [];
    if (mv?.mission) parts.push(`Mission: ${mv.mission}`);
    if (mv?.vision) parts.push(`Vision: ${mv.vision}`);
    if (positioning?.statement) parts.push(`Positioning: ${positioning.statement}`);
    if (positioning?.unique_advantage) parts.push(`Unique advantage: ${positioning.unique_advantage}`);
    if (voice?.archetype) parts.push(`Voice: ${voice.archetype}`);
    if (messaging?.elevator_pitch) parts.push(`Elevator pitch: ${messaging.elevator_pitch}`);
    if (style?.design_cues?.length) parts.push(`Design cues: ${style.design_cues.join(", ")}`);
    return parts.join(". ");
  })();

  const headlineFont = fontNames[0] ?? null;
  const bodyFont = fontNames[1] ?? fontNames[0] ?? null;

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {}
  };
  const toHex = (color: string): string => {
    if (!color?.trim()) return "";
    const c = color.trim();
    if (/^#[0-9A-Fa-f]{3,8}$/.test(c)) return c;
    if (/^#[0-9A-Fa-f]+$/.test(c)) return c.length >= 7 ? c : `#${c.slice(1).padEnd(6, "0")}`;
    return c.startsWith("rgb") || c.startsWith("hsl") ? c : `#${c.replace(/^#/, "")}`;
  };
  const primaryColor = palette.primary ?? displayColors[0];
  const primaryHex = primaryColor ? toHex(primaryColor) : undefined;

  return (
    <div className="flex flex-col min-h-full w-full max-w-full min-w-0 p-4 sm:p-6 lg:p-8 overflow-x-hidden">
      <div className="flex flex-1 w-full max-w-5xl mx-auto flex-col gap-6">
        {!pack ? (
          <div className="rounded-2xl border border-border bg-card p-8 text-center">
            <p className="text-muted-foreground mb-4">
              No Brand Identity yet. Complete onboarding or open Brand Identity
              to add your logo, fonts, and colours.
            </p>
            <Button onClick={() => packLayout?.openChatPopover()}>
              Open Chat with Klaro
            </Button>
          </div>
        ) : (
          <>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Brand Identity
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Inherited by page, ads, posters, proposals, and invoices.
              </p>
            </div>

            {/* Preview strip */}
            {(brandName || primaryHex || headlineFont) && (
              <div
                className="rounded-xl border border-border bg-card overflow-hidden"
                style={primaryHex ? { backgroundColor: `${primaryHex}12` } : undefined}
              >
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                  <span
                    className="font-bold text-foreground truncate"
                    style={headlineFont ? { fontFamily: `"${headlineFont}", sans-serif` } : undefined}
                  >
                    {brandName || "Your brand"}
                  </span>
                  {pack?.primary_cta && (
                    <span
                      className="rounded-lg px-3 py-1.5 text-sm font-medium text-white shrink-0"
                      style={primaryHex ? { backgroundColor: primaryHex } : undefined}
                    >
                      {pack.primary_cta}
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-8 lg:gap-10">
              {/* Left: Visual identity */}
              <div className="space-y-6">
                <h2 className="text-sm font-semibold text-foreground">Visual identity</h2>

                {/* Logo */}
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Logo
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSuggestIdentityError(null);
                        setLogoDrawerOpen(true);
                      }}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      {wordmarkSvgOrUrl && !logoLoadFailed ? "Refine with AI" : "Suggest with AI"}
                    </button>
                  </div>
                  {wordmarkSvgOrUrl && !logoLoadFailed ? (
                    <button
                      type="button"
                      onClick={() => setLogoDrawerOpen(true)}
                      className="w-full rounded-xl border border-border bg-card p-8 flex items-center justify-center min-h-[140px] cursor-pointer hover:border-muted-foreground/50 transition-colors"
                      aria-label="Change logo"
                    >
                      {typeof wordmarkSvgOrUrl === "string" &&
                      wordmarkSvgOrUrl.trimStart().startsWith("<") ? (
                        <div
                          className="max-h-24 flex items-center justify-center [&>svg]:max-w-full [&>svg]:max-h-24"
                          dangerouslySetInnerHTML={{ __html: wordmarkSvgOrUrl }}
                        />
                      ) : (
                        <img
                          src={wordmarkSvgOrUrl as string}
                          alt={brandName ? `${brandName} logo` : "Brand logo"}
                          className="max-h-24 object-contain"
                          onError={() => setLogoLoadFailed(true)}
                        />
                      )}
                    </button>
                  ) : (
                    <div
                      className="w-full rounded-xl border-2 border-dashed border-muted-foreground/30 bg-muted/20 p-8 flex flex-col items-center justify-center min-h-[140px] gap-3"
                    >
                      <p className="text-sm text-muted-foreground text-center">
                        Upload or generate with AI
                      </p>
                      <Button onClick={() => setLogoDrawerOpen(true)} size="sm">
                        Add logo
                      </Button>
                    </div>
                  )}
                </div>

                {/* Palette */}
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <Palette className="h-4 w-4 text-muted-foreground" />
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Palette
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={handleSuggestPalette}
                      disabled={suggestPaletteLoading}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {suggestPaletteLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      {hasPaletteColors ? "Refine with AI" : "Suggest with AI"}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-4">
                    {displayColors.map((color, i) => {
                      const cssColor = color
                        ? /^#|^rgb|^hsl/.test(color)
                          ? color
                          : `#${color.replace(/^#/, "")}`
                        : undefined;
                      const hex = color ? toHex(color) : "";
                      const id = `hex-${i}`;
                      return (
                        <button
                          key={id}
                          type="button"
                          onClick={() => hex && copyToClipboard(hex, id)}
                          className={cn(
                            "h-16 w-16 rounded-xl border border-border shadow-sm shrink-0",
                            hex && "cursor-pointer hover:ring-2 hover:ring-primary/50",
                          )}
                          style={cssColor ? { backgroundColor: cssColor } : undefined}
                          title={hex ? "Copy hex" : undefined}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Typography */}
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Typography
                    </span>
                    <button
                      type="button"
                      onClick={handleSuggestTypography}
                      disabled={suggestTypographyLoading}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {suggestTypographyLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                      {headlineFont || bodyFont ? "Refine with AI" : "Suggest with AI"}
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-border bg-card p-4">
                      <span className="text-xs text-muted-foreground block mb-1">Headlines</span>
                      <button
                        type="button"
                        onClick={() => headlineFont && copyToClipboard(headlineFont, "font-headline")}
                        className="text-left w-full"
                      >
                        <p className="text-lg font-bold text-foreground truncate">
                          {headlineFont || "—"}
                        </p>
                        {headlineFont && (
                          <span className="text-[10px] text-muted-foreground">
                            {copiedId === "font-headline" ? "Copied" : "Click to copy"}
                          </span>
                        )}
                      </button>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4">
                      <span className="text-xs text-muted-foreground block mb-1">Body</span>
                      <button
                        type="button"
                        onClick={() => bodyFont && copyToClipboard(bodyFont, "font-body")}
                        className="text-left w-full"
                      >
                        <p className="text-lg font-medium text-foreground truncate">
                          {bodyFont || "—"}
                        </p>
                        {bodyFont && (
                          <span className="text-[10px] text-muted-foreground">
                            {copiedId === "font-body" ? "Copied" : "Click to copy"}
                          </span>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
                {suggestIdentityError && (
                  <p className="text-sm text-destructive">{suggestIdentityError}</p>
                )}
              </div>

              {/* Right: Voice & messaging */}
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold text-foreground">Voice & messaging</h2>
                  {active?.brand_strategy && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => openEdit("messaging")}
                    >
                      <Settings className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                  )}
                </div>
                <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                  {mv?.mission && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground block mb-1">Mission</span>
                      <p className="text-sm text-foreground">{mv.mission}</p>
                      <button
                        type="button"
                        onClick={() => openEdit("mission_vision")}
                        className="text-xs text-muted-foreground hover:text-foreground mt-1"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                  {messaging?.elevator_pitch && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground block mb-1">Elevator pitch</span>
                      <p className="text-sm text-foreground">{messaging.elevator_pitch}</p>
                      <button
                        type="button"
                        onClick={() => openEdit("messaging")}
                        className="text-xs text-muted-foreground hover:text-foreground mt-1"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                  {voice?.archetype && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground block mb-1">Voice</span>
                      <p className="text-sm text-foreground">{voice.archetype}</p>
                      <button
                        type="button"
                        onClick={() => openEdit("voice")}
                        className="text-xs text-muted-foreground hover:text-foreground mt-1"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                  {(pack.primary_cta || pack.usp_statement) && (
                    <div className="pt-2 border-t border-border space-y-3">
                      {pack.primary_cta && (
                        <div>
                          <span className="text-xs font-medium text-muted-foreground block mb-1">Primary CTA</span>
                          <p className="text-sm text-foreground">{pack.primary_cta}</p>
                        </div>
                      )}
                      {pack.usp_statement && (
                        <div>
                          <span className="text-xs font-medium text-muted-foreground block mb-1">USP</span>
                          <p className="text-sm text-foreground">{pack.usp_statement}</p>
                        </div>
                      )}
                    </div>
                  )}
                  {!mv?.mission && !messaging?.elevator_pitch && !voice?.archetype && !pack?.primary_cta && !pack?.usp_statement && (
                    <div className="flex flex-col gap-2">
                      <p className="text-sm text-muted-foreground">
                        Add your mission, pitch, and voice in strategy.
                      </p>
                      {active?.brand_strategy && (
                        <Button variant="outline" size="sm" onClick={() => openEdit("mission_vision")}>
                          Edit voice & messaging
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Footer: used across + edit links */}
            {hasBrandIdentity && (
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
                <span className="text-sm text-muted-foreground">
                  Your brand identity is used across Website, Ads, and Posters.
                </span>
                <button
                  type="button"
                  onClick={() => setLogoDrawerOpen(true)}
                  className="text-sm text-primary hover:underline"
                >
                  Edit logo
                </button>
                {active?.brand_strategy && (
                  <>
                    <span className="text-muted-foreground">·</span>
                    <button
                      type="button"
                      onClick={() => openEdit("messaging")}
                      className="text-sm text-primary hover:underline"
                    >
                      Edit strategy
                    </button>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <AnimatePresence>
        {(editingSection || logoDrawerOpen) && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
              onClick={closeEdit}
              aria-hidden
            />
            <div className="fixed inset-0 z-50 pointer-events-none flex justify-end">
              <motion.div
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "tween", duration: 0.25, ease: "easeOut" }}
                className="pointer-events-auto w-full max-w-[400px] m-10 rounded-2xl border border-border bg-card/95 backdrop-blur-2xl shadow shadow-black/5 dark:shadow-black/15 ring-1 ring-border/50 flex flex-col overflow-hidden"
                role="dialog"
                aria-modal="true"
                aria-labelledby="edit-drawer-title"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3 shrink-0">
                  <h2
                    id="edit-drawer-title"
                    className="font-semibold text-lg text-foreground truncate"
                  >
                    {logoDrawerOpen
                      ? wordmarkSvgOrUrl
                        ? "Change brand logo"
                        : "Add brand logo"
                      : editingSection
                        ? EDIT_SECTION_LABELS[editingSection]
                        : ""}
                  </h2>
                  <button
                    type="button"
                    onClick={closeEdit}
                    className="p-1.5 rounded-lg text-muted-foreground hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors shrink-0"
                    aria-label="Close"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4">
                  {logoDrawerOpen ? (
                    <>
                      {logoError && (
                        <p className="text-sm text-destructive">{logoError}</p>
                      )}
                      <div>
                        <p className="text-sm font-medium text-foreground mb-2">
                          Upload logo
                        </p>
                        <input
                          type="file"
                          accept="image/*"
                          className="block w-full text-sm text-muted-foreground file:mr-2 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary-foreground file:cursor-pointer hover:file:opacity-90"
                          disabled={logoUploading}
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file || !packId) return;
                            setLogoError(null);
                            setLogoUploading(true);
                            try {
                              await packsApi.uploadLogo(packId, file);
                              const updated = await packsApi.get(packId);
                              setPack(updated);
                              setLogoLoadFailed(false);
                              setLogoDrawerOpen(false);
                            } catch (err) {
                              setLogoError(
                                err instanceof Error
                                  ? err.message
                                  : "Upload failed",
                              );
                            } finally {
                              setLogoUploading(false);
                              e.target.value = "";
                            }
                          }}
                        />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground mb-2">
                          Generate my logo
                        </p>
                        <form
                          className="space-y-3"
                          onSubmit={async (e) => {
                            e.preventDefault();
                            const form = e.currentTarget;
                            const brand =
                              (
                                form.querySelector(
                                  '[name="logo_brand_name"]',
                                ) as HTMLInputElement
                              )?.value?.trim() ||
                              brandName ||
                              "My Brand";
                            const styleDescription =
                              logoStyleChips.length > 0
                                ? logoStyleChips.join(", ")
                                : undefined;
                            const colorScheme =
                              logoColorChips.length > 0
                                ? logoColorChips.join(", ")
                                : undefined;
                            const colorPalette =
                              palette.primary || palette.secondary || palette.accent
                                ? {
                                    ...(palette.primary && { primary: palette.primary }),
                                    ...(palette.secondary && { secondary: palette.secondary }),
                                    ...(palette.accent && { accent: palette.accent }),
                                  }
                                : undefined;
                            setLogoError(null);
                            setLogoGenerating(true);
                            try {
                              await packsApi.generateLogo(packId, {
                                brand_name: brand,
                                prompt: styleDescription,
                                color_scheme: colorScheme,
                                color_palette: colorPalette ?? undefined,
                                brand_os_summary:
                                  brandOsSummary || undefined,
                              });
                              const updated = await packsApi.get(packId);
                              setPack(updated);
                            } catch (err) {
                              setLogoError(
                                err instanceof Error
                                  ? err.message
                                  : "Generation failed",
                              );
                            } finally {
                              setLogoGenerating(false);
                            }
                          }}
                        >
                          <input
                            type="text"
                            name="logo_brand_name"
                            placeholder="Brand name"
                            defaultValue={brandName || ""}
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                          />
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1.5">
                              Style
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {LOGO_STYLE_CHIPS.map((label) => (
                                <button
                                  key={label}
                                  type="button"
                                  onClick={() =>
                                    setLogoStyleChips((prev) =>
                                      prev.includes(label)
                                        ? prev.filter((x) => x !== label)
                                        : [...prev, label],
                                    )
                                  }
                                  className={cn(
                                    "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                                    logoStyleChips.includes(label)
                                      ? "bg-primary text-primary-foreground"
                                      : "bg-muted text-muted-foreground hover:bg-muted/80",
                                  )}
                                >
                                  {label}
                                </button>
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1.5">
                              Color scheme
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {LOGO_COLOR_CHIPS.map((label) => (
                                <button
                                  key={label}
                                  type="button"
                                  onClick={() =>
                                    setLogoColorChips((prev) =>
                                      prev.includes(label)
                                        ? prev.filter((x) => x !== label)
                                        : [...prev, label],
                                    )
                                  }
                                  className={cn(
                                    "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                                    logoColorChips.includes(label)
                                      ? "bg-primary text-primary-foreground"
                                      : "bg-muted text-muted-foreground hover:bg-muted/80",
                                  )}
                                >
                                  {label}
                                </button>
                              ))}
                            </div>
                          </div>
                          <Button
                            type="submit"
                            disabled={logoGenerating}
                            className="w-full gap-2"
                          >
                            {logoGenerating ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Sparkles className="h-4 w-4" />
                            )}
                            Generate my logo
                          </Button>
                        </form>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground mb-2">
                          Suggested logos
                        </p>
                        {(() => {
                          const raw = pack?.onboarding_answers?.suggested_logos;
                          let suggested: string[] = [];
                          if (typeof raw === "string") {
                            try {
                              suggested = JSON.parse(raw) as string[];
                            } catch {
                              suggested = [];
                            }
                          } else if (Array.isArray(raw)) {
                            suggested = raw as string[];
                          }
                          if (suggested.length === 0) {
                            return (
                              <p className="text-sm text-muted-foreground">
                                Generate logos above to see suggestions here.
                              </p>
                            );
                          }
                          return (
                            <div className="grid grid-cols-3 gap-2">
                              {suggested.map((url, i) => (
                                <div
                                  key={i}
                                  className="relative group rounded-lg border border-border overflow-hidden bg-muted/30 hover:border-primary/50 aspect-square flex items-center justify-center p-1"
                                >
                                  <button
                                    type="button"
                                    onClick={async () => {
                                      if (!pack) return;
                                      const merged = {
                                        ...(pack.onboarding_answers || {}),
                                        wordmark_svg_or_url: url,
                                      };
                                      setLogoError(null);
                                      try {
                                        await packsApi.submitOnboarding(
                                          packId,
                                          merged as Record<string, string>,
                                        );
                                        const updated =
                                          await packsApi.get(packId);
                                        setPack(updated);
                                        setLogoLoadFailed(false);
                                        setLogoDrawerOpen(false);
                                      } catch (err) {
                                        setLogoError(
                                          err instanceof Error
                                            ? err.message
                                            : "Failed to set logo",
                                        );
                                      }
                                    }}
                                    className="absolute inset-0 flex items-center justify-center p-1 w-full h-full"
                                  >
                                    {url.trimStart().startsWith("<") ? (
                                      <div
                                        className="w-full h-full flex items-center justify-center [&>svg]:max-w-full [&>svg]:max-h-full"
                                        dangerouslySetInnerHTML={{
                                          __html: url,
                                        }}
                                      />
                                    ) : (
                                      <img
                                        src={url}
                                        alt=""
                                        className="max-w-full max-h-full object-contain"
                                      />
                                    )}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={async (e) => {
                                      e.stopPropagation();
                                      if (!pack) return;
                                      setLogoError(null);
                                      const next = suggested.filter(
                                        (_, j) => j !== i,
                                      );
                                      const merged = {
                                        ...(pack.onboarding_answers || {}),
                                        suggested_logos: JSON.stringify(next),
                                      };
                                      try {
                                        await packsApi.submitOnboarding(
                                          packId,
                                          merged as Record<string, string>,
                                        );
                                        const updated =
                                          await packsApi.get(packId);
                                        setPack(updated);
                                      } catch (err) {
                                        setLogoError(
                                          err instanceof Error
                                            ? err.message
                                            : "Failed to remove",
                                        );
                                      }
                                    }}
                                    className="absolute top-1 right-1 p-1 rounded-md bg-background/90 border border-border text-muted-foreground hover:text-destructive hover:border-destructive/50 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                                    aria-label="Remove from suggested"
                                  >
                                    <X className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          );
                        })()}
                      </div>
                      {wordmarkSvgOrUrl && (
                        <div className="pt-2 border-t border-border">
                          <Button
                            type="button"
                            variant="outline"
                            className="w-full gap-2 text-destructive border-destructive/50 hover:bg-destructive/10 hover:border-destructive"
                            disabled={logoRemoving}
                            onClick={async () => {
                              if (!pack) return;
                              setLogoError(null);
                              setLogoRemoving(true);
                              try {
                                const current = {
                                  ...(pack.onboarding_answers || {}),
                                };
                                delete current.wordmark_svg_or_url;
                                delete current.wordmark_result;
                                await packsApi.submitOnboarding(
                                  packId,
                                  current as Record<string, string>,
                                );
                                const updated = await packsApi.get(packId);
                                setPack(updated);
                                setLogoLoadFailed(false);
                                setLogoDrawerOpen(false);
                              } catch (err) {
                                setLogoError(
                                  err instanceof Error
                                    ? err.message
                                    : "Failed to remove logo",
                                );
                              } finally {
                                setLogoRemoving(false);
                              }
                            }}
                          >
                            {logoRemoving ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                            Remove logo
                          </Button>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {editingSection === "mission_vision" &&
                        editDraft.mission_vision && (
                          <>
                            <DrawerFieldLabel
                              label="Mission"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "mission_vision.mission",
                                  editDraft.mission_vision?.mission ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      mission_vision: {
                                        ...prev.mission_vision!,
                                        mission: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField === "mission_vision.mission"
                              }
                            />
                            <TextareaWithIcon
                              value={editDraft.mission_vision.mission}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  mission_vision: {
                                    ...prev.mission_vision!,
                                    mission: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Vision"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "mission_vision.vision",
                                  editDraft.mission_vision?.vision ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      mission_vision: {
                                        ...prev.mission_vision!,
                                        vision: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField === "mission_vision.vision"
                              }
                            />
                            <TextareaWithIcon
                              value={editDraft.mission_vision.vision}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  mission_vision: {
                                    ...prev.mission_vision!,
                                    vision: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Promise"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "mission_vision.promise",
                                  editDraft.mission_vision?.promise ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      mission_vision: {
                                        ...prev.mission_vision!,
                                        promise: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField === "mission_vision.promise"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[120px]"
                              value={editDraft.mission_vision.promise}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  mission_vision: {
                                    ...prev.mission_vision!,
                                    promise: e.target.value,
                                  },
                                }))
                              }
                            />
                          </>
                        )}
                      {editingSection === "audience" &&
                        editDraft.audience_personas && (
                          <div className="space-y-4">
                            {editDraft.audience_personas.map((p, idx) => (
                              <div
                                key={idx}
                                className="p-3 rounded-xl border border-border space-y-2"
                              >
                                <div className="flex justify-between items-center">
                                  <span className="text-sm font-medium">
                                    Persona {idx + 1}
                                  </span>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="text-muted-foreground h-8"
                                    onClick={() =>
                                      setEditDraft((prev) => ({
                                        ...prev,
                                        audience_personas:
                                          prev.audience_personas!.filter(
                                            (_, i) => i !== idx,
                                          ) as AudiencePersona[],
                                      }))
                                    }
                                  >
                                    Remove
                                  </Button>
                                </div>
                                <DrawerFieldLabel
                                  label="Persona name"
                                  onSuggestClick={() =>
                                    handleSuggest(
                                      `audience_personas.${idx}.persona`,
                                      p.persona,
                                      (s) => {
                                        const next = [
                                          ...(editDraft.audience_personas ??
                                            []),
                                        ];
                                        next[idx] = {
                                          ...next[idx],
                                          persona: s,
                                        };
                                        setEditDraft((prev) => ({
                                          ...prev,
                                          audience_personas: next,
                                        }));
                                      },
                                    )
                                  }
                                  isSuggesting={
                                    suggestingField ===
                                    `audience_personas.${idx}.persona`
                                  }
                                />
                                <input
                                  className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                                  placeholder="Persona name"
                                  value={p.persona}
                                  onChange={(e) => {
                                    const next = [
                                      ...(editDraft.audience_personas ?? []),
                                    ];
                                    next[idx] = {
                                      ...next[idx],
                                      persona: e.target.value,
                                    };
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      audience_personas: next,
                                    }));
                                  }}
                                />
                                <DrawerFieldLabel
                                  label="Needs (one per line)"
                                  onSuggestClick={() =>
                                    handleSuggest(
                                      `audience_personas.${idx}.needs`,
                                      (p.needs ?? []).join("\n"),
                                      (s) => {
                                        const next = [
                                          ...(editDraft.audience_personas ??
                                            []),
                                        ];
                                        next[idx] = {
                                          ...next[idx],
                                          needs: s
                                            .split("\n")
                                            .map((x) => x.trim())
                                            .filter(Boolean),
                                        };
                                        setEditDraft((prev) => ({
                                          ...prev,
                                          audience_personas: next,
                                        }));
                                      },
                                    )
                                  }
                                  isSuggesting={
                                    suggestingField ===
                                    `audience_personas.${idx}.needs`
                                  }
                                />
                                <TextareaWithIcon
                                  className="min-h-[100px]"
                                  placeholder="Needs (one per line)"
                                  value={(p.needs ?? []).join("\n")}
                                  onChange={(e) => {
                                    const next = [
                                      ...(editDraft.audience_personas ?? []),
                                    ];
                                    next[idx] = {
                                      ...next[idx],
                                      needs: e.target.value
                                        .split("\n")
                                        .map((s) => s.trim())
                                        .filter(Boolean),
                                    };
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      audience_personas: next,
                                    }));
                                  }}
                                />
                                <DrawerFieldLabel
                                  label="Pain points (one per line)"
                                  onSuggestClick={() =>
                                    handleSuggest(
                                      `audience_personas.${idx}.pain_points`,
                                      (p.pain_points ?? []).join("\n"),
                                      (s) => {
                                        const next = [
                                          ...(editDraft.audience_personas ??
                                            []),
                                        ];
                                        next[idx] = {
                                          ...next[idx],
                                          pain_points: s
                                            .split("\n")
                                            .map((x) => x.trim())
                                            .filter(Boolean),
                                        };
                                        setEditDraft((prev) => ({
                                          ...prev,
                                          audience_personas: next,
                                        }));
                                      },
                                    )
                                  }
                                  isSuggesting={
                                    suggestingField ===
                                    `audience_personas.${idx}.pain_points`
                                  }
                                />
                                <TextareaWithIcon
                                  className="min-h-[100px]"
                                  placeholder="Pain points (one per line)"
                                  value={(p.pain_points ?? []).join("\n")}
                                  onChange={(e) => {
                                    const next = [
                                      ...(editDraft.audience_personas ?? []),
                                    ];
                                    next[idx] = {
                                      ...next[idx],
                                      pain_points: e.target.value
                                        .split("\n")
                                        .map((s) => s.trim())
                                        .filter(Boolean),
                                    };
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      audience_personas: next,
                                    }));
                                  }}
                                />
                              </div>
                            ))}
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  audience_personas: [
                                    ...(prev.audience_personas ?? []),
                                    { persona: "", needs: [], pain_points: [] },
                                  ],
                                }))
                              }
                            >
                              Add persona
                            </Button>
                          </div>
                        )}
                      {editingSection === "positioning" &&
                        editDraft.positioning_differentiation && (
                          <>
                            <DrawerFieldLabel
                              label="Statement"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "positioning_differentiation.statement",
                                  editDraft.positioning_differentiation
                                    ?.statement ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      positioning_differentiation: {
                                        ...prev.positioning_differentiation!,
                                        statement: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "positioning_differentiation.statement"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[120px]"
                              value={
                                editDraft.positioning_differentiation.statement
                              }
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  positioning_differentiation: {
                                    ...prev.positioning_differentiation!,
                                    statement: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Unique advantage"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "positioning_differentiation.unique_advantage",
                                  editDraft.positioning_differentiation
                                    ?.unique_advantage ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      positioning_differentiation: {
                                        ...prev.positioning_differentiation!,
                                        unique_advantage: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "positioning_differentiation.unique_advantage"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[120px]"
                              value={
                                editDraft.positioning_differentiation
                                  .unique_advantage
                              }
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  positioning_differentiation: {
                                    ...prev.positioning_differentiation!,
                                    unique_advantage: e.target.value,
                                  },
                                }))
                              }
                            />
                          </>
                        )}
                      {editingSection === "voice" &&
                        editDraft.voice_personality && (
                          <>
                            <DrawerFieldLabel
                              label="Archetype"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "voice_personality.archetype",
                                  editDraft.voice_personality?.archetype ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      voice_personality: {
                                        ...prev.voice_personality!,
                                        archetype: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "voice_personality.archetype"
                              }
                            />
                            <input
                              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                              value={editDraft.voice_personality.archetype}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  voice_personality: {
                                    ...prev.voice_personality!,
                                    archetype: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Profile (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "voice_personality.profile",
                                  (
                                    editDraft.voice_personality?.profile ?? []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      voice_personality: {
                                        ...prev.voice_personality!,
                                        profile: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField === "voice_personality.profile"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[100px]"
                              value={(
                                editDraft.voice_personality.profile ?? []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  voice_personality: {
                                    ...prev.voice_personality!,
                                    profile: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="We are (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "voice_personality.we_are",
                                  (
                                    editDraft.voice_personality?.we_are ?? []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      voice_personality: {
                                        ...prev.voice_personality!,
                                        we_are: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField === "voice_personality.we_are"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[100px]"
                              value={(
                                editDraft.voice_personality.we_are ?? []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  voice_personality: {
                                    ...prev.voice_personality!,
                                    we_are: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="We are not (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "voice_personality.we_are_not",
                                  (
                                    editDraft.voice_personality?.we_are_not ??
                                    []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      voice_personality: {
                                        ...prev.voice_personality!,
                                        we_are_not: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "voice_personality.we_are_not"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[100px]"
                              value={(
                                editDraft.voice_personality.we_are_not ?? []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  voice_personality: {
                                    ...prev.voice_personality!,
                                    we_are_not: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                          </>
                        )}
                      {editingSection === "messaging" &&
                        editDraft.core_messaging_hierarchy && (
                          <>
                            <DrawerFieldLabel
                              label="Elevator pitch"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "core_messaging_hierarchy.elevator_pitch",
                                  editDraft.core_messaging_hierarchy
                                    ?.elevator_pitch ?? "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      core_messaging_hierarchy: {
                                        ...prev.core_messaging_hierarchy!,
                                        elevator_pitch: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "core_messaging_hierarchy.elevator_pitch"
                              }
                            />
                            <TextareaWithIcon
                              value={
                                editDraft.core_messaging_hierarchy
                                  .elevator_pitch
                              }
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  core_messaging_hierarchy: {
                                    ...prev.core_messaging_hierarchy!,
                                    elevator_pitch: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Proof points (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "core_messaging_hierarchy.proof_points",
                                  (
                                    editDraft.core_messaging_hierarchy
                                      ?.proof_points ?? []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      core_messaging_hierarchy: {
                                        ...prev.core_messaging_hierarchy!,
                                        proof_points: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "core_messaging_hierarchy.proof_points"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[120px]"
                              value={(
                                editDraft.core_messaging_hierarchy
                                  .proof_points ?? []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  core_messaging_hierarchy: {
                                    ...prev.core_messaging_hierarchy!,
                                    proof_points: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                          </>
                        )}
                      {editingSection === "style" &&
                        editDraft.style_direction_seeds && (
                          <>
                            <DrawerFieldLabel
                              label="Typography"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "style_direction_seeds.typography",
                                  editDraft.style_direction_seeds?.typography ??
                                    "",
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      style_direction_seeds: {
                                        ...prev.style_direction_seeds!,
                                        typography: s,
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "style_direction_seeds.typography"
                              }
                            />
                            <input
                              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                              value={editDraft.style_direction_seeds.typography}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  style_direction_seeds: {
                                    ...prev.style_direction_seeds!,
                                    typography: e.target.value,
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Design cues (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "style_direction_seeds.design_cues",
                                  (
                                    editDraft.style_direction_seeds
                                      ?.design_cues ?? []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      style_direction_seeds: {
                                        ...prev.style_direction_seeds!,
                                        design_cues: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "style_direction_seeds.design_cues"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[100px]"
                              value={(
                                editDraft.style_direction_seeds.design_cues ??
                                []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  style_direction_seeds: {
                                    ...prev.style_direction_seeds!,
                                    design_cues: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                            <DrawerFieldLabel
                              label="Palette (one per line)"
                              onSuggestClick={() =>
                                handleSuggest(
                                  "style_direction_seeds.palette",
                                  (
                                    editDraft.style_direction_seeds?.palette ??
                                    []
                                  ).join("\n"),
                                  (s) =>
                                    setEditDraft((prev) => ({
                                      ...prev,
                                      style_direction_seeds: {
                                        ...prev.style_direction_seeds!,
                                        palette: s
                                          .split("\n")
                                          .map((x) => x.trim())
                                          .filter(Boolean),
                                      },
                                    })),
                                )
                              }
                              isSuggesting={
                                suggestingField ===
                                "style_direction_seeds.palette"
                              }
                            />
                            <TextareaWithIcon
                              className="min-h-[100px]"
                              value={(
                                editDraft.style_direction_seeds.palette ?? []
                              ).join("\n")}
                              onChange={(e) =>
                                setEditDraft((prev) => ({
                                  ...prev,
                                  style_direction_seeds: {
                                    ...prev.style_direction_seeds!,
                                    palette: e.target.value
                                      .split("\n")
                                      .map((s) => s.trim())
                                      .filter(Boolean),
                                  },
                                }))
                              }
                            />
                          </>
                        )}
                    </>
                  )}
                </div>
                {!logoDrawerOpen && (
                  <div className="border-t border-border px-4 py-3 shrink-0 flex flex-col gap-2">
                    {saveError && (
                      <p className="text-sm text-destructive">{saveError}</p>
                    )}
                    <Button
                      onClick={handleSaveEdit}
                      disabled={saveLoading}
                      className="w-full"
                    >
                      {saveLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Save Changes"
                      )}
                    </Button>
                  </div>
                )}
              </motion.div>
            </div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
