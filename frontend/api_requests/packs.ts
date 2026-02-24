import { api } from "@/lib/http";
import type {
  Pack,
  PackListResponse,
  PackSummaryResponse,
  PackGatesResponse,
  OnboardingCompleteResponse,
  OnboardingCompleteAccepted,
  ExtractBrandBody,
  ExtractBrandResponse,
  GenerateStarterBrandBody,
  GenerateStarterBrandResponse,
  GenerateLogoBody,
  GenerateLogoResponse,
  UploadLogoResponse,
  GenerateMockupsResponse,
} from "@/types/api-types";

const PACKS_PREFIX = "/api/v1/packs";

const ONBOARDING_POLL_INTERVAL_MS = 2000;
const ONBOARDING_POLL_TIMEOUT_MS = 120000; // 2 min

/** Poll GET pack until onboarding_background_completed_at is set (after 202 from complete). */
export async function pollPackUntilOnboardingReady(
  packId: string,
  options?: { intervalMs?: number; timeoutMs?: number }
): Promise<Pack> {
  const intervalMs = options?.intervalMs ?? ONBOARDING_POLL_INTERVAL_MS;
  const timeoutMs = options?.timeoutMs ?? ONBOARDING_POLL_TIMEOUT_MS;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const pack = await packs.get(packId);
    if (pack.onboarding_background_completed_at) return pack;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Onboarding is taking longer than expected. Refresh the page to check status.");
}

export const packs = {
  list: (includeArchived = false) =>
    api<PackListResponse>(
      `${PACKS_PREFIX}?include_archived=${includeArchived}`
    ),
  get: (id: string) => api<Pack>(`${PACKS_PREFIX}/${id}`),
  getSummary: (id: string) =>
    api<PackSummaryResponse>(`${PACKS_PREFIX}/${id}/summary`),
  gates: (id: string) =>
    api<PackGatesResponse>(`${PACKS_PREFIX}/${id}/gates`),
  create: (name: string) =>
    api<Pack>(`${PACKS_PREFIX}`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  patch: (
    id: string,
    body: {
      name?: string;
      client_id?: string | null;
      pack_type?: string;
      core_concept?: string | null;
      brand_name?: string | null;
      primary_cta?: string | null;
      usp_category?: string | null;
      usp_statement?: string | null;
      usp_proof?: string | null;
      usp_locked_line?: string | null;
      proof_types?: string[] | null;
      proof_text?: string | null;
      onboarding_answers?: Record<string, string>;
    }
  ) =>
    api<Pack>(`${PACKS_PREFIX}/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  archive: (id: string) =>
    api<Pack>(`${PACKS_PREFIX}/${id}/archive`, {
      method: "POST",
    }),
  restore: (id: string) =>
    api<Pack>(`${PACKS_PREFIX}/${id}/restore`, {
      method: "POST",
    }),
  delete: (id: string) =>
    api(`${PACKS_PREFIX}/${id}`, {
      method: "DELETE",
    }),
  submitOnboarding: (packId: string, answers: Record<string, string>) =>
    api<Pack>(`${PACKS_PREFIX}/${packId}/onboarding`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
  /** Returns 200 with pack + is_existing_brand, or 202 with { status, pack_id }. For 202, use pollPackUntilOnboardingReady(pack_id) then use the pack. */
  completeOnboarding: (packId: string) =>
    api<OnboardingCompleteResponse | OnboardingCompleteAccepted>(
      `${PACKS_PREFIX}/${packId}/onboarding/complete`,
      { method: "POST" }
    ),
  extractBrand: (packId: string, body: ExtractBrandBody) =>
    api<ExtractBrandResponse>(
      `${PACKS_PREFIX}/${packId}/onboarding/extract-brand`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  generateStarterBrand: (packId: string, body: GenerateStarterBrandBody) =>
    api<GenerateStarterBrandResponse>(
      `${PACKS_PREFIX}/${packId}/onboarding/generate-starter-brand`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  uploadLogo: (packId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api<UploadLogoResponse>(
      `${PACKS_PREFIX}/${packId}/onboarding/upload-logo`,
      { method: "POST", body: form }
    );
  },
  generateLogo: (packId: string, body: GenerateLogoBody) =>
    api<GenerateLogoResponse>(
      `${PACKS_PREFIX}/${packId}/onboarding/generate-logo`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  generateMockups: (packId: string) =>
    api<GenerateMockupsResponse>(
      `${PACKS_PREFIX}/${packId}/brand-showcase/generate-mockups`,
      { method: "POST" }
    ),

  suggestTypography: (
    packId: string,
    body?: { current_headline?: string | null; current_body?: string | null }
  ) =>
    api<{ headline_font: string; body_font: string }>(
      `${PACKS_PREFIX}/${packId}/brand-identity/suggest-typography`,
      { method: "POST", body: JSON.stringify(body ?? {}) }
    ),

  suggestPalette: (
    packId: string,
    body?: { current_palette?: Record<string, string> | null }
  ) =>
    api<{
      primary: string;
      secondary: string;
      accent: string;
      background?: string | null;
      surface?: string | null;
    }>(`${PACKS_PREFIX}/${packId}/brand-identity/suggest-palette`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
};
