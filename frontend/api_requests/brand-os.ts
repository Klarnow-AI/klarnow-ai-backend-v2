import { api } from "@/lib/http";
import type { BrandOS, BrandStrategyProfile } from "@/types/api-types";

const API_PREFIX = "/api/v1";

export type BrandOSUpdateBody = {
  foundation?: BrandOS["foundation"];
  brand_strategy?: BrandStrategyProfile;
};

export const brandOs = {
  getActive: (packId: string) =>
    api<BrandOS | null>(`${API_PREFIX}/packs/${packId}/brand-os/active`),

  listVersions: (packId: string) =>
    api<{ items: BrandOS[]; total: number }>(
      `${API_PREFIX}/packs/${packId}/brand-os`
    ),

  getVersion: (packId: string, version: string) =>
    api<BrandOS>(`${API_PREFIX}/packs/${packId}/brand-os/version/${version}`),

  /** Update the active Brand OS (merge foundation and/or brand_strategy). */
  updateActive: (packId: string, body: BrandOSUpdateBody) =>
    api<BrandOS>(`${API_PREFIX}/packs/${packId}/brand-os/active`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /** Suggest a value for a Brand OS field using AI. */
  suggest: (packId: string, body: { field: string; current_value?: string | null }) =>
    api<{ suggestion: string }>(`${API_PREFIX}/packs/${packId}/brand-os/suggest`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** Regenerate: create Version B from current version (P8). */
  regenerate: (packId: string, brandOsId: string) =>
    api<BrandOS>(`${API_PREFIX}/packs/${packId}/brand-os/${brandOsId}/regenerate`, {
      method: "POST",
    }),
};
