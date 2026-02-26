import { api } from "@/lib/http";

export type CampaignRead = {
  id: string;
  pack_id: string;
  version: string;
  primary_cta: string | null;
  goal: Record<string, unknown> | null;
  angles: unknown[] | null;
  active_angle_id: string | null;
  is_active: boolean;
  created_at: string;
};

export const campaign = {
  get: (packId: string) =>
    api<CampaignRead | null>(`/api/v1/packs/${packId}/campaign`),
  patch: (packId: string, body: { is_active?: boolean }) =>
    api<CampaignRead>(`/api/v1/packs/${packId}/campaign`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};
