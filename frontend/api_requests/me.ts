import { api } from "@/lib/http";
import type {
  LandingContext,
  NextAction,
  LandingCompleteBody,
  LandingCompleteResponse,
} from "@/types/api-types";

const ME_PREFIX = "/api/v1/me";

export const me = {
  landingContext: () => api<LandingContext>(`${ME_PREFIX}/landing-context`),
  getNextAction: (packId?: string | null) =>
    api<NextAction>(
      packId
        ? `${ME_PREFIX}/next-action?pack_id=${encodeURIComponent(packId)}`
        : `${ME_PREFIX}/next-action`
    ),
  landingComplete: (body: LandingCompleteBody) =>
    api<LandingCompleteResponse>(`${ME_PREFIX}/landing-complete`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    }),
};
