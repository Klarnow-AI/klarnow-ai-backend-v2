import { api } from "@/lib/http";
import type {
  ConversionPagePreview,
  PublicLeadCaptureBody,
  PublicLeadCaptureResponse,
} from "@/types/api-types";

const PUBLIC_PREFIX = "/api/v1/public";

export const publicApi = {
  getPublishedConversionPage: (packId: string) =>
    api<ConversionPagePreview>(
      `${PUBLIC_PREFIX}/packs/${packId}/conversion-page`
    ),

  captureLead: (packId: string, body: PublicLeadCaptureBody) =>
    api<PublicLeadCaptureResponse>(`${PUBLIC_PREFIX}/packs/${packId}/leads`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

