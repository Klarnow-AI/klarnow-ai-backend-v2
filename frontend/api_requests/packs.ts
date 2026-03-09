import { api } from "@/lib/http";
import type {
  Pack,
  PackListResponse,
  PackSummaryResponse,
  PackGatesResponse,
  OnboardingCompleteResponse,
  OnboardingCompleteAccepted,
  OnboardingJobStatus,
  ExtractBrandBody,
  ExtractBrandResponse,
  GenerateStarterBrandBody,
  GenerateStarterBrandResponse,
  GenerateLogoBody,
  GenerateLogoResponse,
  UploadLogoResponse,
} from "@/types/api-types";

const PACKS_PREFIX = "/api/v1/packs";

const ONBOARDING_POLL_TIMEOUT_MS = 120000; // 2 min
const ONBOARDING_POLL_INTERVALS_MS = [2000, 3000, 5000, 8000];

function getOnboardingStageLabel(stage: string | null | undefined): string | null {
  switch (stage) {
    case "starter_brand":
      return "Creating your starter brand";
    case "brand_os":
      return "Generating your Brand OS";
    case "logo":
      return "Generating your logo";
    default:
      return null;
  }
}

function inferOnboardingStage(status: OnboardingJobStatus): string | null {
  if (status.current_stage) return status.current_stage;
  if (!status.stages) return null;

  const orderedStages = ["starter_brand", "brand_os", "logo"] as const;
  for (const stageName of orderedStages) {
    const stage = status.stages[stageName];
    if (!stage) continue;
    if (stage.status === "running") return stageName;
    if (stage.status === "pending") return stageName;
  }
  return null;
}

export function formatOnboardingProgress(status: OnboardingJobStatus): string {
  const retryPrefix =
    status.attempt > 1 ? `Retry ${status.attempt - 1} of ${status.max_attempts - 1}. ` : "";

  if (status.status === "queued") {
    return retryPrefix
      ? `${retryPrefix}Queued. Preparing your brand setup...`
      : "Queued. Preparing your brand setup...";
  }

  if (status.status === "running") {
    const stageLabel = getOnboardingStageLabel(inferOnboardingStage(status));
    return stageLabel
      ? `${retryPrefix}${stageLabel}...`
      : `${retryPrefix}Finalizing your brand setup...`;
  }

  if (status.status === "completed") {
    return "Brand setup ready.";
  }

  if (status.status === "failed") {
    return status.last_error || "Brand setup failed. Please retry.";
  }

  return "Preparing your brand setup...";
}

/** Poll GET pack until onboarding_background_completed_at is set (after 202 from complete). */
export async function pollPackUntilOnboardingReady(
  packId: string,
  options?: {
    intervalMs?: number;
    timeoutMs?: number;
    onProgress?: (status: OnboardingJobStatus, message: string) => void;
  }
): Promise<Pack> {
  const timeoutMs = options?.timeoutMs ?? ONBOARDING_POLL_TIMEOUT_MS;
  const deadline = Date.now() + timeoutMs;
  let attempt = 0;
  let lastStatusErrorMessage: string | null = null;
  while (Date.now() < deadline) {
    const status = await packs
      .getOnboardingStatus(packId)
      .catch((error) => {
        lastStatusErrorMessage =
          error instanceof Error ? error.message : String(error);
        return null;
      });
    if (status) {
      options?.onProgress?.(status, formatOnboardingProgress(status));
    }
    if (status?.status === "failed") {
      throw new Error(
        status.last_error ||
          "Onboarding failed in background processing. Please retry.",
      );
    }
    if (status?.status === "completed") {
      return packs.get(packId);
    }
    const intervalMs =
      options?.intervalMs ??
      ONBOARDING_POLL_INTERVALS_MS[
        Math.min(attempt, ONBOARDING_POLL_INTERVALS_MS.length - 1)
      ];
    attempt += 1;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  const pack = await packs.get(packId).catch(() => null);
  if (pack?.onboarding_background_completed_at) return pack;
  if (lastStatusErrorMessage) {
    throw new Error(
      `Unable to confirm onboarding status: ${lastStatusErrorMessage}`,
    );
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
  getDayReadiness: (packId: string, day: number) =>
    api<{ ready: boolean }>(
      `${PACKS_PREFIX}/${packId}/day-readiness?day=${day}`
    ),
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
  getOnboardingStatus: (packId: string) =>
    api<OnboardingJobStatus>(`${PACKS_PREFIX}/${packId}/onboarding/status`),
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
