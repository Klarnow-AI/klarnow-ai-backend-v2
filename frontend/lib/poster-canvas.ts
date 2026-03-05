import {
  POSTER_SIZE_SPECS,
  type PosterSizeId,
  extractPosterTemplateIdFromFilename,
} from "@/lib/poster-output";

export type PosterCanvasDimensions = {
  width: number;
  height: number;
  sizeId: PosterSizeId | null;
};

const DEFAULT_SIZE_ID: PosterSizeId = "4x5";

function extractNumericStyleDimension(
  code: string,
  property: "width" | "height",
): number | null {
  const patterns = [
    new RegExp(`${property}\\s*:\\s*(\\d{3,4})(?:\\b|\\s*[,}])`, "i"),
    new RegExp(`${property}\\s*:\\s*[\"'](\\d{3,4})px[\"']`, "i"),
    new RegExp(`${property}\\s*:\\s*[\"']?(\\d{3,4})[\"']?`, "i"),
  ];

  for (const pattern of patterns) {
    const match = code.match(pattern);
    if (match) {
      const parsed = Number.parseInt(match[1], 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    }
  }

  return null;
}

export function inferPosterCanvasDimensions(
  name: string,
  code: string,
): PosterCanvasDimensions {
  const sizeIdFromName = extractPosterTemplateIdFromFilename(name);
  if (sizeIdFromName) {
    const spec = POSTER_SIZE_SPECS[sizeIdFromName];
    return {
      width: spec.width,
      height: spec.height,
      sizeId: sizeIdFromName,
    };
  }

  const widthFromCode = extractNumericStyleDimension(code, "width");
  const heightFromCode = extractNumericStyleDimension(code, "height");

  if (widthFromCode && heightFromCode) {
    return {
      width: widthFromCode,
      height: heightFromCode,
      sizeId: null,
    };
  }

  const fallback = POSTER_SIZE_SPECS[DEFAULT_SIZE_ID];
  return {
    width: fallback.width,
    height: fallback.height,
    sizeId: DEFAULT_SIZE_ID,
  };
}
