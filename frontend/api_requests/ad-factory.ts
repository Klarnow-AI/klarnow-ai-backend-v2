import { api } from "@/lib/http";
import type { CreativeAsset } from "@/types/api-types";

const AD_FACTORY_PREFIX = "/api/v1/ad-factory";

export type VariantSlot = "A" | "B" | "C";
export type RenderScope = "single_variant_30" | "abc_bundle_30" | "abc_bundle_30_plus_15";

export type Lineage = {
  source_registry_item_id: string;
  source_registry_item_type: string;
  template_id: string;
  fill_variables: Record<string, string>;
  registry_version: string;
  engine_logic_version: string;
  generator_stage: string;
};

export type TimedScriptBeat = {
  beat_name: "hook" | "problem" | "mechanism" | "proof" | "offer" | "cta";
  text: string;
  start_second: number;
  end_second: number;
  lineage: Lineage;
};

export type Script = {
  beats: TimedScriptBeat[];
  timing_rules_satisfied: boolean;
};

export type CTAResolved = {
  cta_action: string;
  destination_type: string;
  destination_value: string;
  mid_line: string;
  end_line: string;
  mid_lineage: Lineage;
  end_lineage: Lineage;
};

export type LineageTextItem = {
  text: string;
  lineage: Lineage;
};

export type AnchorShot = {
  index: number;
  shot_type: string;
  description: string;
  on_screen_text: string;
  nanobanana_prompt: string;
  lineage: Lineage;
  caption_overlay: Record<string, unknown>;
};

export type RenderAnchorFrame = {
  index: number;
  shot_type: string;
  description: string;
  on_screen_text: string;
};

export type ProviderNeutralRenderIntent = {
  duration_seconds: 15 | 30;
  aspect_ratio: "9:16";
  treatment: string;
  pacing_mode: string;
  captions_on: boolean;
  fast_cuts: boolean;
  cta_mid_and_end: boolean;
  anchor_frames: RenderAnchorFrame[];
  continuity_requirements: Record<string, unknown>;
  voiceover_mode: "native_audio" | "silent";
  provider_target: "kling";
  spoken_narration: string;
  caption_lines: string[];
  hook_line: string;
  core_concept: string;
  cta_line: string;
  business_name: string;
  offer: string;
  audience: string;
  primary_outcome: string;
  proof_line: string;
};

export type AdFactoryVariant = {
  slot: VariantSlot;
  intent: string;
  path: string;
  treatment: string;
  hook_type: string;
  core_concept: string;
  hook_line: string;
  hook_lineage: Lineage;
  script_15s: Script;
  script_30s: Script;
  anchor_shot_plan: AnchorShot[];
  on_screen_text: LineageTextItem[];
  nanobanana_prompts: LineageTextItem[];
  render_intent_15s: ProviderNeutralRenderIntent;
  render_intent_30s: ProviderNeutralRenderIntent;
  cta: CTAResolved;
};

export type ValidationCheck = {
  check_id: string;
  passed: boolean;
  blocking: boolean;
  slot: VariantSlot | null;
  field_path: string;
  message?: string | null;
};

export type ClaimGuardCheck = {
  rule_id: string;
  passed: boolean;
  blocking: boolean;
  slot: VariantSlot | null;
  field_path: string;
  message?: string | null;
};

export type BillingSnapshot = {
  billing_mode: "disabled" | "feature_flagged" | "enforced";
  render_scope: RenderScope;
  credits_required: number;
  credits_available: number;
  credits_reserved: number;
  credits_consumed: number;
  purchase_required: boolean;
  reservation_expires_at: string | null;
  idempotency_key: string;
};

export type LaunchState = {
  live_order: Array<{
    slot: VariantSlot;
    marked_live_at: string;
  }>;
};

export type AdFactoryCompile = {
  id: string;
  pack_id: string;
  status: "compiled" | "validation_failed" | "failed";
  brand_brief: Record<string, unknown>;
  pack_snapshot: Record<string, unknown>;
  selection: {
    selection_seed: string;
    variant_intent_strategy: string;
  };
  versions: {
    schema_version: string;
    registry_version: string;
    pattern_pack_version: string;
    engine_logic_version: string;
    provider_adapter_version: string;
    model_version_map: Record<string, string>;
  };
  compile_result: {
    engine0_output: Record<string, unknown>;
    engine1_output: Record<string, unknown>;
    engine2_output: Record<string, unknown>;
    engine3_output: Record<string, unknown>;
    engine4_output: Record<string, unknown>;
    engine5_output: Record<string, unknown>;
    engine6_output: Record<string, unknown>;
    variants: Record<VariantSlot, AdFactoryVariant>;
  };
  claim_guard_result: {
    status: "pass" | "fail";
    checks: ClaimGuardCheck[];
    blocking_errors: ClaimGuardCheck[];
  };
  validator_result: {
    status: "pass" | "fail";
    checks: ValidationCheck[];
    blocking_errors: ValidationCheck[];
  };
  launch_recommendation: {
    order: VariantSlot[];
    rationale: string[];
  };
  launch_state: LaunchState;
  created_at: string;
  updated_at: string;
};

