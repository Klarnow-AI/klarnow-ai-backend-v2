import { api } from "@/lib/http";
import type {
  CreativeAsset,
  CreativeAssetCreateBody,
  CreativeAssetListResponse,
} from "@/types/api-types";

const CREATIVE_PREFIX = "/api/v1/creative";

export const creative = {
  listAssets: (packId: string) =>
    api<CreativeAssetListResponse>(
      `${CREATIVE_PREFIX}/assets?pack_id=${encodeURIComponent(packId)}`
    ),

  createAsset: (body: CreativeAssetCreateBody) =>
    api<CreativeAsset>(`${CREATIVE_PREFIX}/assets`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteAsset: (assetId: string) =>
    api<void>(`${CREATIVE_PREFIX}/assets/${encodeURIComponent(assetId)}`, {
      method: "DELETE",
    }),
};
