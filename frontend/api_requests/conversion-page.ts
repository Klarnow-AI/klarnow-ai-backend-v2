import { api } from "@/lib/http";
import type {
  ConversionPageListResponse,
  ConversionPagePreview,
  ConversionPagePublishBody,
  ConversionPageRead,
  ConversionPageUpdateBody,
} from "@/types/api-types";

const PACKS_PREFIX = "/api/v1/packs";

export const conversionPageApi = {
  getDraft: (packId: string) =>
    api<ConversionPageRead | null>(
      `${PACKS_PREFIX}/${packId}/conversion-page/draft`
    ),

  getPublished: (packId: string) =>
    api<ConversionPageRead | null>(
      `${PACKS_PREFIX}/${packId}/conversion-page/published`
    ),

  getPreview: (packId: string, version?: string | null) =>
    api<ConversionPagePreview>(
      version
        ? `${PACKS_PREFIX}/${packId}/conversion-page/preview?version=${encodeURIComponent(
            version
          )}`
        : `${PACKS_PREFIX}/${packId}/conversion-page/preview`
    ),

  listVersions: (packId: string) =>
    api<ConversionPageListResponse>(`${PACKS_PREFIX}/${packId}/conversion-page`),

  getByVersion: (packId: string, version: string) =>
    api<ConversionPageRead>(
      `${PACKS_PREFIX}/${packId}/conversion-page/version/${encodeURIComponent(
        version
      )}`
    ),

  patchDraft: (packId: string, body: ConversionPageUpdateBody) =>
    api<ConversionPageRead>(`${PACKS_PREFIX}/${packId}/conversion-page/draft`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  regenerate: (packId: string) =>
    api<ConversionPageRead>(
      `${PACKS_PREFIX}/${packId}/conversion-page/regenerate`,
      { method: "POST" }
    ),

  publish: (packId: string, body: ConversionPagePublishBody) =>
    api<ConversionPageRead>(
      `${PACKS_PREFIX}/${packId}/conversion-page/publish`,
      { method: "POST", body: JSON.stringify(body) }
    ),
};