export type AdFactoryRenderJob = {
  id: string;
  compile_result_id: string;
  pack_id: string;
  status: "pending" | "reserved" | "rendering" | "complete" | "failed";
  selected_variants: VariantSlot[];
  durations_requested: Array<15 | 30>;
  voiceover_addon: boolean;
  provider_target: string;
  provider_adapter_version: string;
  billing_snapshot: BillingSnapshot;
  provider_job_ids: Record<string, string>;
  asset_urls: Record<string, string | null>;
  retry_state: Record<string, unknown>;
  failure_state: Record<string, unknown>;
  render_result: {
    render_scope: RenderScope;
    asset_ids: string[];
    assets: CreativeAsset[];
    provider_payloads: Record<string, unknown>;
    storage_sync_status?: string;
  };
  created_at: string;
  updated_at: string;
};

export type CreateRenderJobBody = {
  compile_result_id: string;
  selected_variants: VariantSlot[];
  durations_requested: Array<15 | 30>;
  voiceover_addon?: boolean;
  provider_target?: "kling";
  idempotency_key?: string;
};

export type LegacyGenerateVariantsResponse = {
  render_id: string;
  compile_id: string;
  variants: Array<{
    slot: VariantSlot;
    intent: string;
    path: string;
    treatment: string;
    hook_type: string;
    core_concept: string;
    hook_line: string;
    script_15s: { beats: Array<{ beat_name: string; text: string }>; timing_rules_satisfied: boolean };
    script_30s: { beats: Array<{ beat_name: string; text: string }>; timing_rules_satisfied: boolean };
    shot_list: Array<{ shot_type: string; description: string; on_screen_text: string; nanobanana_prompt: string }>;
    on_screen_text: string[];
    nanobanana_prompts: string[];
    kling_15s: { prompt: string; duration_seconds: 15 };
    kling_30s: { prompt: string; duration_seconds: 30 };
  }>;
  validation_status: "pass" | "fail";
  validation_checks: ValidationCheck[];
};

export const adFactory = {
  createCompile: (packId: string, selectionSeed?: string) =>
    api<AdFactoryCompile>(`${AD_FACTORY_PREFIX}/compiles`, {
      method: "POST",
      body: JSON.stringify({
        pack_id: packId,
        ...(selectionSeed ? { selection_seed: selectionSeed } : {}),
      }),
    }),

  getCompile: (compileId: string) =>
    api<AdFactoryCompile>(`${AD_FACTORY_PREFIX}/compiles/${encodeURIComponent(compileId)}`),

  createRenderJob: (body: CreateRenderJobBody) =>
    api<AdFactoryRenderJob>(`${AD_FACTORY_PREFIX}/renders`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getRenderJob: (renderJobId: string) =>
    api<AdFactoryRenderJob>(`${AD_FACTORY_PREFIX}/renders/${encodeURIComponent(renderJobId)}`),

  markVariantLive: (compileId: string, slot: VariantSlot) =>
    api<{ compile_id: string; slot: VariantSlot; launch_state: LaunchState }>(
      `${AD_FACTORY_PREFIX}/compiles/${encodeURIComponent(compileId)}/launches/${encodeURIComponent(slot)}`,
      {
        method: "POST",
      },
    ),

  generateVariants: (packId: string) =>
    api<LegacyGenerateVariantsResponse>(`${AD_FACTORY_PREFIX}/generate`, {
      method: "POST",
      body: JSON.stringify({ pack_id: packId }),
    }),

  render: (compileId: string, variantSlots: VariantSlot[]) =>
    api<{ asset_ids: string[]; assets: CreativeAsset[]; render_job_id: string }>(
      `${AD_FACTORY_PREFIX}/renders/${encodeURIComponent(compileId)}/render`,
      {
        method: "POST",
        body: JSON.stringify({ variant_slots: variantSlots }),
      },
    ),

  getRender: (compileId: string) =>
    api<{
      render_id: string;
      pack_id: string;
      status: string;
      brand_brief: Record<string, unknown>;
      pack_snapshot: Record<string, unknown>;
      variants: AdFactoryVariant[];
      engines_output?: Record<string, unknown>;
      render_metadata?: Record<string, unknown>;
    }>(`${AD_FACTORY_PREFIX}/legacy/renders/${encodeURIComponent(compileId)}`),
};
