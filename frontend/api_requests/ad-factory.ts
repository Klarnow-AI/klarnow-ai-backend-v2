import { api } from "@/lib/http";

const AD_FACTORY_PREFIX = "/api/v1/ad-factory";

export type AdFactoryVariant = {
  slot: "A" | "B" | "C";
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
};

export type GenerateVariantsResponse = {
  render_id: string;
  variants: AdFactoryVariant[];
  validation_status: "pass" | "fail";
  validation_checks?: Array<{ check_id: string; passed: boolean; message?: string }>;
};

export type RenderResponse = {
  asset_ids: string[];
  credits_used: number;
};

export const adFactory = {
  generateVariants: (packId: string) =>
    api<GenerateVariantsResponse>(`${AD_FACTORY_PREFIX}/generate`, {
      method: "POST",
      body: JSON.stringify({ pack_id: packId }),
    }),

  render: (renderId: string, variantSlots: ("A" | "B" | "C")[]) =>
    api<RenderResponse>(`${AD_FACTORY_PREFIX}/renders/${encodeURIComponent(renderId)}/render`, {
      method: "POST",
      body: JSON.stringify({ variant_slots: variantSlots }),
    }),

  getRender: (renderId: string) =>
    api<{
      render_id: string;
      pack_id: string;
      status: string;
      brand_brief: Record<string, unknown>;
      pack_snapshot: Record<string, unknown>;
      variants: AdFactoryVariant[];
      engines_output?: Record<string, unknown>;
      render_metadata?: Record<string, unknown>;
    }>(`${AD_FACTORY_PREFIX}/renders/${encodeURIComponent(renderId)}`),
};
